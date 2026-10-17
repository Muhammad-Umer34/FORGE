# D:\FYP\FORGE-1\agents\orchestrator\graph.py
from langgraph.graph import END, START, StateGraph

from agents.clarification import build_clarification_graph
from agents.state import GraphState, Stage

# Clarification status -> Orchestrator stage. The Orchestrator is the only writer of `control`.
_STAGE_AFTER_CLARIFICATION = {
    "done": Stage.RETRIEVING,
    "failed": Stage.FAILED,
    "out_of_scope": Stage.OUT_OF_SCOPE,
    "cancelled": Stage.CANCELLED,
    "replied": Stage.REPLIED,
}


def after_clarification(state: GraphState) -> dict:
    """Join node: turn the Clarification Agent's end status into the run's stage."""
    c = state["clarification"]
    control = state["control"].model_copy(deep=True)
    control.stage = _STAGE_AFTER_CLARIFICATION.get(c.status, Stage.FAILED)
    if control.stage == Stage.FAILED:
        control.failed = True
        control.failure_reason = c.failure.message if c.failure else "The request could not be clarified."
    return {"control": control}


def build_forge_graph():
    """
    Constructs the master LangGraph workflow for the FORGE autonomous builder.
    Only the Clarification Agent is wired so far; the run stops at RETRIEVING until
    Context Retrieval is built. Compile it with a checkpointer (pauses need one).
    """
    builder = StateGraph(GraphState)
    builder.add_node("clarification", build_clarification_graph())
    builder.add_node("after_clarification", after_clarification)
    builder.add_edge(START, "clarification")
    builder.add_edge("clarification", "after_clarification")
    builder.add_edge("after_clarification", END)
    return builder
