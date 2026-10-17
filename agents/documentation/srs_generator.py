# D:\FYP\FORGE-1\agents\documentation\srs_generator.py
from agents.state import ClarifiedBrief, BuildPlan


def generate_srs_document(brief: ClarifiedBrief, plan: BuildPlan) -> str:
    """
    Generates a formal Software Requirements Specification (SRS) markdown document.
    """
    return "# Software Requirements Specification\n"
