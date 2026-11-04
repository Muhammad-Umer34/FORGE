from langgraph.graph import END, START, StateGraph

from agents.clarification import build_clarification_graph
from agents.planning import build_planning_graph
from agents.retrieval.ranker import rank_and_retrieve_components
from agents.state import GraphState, Stage

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
    return {"retrieval": rank_and_retrieve_components(state["brief"]),
            **_set_stage(state, Stage.PLANNING, "")}


def after_planning(state: GraphState) -> dict:
    p = state["planning"]
    return _set_stage(state, _STAGE_AFTER_PLANNING.get(p.status, Stage.FAILED),
                      p.failure.message if p.failure else "The site could not be planned.")


def _route_after_clarification(state: GraphState) -> str:
    return "retrieval" if state["control"].stage == Stage.RETRIEVING else END


def build_forge_graph():
    """
    Constructs the master LangGraph workflow for the FORGE autonomous builder.
    Clarification -> Context Retrieval -> Planning are wired; the run stops at GENERATING until the
    builder agents exist. Compile it with a checkpointer (pauses need one).
    """
    builder = StateGraph(GraphState)
    builder.add_node("clarification", build_clarification_graph())
    builder.add_node("after_clarification", after_clarification)
    builder.add_node("retrieval", retrieval)
    builder.add_node("planning", build_planning_graph())
    builder.add_node("after_planning", after_planning)
    builder.add_edge(START, "clarification")
    builder.add_edge("clarification", "after_clarification")
    builder.add_conditional_edges("after_clarification", _route_after_clarification)
    builder.add_edge("retrieval", "planning")
    builder.add_edge("planning", "after_planning")
    builder.add_edge("after_planning", END)
    return builder
