# D:\FYP\FORGE-1\agents\gateway.py
"""
Minimal LLM gateway (decisions D-128, D-138). Every model call made by an agent goes through
call_structured(), so agents contain no provider code. The gateway:
  * picks the model for a task from the environment (the single FORGE-1/.env),
  * sends every call to one provider: Vertex AI (Google Cloud, uses the project's credits) or the
    Google AI Studio API, chosen by LLM_PROVIDER (D-184),
  * asks for structured output that matches a Pydantic schema,
  * retries an invalid output once, sending the parse error back to the model,
  * retries transient provider errors (HTTP 429/5xx, timeouts) with backoff, then tries
    the fallback model once (D-121, D-140),
  * returns the usage of the call (tokens, latency) for the run's usage totals.

The per-call LLM_CALL database record is written later by the API layer (D-133).
Cost is not estimated yet: MODEL_CONFIG prices are not set up.
"""
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

T = TypeVar("T", bound=BaseModel)

# task -> environment variable holding its model id
_TASK_MODEL_ENV = {
    "clarification": "CLARIFICATION_MODEL",
}
_DEFAULT_MODEL = "gemini-3.8-flash"
_TRANSIENT_CODES = {408, 429, 500, 502, 503, 504}
_BACKOFF_SECONDS = (1.0, 3.0)          # PLACEHOLDER: waits before the 2nd and 3rd attempt


class ModelCallError(Exception):
    """The call failed for good. Nodes turn this into a FAILED run with category 'system'."""


class InvalidOutputError(ModelCallError):
    """The model returned output that does not match the schema, twice."""


@dataclass
class CallUsage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    unknown_token_calls: int = 0
    latency_ms: int = 0
    models: list[str] = field(default_factory=list)


def model_for(task: str) -> str:
    return os.getenv(_TASK_MODEL_ENV.get(task, ""), "") or _DEFAULT_MODEL


def provider() -> str:
    """'vertex' or 'studio'. LLM_PROVIDER decides; if it is not set, Vertex AI is used whenever
    VERTEX_API_KEY exists. Primary and fallback model always use the same provider, so all spending
    lands on one bill (D-184)."""
    chosen = os.getenv("LLM_PROVIDER", "").strip().lower()
    if chosen in ("vertex", "studio"):
        return chosen
    return "vertex" if os.getenv("VERTEX_API_KEY") else "studio"


# The Google SDK reads these two by itself and, in Vertex mode, prefers them over the key we pass,
# so the AI Studio key is stored as STUDIO_API_KEY instead (D-184).
_SDK_KEY_VARIABLES = ("GOOGLE_API_KEY", "GEMINI_API_KEY")


def api_key() -> str:
    return os.getenv("VERTEX_API_KEY" if provider() == "vertex" else "STUDIO_API_KEY", "")


def _check_vertex_environment() -> None:
    found = [name for name in _SDK_KEY_VARIABLES if os.getenv(name)]
    if found:
        raise ModelCallError(
            f"{' and '.join(found)} is set, so the Google SDK would use it instead of VERTEX_API_KEY. "
            "Rename it to STUDIO_API_KEY in FORGE-1/.env."
        )


def _fallback_model() -> str | None:
    return os.getenv("FALLBACK_MODEL") or None


def _is_transient(error: Exception) -> bool:
    code = getattr(error, "code", None) or getattr(error, "status_code", None)
    if isinstance(code, int) and code in _TRANSIENT_CODES:
        return True
    name = type(error).__name__
    if "RateLimit" in name or "Timeout" in name or isinstance(error, TimeoutError):
        return True
    text = str(error)
    return any(s in text for s in ("UNAVAILABLE", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED", " 503", " 429"))


def _llm(model: str):
    # Imported here so modules that never call a model (and unit tests) do not need the provider package.
    from langchain_google_genai import ChatGoogleGenerativeAI

    if provider() == "vertex":
        _check_vertex_environment()
    # Vertex AI with an API key bound to the project ("express mode"): the key carries the project,
    # and project/location would require a service-account login instead of a key.
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key(),
        vertexai=provider() == "vertex",
        temperature=0,          # extraction should be repeatable (D-127)
        max_retries=0,          # retries are handled here
        timeout=60,
    )


def _invoke_once(model: str, schema: type[T], messages: list, usage: CallUsage) -> dict:
    started = time.perf_counter()
    try:
        result = _llm(model).with_structured_output(schema, include_raw=True).invoke(messages)
    finally:
        usage.calls += 1
        usage.latency_ms += int((time.perf_counter() - started) * 1000)
        usage.models.append(model)
    meta = getattr(result.get("raw"), "usage_metadata", None) or {}
    if meta:
        usage.prompt_tokens += int(meta.get("input_tokens") or 0)
        usage.completion_tokens += int(meta.get("output_tokens") or 0)
    else:
        usage.unknown_token_calls += 1
    return result


def _invoke_with_retries(schema: type[T], messages: list, task: str, usage: CallUsage) -> dict:
    """Primary model: up to 3 attempts while errors are transient. Then the fallback model once."""
    primary = model_for(task)
    last_error: Exception | None = None

    for attempt in range(len(_BACKOFF_SECONDS) + 1):
        if attempt:
            time.sleep(_BACKOFF_SECONDS[attempt - 1])
        try:
            return _invoke_once(primary, schema, messages, usage)
        except Exception as error:  # provider SDKs raise many types; classified by _is_transient
            last_error = error
            if not _is_transient(error):
                break  # bad request, auth or unknown model: retrying the same model will not help

    fallback = _fallback_model()
    if fallback and fallback != primary:
        try:
            return _invoke_once(fallback, schema, messages, usage)
        except Exception as error:
            last_error = error

    raise ModelCallError(f"{type(last_error).__name__}: {last_error}") from last_error


def call_structured(task: str, schema: type[T], system: str, user: str) -> tuple[T, CallUsage]:
    """
    Ask the model for output matching `schema`. Raises ModelCallError (provider failure) or
    InvalidOutputError (schema not met after one corrective retry).
    """
    usage = CallUsage()
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    result = _invoke_with_retries(schema, messages, task, usage)

    if result.get("parsed") is None:
        error = result.get("parsing_error") or "no structured output returned"
        retry_messages = messages + [HumanMessage(content=(
            "Your previous answer did not match the required JSON schema. "
            f"Error: {str(error)[:500]}. Answer again using exactly the schema."
        ))]
        result = _invoke_with_retries(schema, retry_messages, task, usage)
        if result.get("parsed") is None:
            raise InvalidOutputError(f"invalid structured output: {str(result.get('parsing_error'))[:300]}")

    return result["parsed"], usage
