# D:\FYP\FORGE-1\agents\clarification\graph.py
"""
Clarification Agent subgraph (v6 Section 7 and 17). It runs on the shared GraphState and is added
as one node of the Orchestrator graph, so it uses the Orchestrator's checkpointer for pauses.

N0 load_resources -> N1 sanitise_input -> N2 intake (N3 request scope is decided inside intake)
-> N4 ground_items -> N6 select_question -> N7 ask_user (interrupt) -> N8 interpret_answer -> back to N4
-> N9 draft_brief -> N10 check_brief (-> N11 repair) -> N12 build_confirmation
-> N13 await_confirmation (interrupt) -> N14 apply_confirmation (edit -> back to N4)
-> N15/N16 generate_tests -> N17 freeze
"""
from langgraph.graph import END, START, StateGraph

from agents.clarification import nodes
from agents.state import GraphState

_ENDED = ("failed", "out_of_scope", "cancelled", "replied")


def _ended(state: GraphState) -> bool:
    return state["clarification"].status in _ENDED


def _next_or_end(next_node: str):
    def route(state: GraphState) -> str:
        return END if _ended(state) else next_node
    return route


def _after_select(state: GraphState) -> str:
    if _ended(state):
        return END
    return "ask_user" if state["clarification"].status == "awaiting_answer" else "draft_brief"


def _after_check(state: GraphState) -> str:
    if _ended(state):
        return END
    return "build_confirmation" if state["clarification"].check.passed else "repair"


def _after_confirmation(state: GraphState) -> str:
    c = state["clarification"]
    if _ended(state):
        return END
    if c.status == "generating_tests":
        return "generate_tests"
    if c.status == "analysing":           # an edit was applied
        return "ground_items"
    return "build_confirmation"           # edit not possible: show the screen again


def build_clarification_graph():
    g = StateGraph(GraphState)
    for name in (
        "load_resources", "sanitise_input", "intake", "ground_items", "select_question", "ask_user",
        "interpret_answer", "draft_brief", "check_brief", "repair", "build_confirmation",
        "await_confirmation", "apply_confirmation", "generate_tests", "freeze",
    ):
        g.add_node(name, getattr(nodes, name))

    g.add_edge(START, "load_resources")
    g.add_conditional_edges("load_resources", _next_or_end("sanitise_input"))
    g.add_edge("sanitise_input", "intake")
    g.add_conditional_edges("intake", _next_or_end("ground_items"))
    g.add_edge("ground_items", "select_question")
    g.add_conditional_edges("select_question", _after_select)
    g.add_edge("ask_user", "interpret_answer")
    g.add_conditional_edges("interpret_answer", _next_or_end("ground_items"))
    g.add_edge("draft_brief", "check_brief")
    g.add_conditional_edges("check_brief", _after_check)
    g.add_edge("repair", "check_brief")
    g.add_edge("build_confirmation", "await_confirmation")
    g.add_edge("await_confirmation", "apply_confirmation")
    g.add_conditional_edges("apply_confirmation", _after_confirmation)
    g.add_conditional_edges("generate_tests", _next_or_end("freeze"))
    g.add_edge("freeze", END)
    return g.compile()   # no checkpointer here: it inherits the Orchestrator's
