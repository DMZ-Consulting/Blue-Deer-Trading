"""
Agent definition for converting research into testable analysis methods.
"""
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from pydantic import BaseModel, Field
from typing import List
import os
from dotenv import load_dotenv
from agents.postgres_agent import get_postgres_tools

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

class AnalysisMethod(BaseModel):
    """New analysis method discovered"""
    method_name: str = Field(..., description="Name of the analysis method")
    purpose: str = Field(..., description="What this method reveals")
    sql_description: str = Field(..., description="SQL query description for this analysis")
    bucketing_criteria: str = Field(..., description="How to group/bucket the data")
    interpretation_guide: str = Field(..., description="How to interpret results")
    validation_criteria: str = Field(..., description="How to validate findings")

class StrategyTestResults(BaseModel):
    """Results from testing a strategy against data"""
    strategy_name: str
    test_description: str
    sql_query: str
    results_summary: str
    statistical_significance: str
    actionable_insights: List[str]
    recommended_actions: List[str]

def create_analysis_method_agent() -> Agent:
    """Agent that converts research into concrete analysis methods"""
    return Agent(
        name="Analysis Method Agent", 
        role="Convert strategy research into testable analysis methods",
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools(add_instructions=True), get_postgres_tools()],
        instructions=[
            "You convert trading strategy research into concrete, testable analysis methods.",
            "Focus on creating SQL query descriptions that can reveal strategy patterns in data. These are english descriptions of the SQL query, not the query itself.",
            "Design bucketing and grouping criteria that expose meaningful patterns.",
            "Provide clear interpretation guidelines for analysis results.",
            "Ensure methods are statistically sound and practically applicable.",
            "Create validation criteria to test the significance of findings.",
            "You can use the postgres tools to get the schema of the database tables. You can also use the reasoning tools to reason about the data.",
        ],
        response_model=AnalysisMethod,
        add_datetime_to_instructions=True,
        markdown=True,
        debug_mode=debug_mode,
    )

if __name__ == "__main__":
    from agno.utils.pprint import pprint_run_response
    agent = create_analysis_method_agent()
    prompt = "Given trading data with entry/exit times, symbols, and PnL, suggest a novel SQL analysis method."
    print("\n[Manual Test] Running Analysis Method Agent...")
    response = agent.run(prompt)
    pprint_run_response(response)
