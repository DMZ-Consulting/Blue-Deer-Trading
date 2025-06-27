"""
Agent definition for researching new trading strategies and methods.
"""
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.firecrawl import FirecrawlTools
from agno.tools.reasoning import ReasoningTools
from pydantic import BaseModel, Field
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

class TradingStrategyResearch(BaseModel):
    """Research findings about trading strategies"""
    strategy_name: str = Field(..., description="Name of the trading strategy")
    strategy_type: str = Field(..., description="Category (momentum, mean_reversion, etc.)")
    description: str = Field(..., description="Detailed description of the strategy")
    key_indicators: List[str] = Field(..., description="Key indicators or signals used")
    typical_timeframes: List[str] = Field(..., description="Common timeframes for this strategy")
    market_conditions: str = Field(..., description="Best market conditions for this strategy")
    risk_characteristics: str = Field(..., description="Risk profile and characteristics")
    sources: List[str] = Field(..., description="Sources of information")

class TradingStrategyResearchList(BaseModel):
    """List of trading strategies"""
    strategies: List[TradingStrategyResearch] = Field(..., description="List of trading strategies")

def create_strategy_research_agent() -> Agent:
    """Agent that researches new trading strategies and methods"""
    return Agent(
        name="Strategy Research Agent",
        role="Research new trading strategies and analysis methods",
        model=OpenAIChat(id="gpt-4.1-mini"),
        tools=[
            FirecrawlTools(search=True, scrape=True, mapping=True),
            ReasoningTools(add_instructions=True)
        ],
        instructions=[
            "You are an expert trading strategy researcher specializing in discovering new approaches.",
            "Research academic papers, industry reports, and trading methodologies.",
            "Focus on finding novel ways to analyze trading data and identify profitable patterns.",
            "Look for both well-established and cutting-edge trading techniques.",
            "Always provide credible sources for your research findings.",
            "Structure your findings in a clear, actionable format.",
            "Return a list of strategies as a JSON array, each matching the TradingStrategyResearch schema.",
        ],
        response_model=TradingStrategyResearch,
        add_datetime_to_instructions=True,
        markdown=True,
        debug_mode=debug_mode,
    )

if __name__ == "__main__":
    from agno.utils.pprint import pprint_run_response
    agent = create_strategy_research_agent()
    prompt = "Research momentum trading strategies and provide a list of strategies as a JSON array."
    print("\n[Manual Test] Running Strategy Research Agent...")
    response = agent.run(prompt)
    pprint_run_response(response)
