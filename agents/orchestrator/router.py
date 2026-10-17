# D:\FYP\FORGE-1\agents\orchestrator\router.py
from agents.state import GraphState, Stage


def route_stage(state: GraphState) -> str:
    """
    Primary orchestrator stage router inspecting ControlState.stage.
    Returns the next node name or target stage.
    """
    control = state.get("control")
    if not control:
        return Stage.CLARIFYING.value

    if control.failed:
        return Stage.FAILED.value

    return control.stage.value
