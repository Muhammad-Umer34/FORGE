# D:\FYP\FORGE-1\agents\tracing.py
"""
Langfuse tracing of runs (D-215). The model is called through LangChain, so one callback handler on the run's
config records every graph step and every model call (prompt, output, model, tokens, time), nested by agent and
step. Tracing is on only when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set in FORGE-1/.env
(LANGFUSE_BASE_URL picks the server: Langfuse Cloud or a self-hosted one). Without them nothing changes.
"""
import os


def enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def run_config(request_id: str, tags: tuple[str, ...] = ()) -> dict:
    """Config for graph.ainvoke: the run's thread, plus the tracer when tracing is on. One request is one Langfuse
    session, so every step of a run (each answer, confirm and approval) is grouped under it."""
    config: dict = {"configurable": {"thread_id": request_id}}
    if enabled():
        from langfuse.langchain import CallbackHandler   # imported here: tests and runs without tracing skip it

        config["callbacks"] = [CallbackHandler()]
        config["metadata"] = {"langfuse_session_id": request_id, "langfuse_tags": list(tags)}
    return config


def flush() -> None:
    """Send buffered traces now. Scripts call it before exiting; the server sends them in the background."""
    if enabled():
        from langfuse import get_client

        get_client().flush()
