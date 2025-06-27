#!/usr/bin/env python3
"""
Agent Coordinator for managing specialized agent interactions.
This coordinates between the trade analysis agent and polygon options agent.
"""

import sys
sys.path.append('.')

from agents.trade_analysis_agent import get_trade_analysis_agent
from agents.polygon_options_agent import get_polygon_options_agent
import re

class AgentCoordinator:
    """Coordinates between different specialized agents"""
    
    def __init__(self):
        self.trade_agent = get_trade_analysis_agent()
        self.polygon_agent = get_polygon_options_agent()
    
    def analyze_trade_with_market_data(self, query: str):
        """
        Analyze a trade using both database queries and market data.
        
        This method:
        1. Uses trade_agent to get database info and plan analysis
        2. Extracts ticker/parameter info from the trade data
        3. Uses polygon_agent to get actual market data
        4. Uses trade_agent to synthesize final analysis
        """
        print("🎯 Starting coordinated trade analysis...")
        print("=" * 60)
        
        # Step 1: Get trade data and analysis plan from trade agent
        print("📊 Step 1: Getting trade data from database...")
        trade_response = self.trade_agent.run(
            f"{query}\n\n"
            "Get the full details of the trade(s) from the database."
            "IMPORTANT: Focus on getting the trade data from database and formatting the options ticker. "
            "Do NOT try to call PolygonOptionsTools - just get the database data and format the ticker."
        )
        
        print("✅ Database query complete")
        print(f"Trade Agent Response: {trade_response.content[:500]}...")
        
        # Step 2: Extract options ticker and parameters from trade response
        ticker_match = re.search(r'O:[A-Z]+\d{6}[CP]\d{8}', trade_response.content)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', trade_response.content)
        
        if not ticker_match:
            return f"❌ Could not extract options ticker from trade data. Response: {trade_response.content}"
        
        ticker = ticker_match.group(0)
        print(f"🎯 Extracted ticker: {ticker}")
        
        # Step 3: Get market data using specialized polygon agent
        print("📈 Step 2: Getting market data from Polygon API...")
        
        # Extract date range if available
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', trade_response.content)
        if len(dates) >= 2:
            from_date, to_date = dates[0], dates[1]
            polygon_query = (
                f"Get historical options aggregates for {ticker} from {from_date} to {to_date}. "
                f"Also analyze trade execution for entry time {from_date}T09:35:00 and exit time {to_date}T09:38:00."
            )
        else:
            polygon_query = f"Get options contract details and recent market data for {ticker}"
        
        polygon_response = self.polygon_agent.run(polygon_query)
        
        print("✅ Market data retrieval complete")
        print(f"Polygon Agent Response: {polygon_response.content[:500]}...")
        
        # Step 4: Synthesize final analysis
        print("🔬 Step 3: Synthesizing final analysis...")
        final_query = (
            f"Based on the trade data and market data below, provide a comprehensive analysis:\n\n"
            f"TRADE DATA:\n{trade_response.content}\n\n"
            f"MARKET DATA:\n{polygon_response.content}\n\n"
            f"Please synthesize this information into a comprehensive trade analysis with insights and recommendations."
        )
        
        final_response = self.trade_agent.run(final_query)
        
        print("✅ Analysis complete!")
        print("=" * 60)
        
        return final_response.content

def main():
    """Test the agent coordinator"""
    print("🔧 Testing Agent Coordinator")
    print("=" * 50)
    
    try:
        coordinator = AgentCoordinator()
        print("✅ Agent Coordinator initialized")
        
        # Test with the problematic query
        query = "Can you analyze the market against trade with id GNUMT0M0? I am curious how the trade evaluated against the actual contracts market"
        
        result = coordinator.analyze_trade_with_market_data(query)
        print("\n📋 FINAL ANALYSIS:")
        print("=" * 60)
        print(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 