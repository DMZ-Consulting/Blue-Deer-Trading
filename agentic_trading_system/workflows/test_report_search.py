#!/usr/bin/env python3
"""
Test Trade Report Search Agent

This script demonstrates how to use the trade report search agent
to query and analyze saved trade analysis reports.
"""

import sys
import os
sys.path.append(".")

from agents.trade_report_search_agent import create_trade_report_search_agent
from agno.utils.pprint import pprint_run_response

def test_basic_search():
    """Test basic search functionality of the trade report search agent"""
    
    print("🔍 Trade Report Search Agent Demo")
    print("=" * 60)
    
    # Create the search agent
    agent = create_trade_report_search_agent()
    
    print("✅ Agent created successfully!")
    print("\n📋 Available search capabilities:")
    print("- Performance summaries by time period")
    print("- Symbol-specific trade analysis")
    print("- Semantic search through report content")
    print("- Pattern analysis across trades")
    print("- Similar trade identification")
    print("- Recent reports overview")
    
    # Test queries (will work whether reports exist or not)
    test_queries = [
        {
            "query": "Show me recent trade reports",
            "description": "Get the most recent analysis reports"
        },
        {
            "query": "Give me a performance summary for the last 30 days",
            "description": "Overall trading performance metrics"
        },
        {
            "query": "Search for high-performing trades",
            "description": "Find trades with good returns using semantic search"
        },
        {
            "query": "Analyze trading patterns across different market conditions",
            "description": "Pattern analysis by volatility and market trends"
        }
    ]
    
    print(f"\n🧪 Running {len(test_queries)} test queries...")
    print("-" * 60)
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {test['description']}")
        print(f"Query: '{test['query']}'")
        print("-" * 40)
        
        try:
            response = agent.run(test['query'])
            print("✅ Agent Response:")
            pprint_run_response(response)
            
        except Exception as e:
            print(f"❌ Error running query: {e}")
        
        print()
    
    print("=" * 60)
    print("🎯 Demo Complete!")
    print("\nNext steps:")
    print("1. Generate trade reports using controlled_trade_analysis.py")
    print("2. Run more sophisticated searches once reports exist")
    print("3. Use the agent for actual trade performance analysis")

def interactive_search():
    """Interactive search mode for manual testing"""
    
    print("🔍 Interactive Trade Report Search")
    print("=" * 60)
    
    agent = create_trade_report_search_agent()
    
    print("✅ Agent ready! Type your queries below.")
    print("Examples:")
    print("- 'Show me all NVDA trades'")
    print("- 'Find trades with high returns'")
    print("- 'What are the recent reports?'")
    print("- 'Analyze performance patterns'")
    print("\nType 'quit' to exit.")
    print("-" * 60)
    
    while True:
        try:
            query = input("\n🔍 Your query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            print(f"\n🤖 Processing: {query}")
            print("-" * 40)
            
            response = agent.run(query)
            pprint_run_response(response)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Check if user wants interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_search()
    else:
        test_basic_search() 