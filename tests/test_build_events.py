"""Progress events of a running build reach the studio as server-sent events (D-233). No database needed."""
import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes import requests as routes
from backend.services import requests as service


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes._owned_request] = lambda request_id: request_id
    return TestClient(app)


def test_events_stream_the_runs_progress_then_end():
    routes.progress["req_ev1"] = [{"stage": "build", "message": "Saving your approved plan"}]
    body = _client().get("/api/projects/00000000-0000-0000-0000-000000000000/requests/req_ev1/events").text
    assert 'data: {"stage": "build", "message": "Saving your approved plan"}' in body
    assert body.rstrip().endswith("event: end\ndata: {}")


def test_events_wait_while_the_run_is_working():
    async def scenario():
        async with service.one_step_at_a_time("req_ev2"):
            routes.progress["req_ev2"] = []
            assert "req_ev2" in service.running_ids()
        assert "req_ev2" not in service.running_ids()

    asyncio.run(scenario())
