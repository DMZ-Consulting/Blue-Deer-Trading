#!/usr/bin/env python3
"""
Specialized agent that ONLY uses ThetaDataOptionsTools for market data retrieval.
This agent is designed to be called by other agents and focuses solely on API calls.
"""
import sys
sys.path.append(".")

from agno.agent import Agent
from toolkits.theta_data_options import ThetaDataOptionsTools
from agno.models.openai import OpenAIChat
import os
from dotenv import load_dotenv
from agno.utils.pprint import pprint_run_response
from agno.storage.sqlite import SqliteStorage

load_dotenv()

def get_theta_data_agent():
    """
    Create a specialized ThetaDataAgent that ONLY makes API calls.
    No reasoning, no analysis - just data retrieval using Theta Data.
    """
    
    agent = Agent(
        model=OpenAIChat(id="gpt-4.1"),
        name="ThetaDataAgent", 
        role=(
            "Options Market Data Specialist using Theta Data. You are a focused data retrieval specialist. "
            "Your ONLY job is to use the ThetaDataOptionsTools and return the results. "
            "You do NOT analyze, reason, or interpret data - you just fetch it efficiently. "
            "CRITICAL: You MUST EXECUTE the actual tool methods, not just identify them."
        ),
        tools=[ThetaDataOptionsTools()],
        instructions=[
            "ALWAYS use the actual tool calls - do NOT return code or descriptions",
            "EXECUTE the tool method and return the actual results from the API",
            "You NEVER analyze or interpret data - just retrieve and return raw results",
            "You do NOT use reasoning tools - only ThetaDataOptionsTools methods",
            "",
            "WORKFLOW FOR EACH REQUEST:",
            "1. Parse the request to extract required parameters (dates, ticker, strike, expiration, etc.)",
            "2. Convert parameters to Theta Data format:",
            "   - Dates: YYYYMMDD format (e.g., 20250516)",
            "   - Strike prices: 1/10th cent format (e.g., 118000 for $118.00)",
            "   - Options type: 'C' for calls, 'P' for puts",
            "3. EXECUTE the appropriate methods with the parameters. You can use multiple tool calls in a single request.",
            "   Your objective is to return AS MUCH DATA AS POSSIBLE relevant to the request.",
            "   Include data that may be just outside of the specified time frame for completeness of context.",
            "   Always get comprehensive data for the request including:",
            "   - OHLC data with appropriate intervals (60000ms for 1min, 300000ms for 5min)",
            "   - Trade data for volume analysis",
            "   - Greeks data for risk metrics",
            "   - Implied volatility data",
                         "   - AI-friendly compression is enabled by default (auto-compresses data >5000 tokens)",
            "4. Return the API results with all available data types",
            "",
            "PARAMETER CONVERSION GUIDE:",
            "- $118.00 strike -> 118000 (multiply by 1000)",
            "- May 16, 2025 -> 20250516",
            "- NVDA $118 Call -> root='NVDA', strike=118000, right='C'",
            "- Use 5-minute intervals (300000ms) for detailed analysis",
            "- Use 15-minute intervals (900000ms) for Greeks data",
        ],
        show_tool_calls=True,
        add_datetime_to_instructions=True,
        markdown=True,
        debug_mode=True,
        storage=SqliteStorage(table_name="theta_data_agent_results", db_file="./tmp/theta_data_agent_results.db"),
    )
    
    return agent

def main():
    """Test the specialized theta data agent"""
    print("🔧 Testing ThetaDataAgent")
    print("=" * 50)
    
    try:
        agent = get_theta_data_agent()
        print("✅ ThetaDataAgent initialized")
        
        # Test query using our proven NVDA contract
        query = """<task>                                                                                                                                        
        Please retrieve comprehensive historical market data for NVDA $118 Call option expiring on 2025-05-16 for the period between 2025-05-06 and 2025-05-13.     
        Include OHLC price data, trade data, Greeks data, and implied volatility data.
        Use AI-friendly compression to optimize the data for analysis.                                                                                                   
        </task>                                                                                                                                       
                                                                                                                                                    
        <expected_output>                                                                                                                             
        Comprehensive historical market data including:
        - OHLC price movements with 5-minute intervals
        - Trade data with volume and pricing
        - Greeks data (delta, gamma, theta, vega) with 15-minute intervals  
        - Implied volatility data
        - AI-optimized summaries and insights
        All data should be formatted for easy analysis and interpretation.
        </expected_output> """  
        
        print(f"\n🎯 Testing query: {query}")
        print("-" * 50)
        
        response = agent.run(query)
        pprint_run_response(response)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Note: This requires Theta Data Terminal to be running on localhost:25510")

if __name__ == "__main__":
    main() 