# D:\FYP\FORGE-1\agents\gateway.py
"""
Minimal LLM gateway (decisions D-128, D-138). Every model call made by an agent goes through
call_structured(), so agents contain no provider code. The gateway:
  * picks the model for a task from the environment (the single FORGE-1/.env),
  * sends every call to one provider: Vertex AI (Google Cloud, uses the project's credits) or the
    Google AI Studio API, or OpenRouter (many makers' models, D-218), chosen by LLM_PROVIDER (D-184),
  * asks for structured output that matches a Pydantic schema,
  * retries an invalid output once, sending the parse error back to the model,
  * retries transient provider errors (HTTP 429/5xx, timeouts) with backoff, then tries
    the fallback model once (D-121, D-140),
  * returns the usage of the call (tokens, latency, estimated cost) for the run's usage totals,
  * refuses a call once the run has spent its budget (D-216).

The per-call LLM_CALL database record is written later by the API layer (D-133).
"""
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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
    "planning": "PLANNING_MODEL",            # design and text calls: the strongest model (plan v2 §1)
    "planning_fix": "PLANNING_FIX_MODEL",    # fix rounds and plan changes: a faster model
}
_DEFAULT_MODEL = "gemini-3.8-flash"
_TRANSIENT_CODES = {408, 429, 500, 502, 503, 504}
_BACKOFF_SECONDS = (1.0, 3.0)          # PLACEHOLDER: waits before the 2nd and 3rd attempt
# PLACEHOLDER: longest reply a call may write, thinking included. The longest real one (a site's text) is far below;
# an OpenRouter reply once ran to 131,072 tokens and failed (KI-23).
MAX_OUTPUT_TOKENS = 32_768

# USD per 1M tokens (input, output), Vertex AI, prompts under 200k tokens. Checked 2026-11-13 on
# cloud.google.com/vertex-ai/generative-ai/pricing (D-216). Update when a model or price changes.
PRICES = {
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-3.8-flash": (0.75, 3.75),          # introductory price until 2026-12-31
    "gemini-3.1-flash-lite": (0.75, 3.75),     # not listed: priced as Flash so the estimate is never low
    # OpenRouter (openrouter.ai/api/v1/models, 2026-11-13), D-218
    "openai/gpt-6-luna": (0.10, 0.50),
    "xiaomi/mimo-v2.6-pro": (0.435, 0.87),
    "deepseek/deepseek-v4.1-flash": (0.30, 1.20),
    "z-ai/glm-5.3-flash": (0.04, 0.078),
    "deepseek/deepseek-v4-flash-0731": (0.043, 0.30),
}
_UNKNOWN_PRICE = PRICES["gemini-2.5-pro"]     # an unlisted model is priced like the dearest one


class ModelCallError(Exception):
    """The call failed for good. Nodes turn this into a FAILED run with category 'system'."""


class InvalidOutputError(ModelCallError):
    """The model returned output that does not match the schema, twice."""


SPENDING_LIMIT = "the run reached its spending limit"
SPENDING_LIMIT_MESSAGE = ("This request used up its AI budget before it finished. Please start again with a "
                          "shorter description.")


class BudgetExceededError(InvalidOutputError):
    """The run has spent its budget. Steps handle it like output that failed twice: the run ends as failed
    (not paused), because continuing it would only hit the same limit again (D-216)."""


@dataclass
class CallUsage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    unknown_token_calls: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    models: list[str] = field(default_factory=list)


def cost_of(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price_in, price_out = PRICES.get(model, _UNKNOWN_PRICE)
    return (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000


def model_for(task: str) -> str:
    return os.getenv(_TASK_MODEL_ENV.get(task, ""), "") or _DEFAULT_MODEL


def provider() -> str:
    """'vertex', 'studio' or 'openrouter' (D-218). LLM_PROVIDER decides; if it is not set, Vertex AI is used whenever
    VERTEX_API_KEY exists. Primary and fallback model always use the same provider, so all spending
    lands on one bill (D-184)."""
    chosen = os.getenv("LLM_PROVIDER", "").strip().lower()
    if chosen in ("vertex", "studio", "openrouter"):
        return chosen
    return "vertex" if os.getenv("VERTEX_API_KEY") else "studio"


# The Google SDK reads these two by itself and, in Vertex mode, prefers them over the key we pass,
# so the AI Studio key is stored as STUDIO_API_KEY instead (D-184).
_SDK_KEY_VARIABLES = ("GOOGLE_API_KEY", "GEMINI_API_KEY")
# Clients are built one at a time: in Vertex mode the Google SDK puts the key in GOOGLE_API_KEY while it builds a
# client, and a check running in another thread at that moment would refuse (seen in the first parallel eval run).
_CLIENT_LOCK = threading.Lock()


_KEY_VARIABLE = {"vertex": "VERTEX_API_KEY", "studio": "STUDIO_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
OPENROUTER_URL = "https://openrouter.ai/api/v1"


def api_key() -> str:
    return os.getenv(_KEY_VARIABLE[provider()], "")


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
    if provider() == "openrouter":
        return _openrouter_client(model)
    # Vertex AI with an API key bound to the project ("express mode"): the key carries the project,
    # and project/location would require a service-account login instead of a key.
    with _CLIENT_LOCK:   # the Google SDK sets GOOGLE_API_KEY for a moment while it builds a Vertex client
        if provider() == "vertex":
            _check_vertex_environment()
        return _google_client(model)


def _openrouter_client(model: str):
    """OpenRouter speaks the OpenAI API, so the OpenAI LangChain client is used with OpenRouter's address (D-218).
    Model ids carry the maker, e.g. "xiaomi/mimo-v2.6-pro"."""
    from langchain_openai import ChatOpenAI   # imported here: only needed when OpenRouter is the provider

    return ChatOpenAI(
        model=model,
        api_key=api_key(),
        base_url=OPENROUTER_URL,
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=0,          # extraction should be repeatable (D-127)
        max_retries=0,          # retries are handled here
        timeout=60,
    )


def _google_client(model: str):
    # Imported here so modules that never call a model (and unit tests) do not need the provider package.
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key(),
        vertexai=provider() == "vertex",
        max_output_tokens=MAX_OUTPUT_TOKENS,
        temperature=0,          # extraction should be repeatable (D-127)
        max_retries=0,          # retries are handled here
        timeout=60,
    )


def _invoke_once(model: str, schema: type[T] | None, messages: list, usage: CallUsage) -> dict:
    """One call. With a schema: structured output; without (file-output mode): the reply as plain text in "raw"."""
    started = time.perf_counter()
    try:
        llm = _llm(model)
        if schema:
            result = llm.with_structured_output(schema, include_raw=True).invoke(messages)
        else:
            raw = llm.invoke(messages)
            result = {"raw": raw, "parsed": raw.text}
    finally:
        usage.calls += 1
        usage.latency_ms += int((time.perf_counter() - started) * 1000)
        usage.models.append(model)
    meta = getattr(result.get("raw"), "usage_metadata", None) or {}
    if meta:
        tokens_in, tokens_out = int(meta.get("input_tokens") or 0), int(meta.get("output_tokens") or 0)
        usage.prompt_tokens += tokens_in
        usage.completion_tokens += tokens_out
        usage.cost_usd += cost_of(model, tokens_in, tokens_out)
    else:
        usage.unknown_token_calls += 1
    return result


def _invoke_with_retries(schema: type[T] | None, messages: list, task: str, usage: CallUsage) -> dict:
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


def call_structured(task: str, schema: type[T], system: str, user: str,
                    budget_usd: float | None = None) -> tuple[T, CallUsage]:
    """
    Ask the model for output matching `schema`. Raises ModelCallError (provider failure),
    InvalidOutputError (schema not met after one corrective retry) or BudgetExceededError (`budget_usd`,
    what the run may still spend, is used up).
    """
    if budget_usd is not None and budget_usd <= 0:
        raise BudgetExceededError(SPENDING_LIMIT)
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


# ---------------------------------------------------------------- file-output mode (Phase 3, D-228)
_FILE_BLOCK = re.compile(r'<file path="(?P<path>[^"]+)">\n?(?P<body>.*?)\n?</file>', re.DOTALL)
FILE_FORMAT = ('Answer with the files only, each as <file path="relative/path.tsx">...the whole file...</file>. '
               "No other text and no Markdown code fences.")


def parse_files(text: str) -> dict[str, str]:
    """`<file path="...">` blocks -> {path: content}. Paths must be relative and stay inside the site."""
    files = {}
    for m in _FILE_BLOCK.finditer(text):
        path = m["path"].strip().replace("\\", "/")
        if path.startswith("/") or ".." in path.split("/") or not path:
            raise ValueError(f"file path not allowed: {path!r}")
        body = re.sub(r"^```\w*\n|\n```\s*$", "", m["body"])    # a fence the model added anyway
        files[path] = body if body.endswith("\n") else body + "\n"
    if not files:
        raise ValueError('no <file path="..."> block found')
    return files


def call_files(task: str, system: str, user: str, budget_usd: float | None = None) -> tuple[dict[str, str], CallUsage]:
    """Ask for whole files as `<file path="...">` blocks (code is written more reliably as plain text than inside
    JSON; Bolt and Lovable use the same pattern). One corrective retry when no valid block comes back."""
    if budget_usd is not None and budget_usd <= 0:
        raise BudgetExceededError(SPENDING_LIMIT)
    usage = CallUsage()
    messages = [SystemMessage(content=f"{system}\n\n{FILE_FORMAT}"), HumanMessage(content=user)]
    text = _invoke_with_retries(None, messages, task, usage)["parsed"]
    try:
        return parse_files(text), usage
    except ValueError as error:
        retry = messages + [HumanMessage(content=f"Your answer could not be read: {error}. {FILE_FORMAT}")]
        text = _invoke_with_retries(None, retry, task, usage)["parsed"]
        try:
            return parse_files(text), usage
        except ValueError as again:
            raise InvalidOutputError(f"no usable files: {again}") from again


RESERVE_PER_CALL_USD = 0.05          # PLACEHOLDER: held back for each call still running (a custom part on Pro ~ $0.04)
MAX_PARALLEL_CALLS = 3               # D-228


def call_files_parallel(jobs: list[tuple[str, str, str]], budget_usd: float,
                        max_parallel: int = MAX_PARALLEL_CALLS) -> list[tuple[dict[str, str] | Exception, CallUsage]]:
    """Several file calls (task, system, user) at once, at most `max_parallel`. The spending cap counts the calls
    still running: each call holds RESERVE_PER_CALL_USD until it ends and then pays its real cost, so parallel
    calls cannot overshoot the budget (D-216, D-228). Results keep the jobs' order; a failed job gives its error."""
    lock, left = threading.Lock(), [budget_usd]

    def one(job):
        with lock:
            if left[0] - RESERVE_PER_CALL_USD < 0:
                return BudgetExceededError(SPENDING_LIMIT), CallUsage()
            left[0] -= RESERVE_PER_CALL_USD
        usage = CallUsage()
        try:
            files, usage = call_files(*job)
            return files, usage
        except Exception as error:      # one part failing must not stop the others (fallback section, D-230)
            return error, usage
        finally:
            with lock:
                left[0] += RESERVE_PER_CALL_USD - usage.cost_usd

    with ThreadPoolExecutor(max_workers=max_parallel) as pool:
        return list(pool.map(one, jobs))
