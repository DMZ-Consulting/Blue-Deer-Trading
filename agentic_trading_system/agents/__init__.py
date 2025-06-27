"""
Agent factory for the agentic trading system.
"""
from .strategy_researcher import create_strategy_research_agent
from .analysis_method_developer import create_analysis_method_agent
from .knowledge_updater import create_knowledge_updater_agent

def create_all_agents(knowledge_base=None):
    """
    Returns a dictionary of all core agents. If knowledge_base is required, it must be provided.
    """
    agents = {
        "strategy_research": create_strategy_research_agent(),
        "analysis_method": create_analysis_method_agent(),
    }
    if knowledge_base is not None:
        agents["knowledge_updater"] = create_knowledge_updater_agent(knowledge_base)
    return agents 