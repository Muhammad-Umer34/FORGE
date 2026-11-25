from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from agents.clarification import build_clarification_graph
from agents.planning import build_planning_graph
from agents.retrieval.ranker import rank_and_retrieve_components
from agents.frontend_generator import agent as frontend_agent
from agents.backend_generator import agent as backend_agent
from agents.database_generator import agent as database_agent
from agents.state import GraphState, Stage, budget_left

# Clarification status -> Orchestrator stage. The Orchestrator is the only writer of `control`.
_STAGE_AFTER_CLARIFICATION = {
    "done": Stage.RETRIEVING,
    "failed": Stage.FAILED,
    "out_of_scope": Stage.OUT_OF_SCOPE,
    "cancelled": Stage.CANCELLED,
    "replied": Stage.REPLIED,
}
_STAGE_AFTER_PLANNING = {"done": Stage.GENERATING, "cancelled": Stage.CANCELLED}


def _set_stage(state: GraphState, stage: Stage, failure: str) -> dict:
    control = state["control"].model_copy(deep=True)
    control.stage = stage
    if stage == Stage.FAILED:
        control.failed = True
        control.failure_reason = failure
    return {"control": control}


def after_clarification(state: GraphState) -> dict:
    """Join node: turn the Clarification Agent's end status into the run's stage."""
    c = state["clarification"]
    return _set_stage(state, _STAGE_AFTER_CLARIFICATION.get(c.status, Stage.FAILED),
                      c.failure.message if c.failure else "The request could not be clarified.")


def retrieval(state: GraphState) -> dict:
    """Context Retrieval (D-203): code only, so it is a plain node."""
    usage = state.get("usage")
    spent = usage.estimated_cost_usd if usage else 0.0
    return {"retrieval": rank_and_retrieve_components(state["brief"]),
            "planning": state["planning"].model_copy(update={"spent_before_usd": spent}),   # for the budget (D-216)
            **_set_stage(state, Stage.PLANNING, "")}


def after_planning(state: GraphState) -> dict:
    p = state["planning"]
    return _set_stage(state, _STAGE_AFTER_PLANNING.get(p.status, Stage.FAILED),
                      p.failure.message if p.failure else "The site could not be planned.")


def build_site(state: GraphState) -> dict:
    """The builder step (Phase 3): the database agent makes the site's storage from the plan's data (D-242 - D-245),
    the backend agent writes the site's form specs and checks, and proves them on that storage (D-247), then the
    frontend agent writes the site (D-240), with a live preview and the build gate when the run's config turns them
    on. Repeat-safe: an unchanged file is not written again (P13)."""
    brief = state.get("brief")
    request = state["request"]
    stored: dict = {}
    database = database_agent.run(state["plan"], request.request_id, request.project_id, state["run_config"],
                                  get_stream_writer(), report=stored)
    storage = None
    if stored.get("db_schema"):
        from backend.services.site_data import Storage
        storage = Storage(request.project_id, stored["db_schema"], stored["db_role"], stored["db_contract"])
    backend = backend_agent.run(state["plan"], request.request_id, request.project_id, state["run_config"],
                                get_stream_writer(), storage)
    artifacts, usage = frontend_agent.run(state["plan"], brief.business_type if brief else None,
                                          state["request"].request_id, state["run_config"], get_stream_writer(),
                                          budget_left(state))   # custom parts spend only what the run has left
    return {"artifacts": {"database": database, "backend": backend, "frontend": artifacts}, "usage": usage}


def _route_after_planning(state: GraphState) -> str:
    return "build_site" if state["control"].stage == Stage.GENERATING else END


def _route_after_clarification(state: GraphState) -> str:
    return "retrieval" if state["control"].stage == Stage.RETRIEVING else END


def build_forge_graph():
    """
    Constructs the master LangGraph workflow for the FORGE autonomous builder.
    Clarification -> Context Retrieval -> Planning -> build step. The build step stays at GENERATING until the
    builder agents exist (Phase 3 Group 3). Compile it with a checkpointer (pauses need one).
    """
    builder = StateGraph(GraphState)
    builder.add_node("clarification", build_clarification_graph())
    builder.add_node("after_clarification", after_clarification)
    builder.add_node("retrieval", retrieval)
    builder.add_node("planning", build_planning_graph())
    builder.add_node("after_planning", after_planning)
    builder.add_node("build_site", build_site)
    builder.add_edge(START, "clarification")
    builder.add_edge("clarification", "after_clarification")
    builder.add_conditional_edges("after_clarification", _route_after_clarification)
    builder.add_edge("retrieval", "planning")
    builder.add_edge("planning", "after_planning")
    builder.add_conditional_edges("after_planning", _route_after_planning)
    builder.add_edge("build_site", END)
    return builder
