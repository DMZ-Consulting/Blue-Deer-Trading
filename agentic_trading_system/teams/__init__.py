"""
Team factory for the agentic trading system.
"""
from .research_team import create_research_team
from .analysis_team import create_analysis_team

def create_all_teams(knowledge_base=None):
    """
    Returns a dictionary of all core teams. If knowledge_base is required, it must be provided.
    """
    teams = {
        "research_team": create_research_team(),
    }
    if knowledge_base is not None:
        teams["analysis_team"] = create_analysis_team(knowledge_base)
    return teams 