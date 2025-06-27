"""
Team definition for coordinating trading strategy research and method development.
"""
from agno.team import Team
from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools
from agents.strategy_researcher import create_strategy_research_agent
from agents.analysis_method_developer import create_analysis_method_agent

import os
from dotenv import load_dotenv

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

def create_research_team() -> Team:
    """Team that researches and discovers new trading strategies"""
    research_agent = create_strategy_research_agent()
    method_agent = create_analysis_method_agent()
    
    return Team(
        name="Strategy Research Team",
        mode="coordinate",
        model=Claude(id="claude-3-7-sonnet-latest"),
        members=[research_agent, method_agent],
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            "You coordinate research into new trading strategies and analysis methods.",
            "First, have the research agent investigate specific strategy areas or questions.",
            "Then, have the method agent convert findings into testable analysis methods.",
            "Focus on practical, implementable strategies that can be tested with SQL.",
            "Ensure all methods have clear validation criteria and interpretation guides.",
            "Prioritize novel approaches that aren't already in the knowledge base.",
        ],
        markdown=True,
        show_members_responses=True,
        enable_agentic_context=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )

if __name__ == "__main__":
    from agno.utils.pprint import pprint_run_response
    team = create_research_team()
    prompt = "Research new momentum trading strategies and analysis methods."
    print("\n[Manual Test] Running Research Team...")
    response = team.run(prompt)
    pprint_run_response(response)
