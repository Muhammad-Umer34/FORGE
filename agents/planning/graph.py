# D:\FYP\FORGE-1\agents\planning\graph.py
"""
Planning Agent subgraph (plan v2 §5, D-204). It runs on the shared GraphState and is added as one node of the
Orchestrator graph, so it uses the Orchestrator's checkpointer for the plan-approval pause.

check_input -> design_site (call 1) -> design_data (call 2, skipped when nothing is stored) -> assemble_plan
-> check_plan (-> fix_plan -> assemble_plan, at most 2 rounds) -> write_texts (call 3) (-> rewrite_texts, once)
-> finish_texts -> await_plan_approval (interrupt) -> apply_change -> assemble_plan ... | freeze
"""
from langgraph.graph import END, START, StateGraph

from agents.planning import nodes
from agents.state import GraphState

_ENDED = ("failed", "cancelled")


def _status(state: GraphState) -> str:
    return state["planning"].status


def _next_or_end(next_node: str):
    def route(state: GraphState) -> str:
        return END if _status(state) in _ENDED else next_node
    return route


def _after_check(state: GraphState) -> str:
    return {"failed": END, "checking": "fix_plan", "awaiting_approval": "await_plan_approval"}.get(
        _status(state), "write_texts")


def _after_write(state: GraphState) -> str:
    if _status(state) in _ENDED:
        return END
    p, limits = state["planning"], state["run_config"].limits
    return "rewrite_texts" if p.issues and p.text_rewrites_used < limits.max_text_rewrites else "finish_texts"


def _after_finish(state: GraphState) -> str:
    return END if _status(state) in _ENDED else "await_plan_approval"


def _after_decision(state: GraphState) -> str:
    return {"done": "freeze", "changing": "apply_change"}.get(_status(state), END)


def _after_change(state: GraphState) -> str:
    return {"failed": END, "awaiting_approval": "await_plan_approval"}.get(_status(state), "assemble_plan")


def build_planning_graph():
    g = StateGraph(GraphState)
    for name in ("check_input", "design_site", "design_data", "assemble_plan", "check_plan", "fix_plan",
                 "write_texts", "rewrite_texts", "finish_texts", "await_plan_approval", "apply_change", "freeze"):
        g.add_node(name, getattr(nodes, name))

    g.add_edge(START, "check_input")
    g.add_conditional_edges("check_input", _next_or_end("design_site"))
    g.add_conditional_edges("design_site", _next_or_end("design_data"))
    g.add_conditional_edges("design_data", _next_or_end("assemble_plan"))
    g.add_edge("assemble_plan", "check_plan")
    g.add_conditional_edges("check_plan", _after_check)
    g.add_conditional_edges("fix_plan", _next_or_end("assemble_plan"))
    g.add_conditional_edges("write_texts", _after_write)
    g.add_conditional_edges("rewrite_texts", _next_or_end("finish_texts"))
    g.add_conditional_edges("finish_texts", _after_finish)
    g.add_conditional_edges("await_plan_approval", _after_decision)
    g.add_conditional_edges("apply_change", _after_change)
    g.add_edge("freeze", END)
    return g.compile()   # no checkpointer here: it inherits the Orchestrator's
