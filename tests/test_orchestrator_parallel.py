"""The build runs its agents side by side (D-253, FR-05): the data branch and the frontend overlap in time, the
Integration Agent waits for both, and a database failure lets the frontend finish while integration reports it."""
import threading
import time
from datetime import datetime, timezone

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from agents import file_store
from agents.database_generator import agent as database_agent
from agents.frontend_generator import agent as frontend_agent
from agents.orchestrator import build_forge_graph
from agents.state import AgentArtifacts, RequestInfo, Stage, UsageSummary, initial_state
from test_backend_agent import salon_plan


@pytest.fixture
def build(monkeypatch):
    monkeypatch.setattr(file_store, "_active", file_store.MemoryFileStore())
    graph = build_forge_graph().compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "parallel-test"}}
    state = initial_state(RequestInfo(request_id="req_parallel", user_id="u", project_id="not-a-uuid", prompt="x",
                                      created_at=datetime.now(timezone.utc)))
    state["plan"] = salon_plan()
    state["control"].stage = Stage.GENERATING
    graph.update_state(config, state, as_node="after_planning")

    def run():
        events = [chunk for _, chunk in graph.stream(None, config, stream_mode=["custom"])]
        return graph.get_state(config).values, events
    return run


def _timed(real, spans, name, seconds=0.6):
    def run(*args, **kwargs):
        start = time.monotonic()
        time.sleep(seconds)                                  # stands in for the slow part of each agent
        out = real(*args, **kwargs)
        spans[name] = (start, time.monotonic(), threading.get_ident())
        return out
    return run


def test_the_data_branch_and_the_frontend_run_side_by_side(build, monkeypatch):
    spans = {}
    monkeypatch.setattr(database_agent, "run", _timed(database_agent.run, spans, "database"))
    monkeypatch.setattr(frontend_agent, "run", _timed(frontend_agent.run, spans, "frontend"))
    values, events = build()
    (d0, d1, dt), (f0, f1, ft) = spans["database"], spans["frontend"]
    assert d0 < f1 and f0 < d1 and dt != ft                  # the two spans overlap, on two threads
    arts = values["artifacts"]
    assert {a: arts[a].status for a in arts} == {"database": "done", "backend": "done", "frontend": "done",
                                                 "integration": "done"}
    lines = [e["message"] for e in events if e.get("message")]
    assert lines[-1] == "Your site is ready"                 # said once, after integration
    assert any(m.startswith("Integration: 3 parts joined") for m in lines)


def test_a_database_failure_lets_the_frontend_finish_and_integration_reports_it(build, monkeypatch):
    def broken(*args, **kwargs):
        raise database_agent.DatabaseBuildError("rule test failed")
    monkeypatch.setattr(database_agent, "run", broken)
    values, events = build()
    arts = values["artifacts"]
    assert arts["frontend"].status == "done" and arts["database"].status == "failed"
    assert arts["integration"].status == "failed" and "backend" not in arts
    lines = [e["message"] for e in events if e.get("message")]
    assert any("database part did not finish" in m for m in lines) and "Your site is ready" not in lines


def test_the_usage_of_both_branches_adds_up(build, monkeypatch):
    real = frontend_agent.run

    def costly(*args, **kwargs):
        arts, usage = real(*args, **kwargs)
        return arts, UsageSummary(calls=usage.calls + 2, estimated_cost_usd=usage.estimated_cost_usd + 0.01)
    monkeypatch.setattr(frontend_agent, "run", costly)
    values, _ = build()
    assert values["usage"].calls == 2 and isinstance(values["artifacts"]["frontend"], AgentArtifacts)
