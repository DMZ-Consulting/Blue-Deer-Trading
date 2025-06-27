#!/usr/bin/env python3
"""
Specialized agent that ONLY uses PolygonOptionsTools for market data retrieval.
This agent is designed to be called by other agents and focuses solely on API calls.
"""
import sys
sys.path.append(".")

from agno.agent import Agent
from toolkits.polygon_options import PolygonOptionsTools
from agno.models.openai import OpenAIChat
import os
from dotenv import load_dotenv
from agno.utils.pprint import pprint_run_response
from agno.storage.sqlite import SqliteStorage

load_dotenv()

def get_polygon_options_agent():
    """
    Create a specialized PolygonOptionsAgent that ONLY makes API calls.
    No reasoning, no analysis - just data retrieval.
    """
    
    # Validate API key
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise ValueError("POLYGON_API_KEY environment variable is required")
    
    agent = Agent(
        model=OpenAIChat(id="gpt-4.1"),
        name="PolygonOptionsAgent", 
        role=(
            "Options Market Data Specialist. You are a focused data retrieval specialist. "
            "Your ONLY job is to use the PolygonOptionsTools and return the results. "
            "You do NOT analyze, reason, or interpret data - you just fetch it efficiently. "
            "CRITICAL: You MUST EXECUTE the actual tool methods, not just identify them."
        ),
        tools=[PolygonOptionsTools()],
        instructions=[
            "ALWAYS use the actual tool calls - do NOT return code or descriptions",
            "EXECUTE the tool method and return the actual results from the API",
            "You NEVER analyze or interpret data - just retrieve and return raw results",
            "You do NOT use reasoning tools - only PolygonOptionsTools methods",
            "",
            "WORKFLOW FOR EACH REQUEST:",
            "1. Parse the request to extract required parameters (dates, ticker, etc.)",
            "2. Format the options ticker if needed (e.g., NVDA $118 Call -> O:NVDA250516C00118000)",
            "3. EXECUTE the appropriate methods with the parameters. You can use multiple tool calls in a single request. "
            "Your objective is to return AS MUCH DATA AS POSSIBLE relevant to the request. "
            "Include data that may be just outside of the specified time frame for completeness of context. Ensure to and from dates are open market dates."
            "Always get the aggregates for the request. If the request is for a specific date, get the aggregates for the entire day. If it is for a range of dates, get the aggregates for the entire range."
            "Infer what the best aggregation size is (minute, hour, day, week, month, year).",
            "4. Return the API results",
        ],
        show_tool_calls=True,
        add_datetime_to_instructions=True,
        markdown=True,
        debug_mode=True,
        storage=SqliteStorage(table_name="polygon_options_agent_results", db_file="./tmp/polygon_options_agent_results.db"),
    )
    
    return agent

def main():
    """Test the specialized polygon options agent"""
    print("🔧 Testing PolygonOptionsAgent")
    print("=" * 50)
    
    try:
        agent = get_polygon_options_agent()
        print("✅ PolygonOptionsAgent initialized")
        
        # Test query
        query = """<task>                                                                                                                                        
      Please retrieve historical market data for NVDA $118 Call option expiring on 2025-05-16 for the period between 2025-05-06 and 2025-05-13.     
      Include price, volume, and volatility data.                                                                                                   
      </task>                                                                                                                                       
                                                                                                                                                    
      <expected_output>                                                                                                                             
      Historical market data including price movements, volume, and volatility metrics for the specified options contract during the trade period.  
      </expected_output> """  
        
        print(f"\n🎯 Testing query: {query}")
        print("-" * 50)
        
        response = agent.run(query)
        pprint_run_response(response)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 