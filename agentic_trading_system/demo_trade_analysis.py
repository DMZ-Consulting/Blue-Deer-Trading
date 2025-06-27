#!/usr/bin/env python3
"""
Demo: Enhanced Trade Analysis Agent with Polygon Options Tools

This script demonstrates how to use the enhanced trade analysis agent to:
1. Analyze trades from your database
2. Use historical options data for comprehensive analysis
3. Provide actionable insights for trading decisions

Prerequisites:
- Set SUPABASE_DB_URL for database access
- Set POLYGON_API_KEY for historical options data
- Have trade data in your database
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append('.')

from agents.trade_analysis_agent import get_trade_analysis_agent, format_options_ticker

load_dotenv()

def demo_trade_analysis():
    """
    Demonstrate the enhanced trade analysis capabilities
    """
    print("🚀 Enhanced Trade Analysis Agent Demo")
    print("=" * 60)
    
    # Check environment setup
    has_db = bool(os.getenv("SUPABASE_DB_URL"))
    has_polygon = bool(os.getenv("POLYGON_API_KEY"))
    
    print(f"Database access: {'✅' if has_db else '❌'} {'(ready)' if has_db else '(set SUPABASE_DB_URL)'}")
    print(f"Polygon API: {'✅' if has_polygon else '❌'} {'(ready)' if has_polygon else '(set POLYGON_API_KEY)'}")
    
    if not has_db:
        print("\n⚠️  Without database access, the agent cannot query trade data.")
        print("Set SUPABASE_DB_URL to enable database functionality.")
    
    if not has_polygon:
        print("\n⚠️  Without Polygon API, historical data will be limited.")
        print("Set POLYGON_API_KEY to enable full historical analysis.")
    
    print("\n🤖 Initializing Enhanced Trade Analysis Agent...")
    
    try:
        agent = get_trade_analysis_agent()
        print("✅ Agent initialized successfully!")
        
        print("\n" + "=" * 60)
        print("📊 DEMO: Agent Capabilities")
        print("=" * 60)
        
        # Demo 1: Show ticker formatting capability
        print("🎯 Demo 1: Options Ticker Formatting")
        print("-" * 40)
        
        example_trades = [
            {"symbol": "NVDA", "exp": "2024-05-16", "type": "call", "strike": 118},
            {"symbol": "AAPL", "exp": "2024-12-20", "type": "put", "strike": 150},
            {"symbol": "TSLA", "exp": "2024-06-21", "type": "call", "strike": 250}
        ]
        
        print("Trade data → Polygon format:")
        for trade in example_trades:
            ticker = format_options_ticker(
                trade["symbol"], trade["exp"], trade["type"], trade["strike"]
            )
            print(f"  {trade['symbol']} {trade['strike']} {trade['type']} exp {trade['exp']} → {ticker}")
        
        # Demo 2: Sample queries the agent can handle
        print(f"\n🎯 Demo 2: Sample Analysis Queries")
        print("-" * 40)
        
        sample_queries = [
            {
                "title": "Recent Trades Analysis",
                "query": "Show me the 5 most recent options trades and calculate their basic P&L"
            },
            {
                "title": "Specific Trade Deep Dive", 
                "query": "Find any NVDA trade and perform comprehensive historical analysis using Polygon data"
            },
            {
                "title": "Portfolio Performance",
                "query": "Analyze my overall options trading performance and identify patterns"
            },
            {
                "title": "Market Context Analysis",
                "query": "For my best performing trade, analyze the market conditions that contributed to success"
            }
        ]
        
        for i, sample in enumerate(sample_queries, 1):
            print(f"\n  Sample Query {i}: {sample['title']}")
            print(f"  └─ \"{sample['query']}\"")
        
        # Demo 3: Interactive mode
        print(f"\n🎯 Demo 3: Interactive Mode")
        print("-" * 40)
        
        if has_db and has_polygon:
            print("✅ Full functionality available!")
            print("\nTry running:")
            print("  agent = get_trade_analysis_agent()")
            print("  response = agent.run('Show me my recent AAPL options trades')")
            print("  print(response.content)")
        elif has_db:
            print("⚠️  Database queries available, limited historical analysis")
            print("\nYou can still:")
            print("  • Query trade data from database")
            print("  • Calculate basic P&L metrics")
            print("  • Get trade summaries and statistics")
        else:
            print("❌ Limited functionality without database access")
            print("\nTo enable full features:")
            print("  1. Set SUPABASE_DB_URL for database access")
            print("  2. Set POLYGON_API_KEY for historical data")
        
        # Demo 4: Show an example interaction (if possible)
        if has_db:
            print(f"\n🎯 Demo 4: Live Example")
            print("-" * 40)
            
            try:
                print("Running: 'Show me database schema info for trades table'")
                response = agent.run("Show me what tables are available in the database and what fields are in the trades-related tables")
                print("\nAgent Response:")
                print(response.content[:500] + "..." if len(response.content) > 500 else response.content)
            except Exception as e:
                print(f"❌ Example query failed: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 Demo Complete!")
        print("=" * 60)
        
        print("\n💡 Next Steps:")
        print("1. Use the agent interactively: agent.run('your query here')")
        print("2. Focus queries on specific trades or time periods")
        print("3. Ask for actionable insights and trading recommendations")
        print("4. Leverage historical data for timing and context analysis")
        
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return False
    
    return True

def show_usage_examples():
    """
    Show practical usage examples
    """
    print("\n📖 Usage Examples:")
    print("=" * 40)
    
    examples = [
        {
            "scenario": "Analyze Recent Performance",
            "code": """
agent = get_trade_analysis_agent()
response = agent.run('''
    Show me my last 10 options trades with:
    - Entry/exit prices and timing
    - P&L calculations 
    - Win/loss ratio
    - Best and worst performers
''')
print(response.content)
"""
        },
        {
            "scenario": "Deep Dive on Specific Trade",
            "code": """
agent = get_trade_analysis_agent()
response = agent.run('''
    Find my NVDA trade from May 2024 and analyze:
    - Historical price movement during the trade
    - Market volatility and conditions
    - Entry/exit timing quality
    - Lessons for future trades
''')
print(response.content)
"""
        },
        {
            "scenario": "Portfolio Strategy Analysis",
            "code": """
agent = get_trade_analysis_agent()
response = agent.run('''
    Analyze my options trading strategy:
    - Which underlying stocks perform best?
    - Optimal holding periods and timing patterns
    - Risk management effectiveness
    - Recommendations for improvement
''')
print(response.content)
"""
        }
    ]
    
    for example in examples:
        print(f"\n🎯 {example['scenario']}:")
        print(example['code'])

if __name__ == "__main__":
    # Run the demo
    success = demo_trade_analysis()
    
    if success:
        show_usage_examples()
    
    print(f"\n🏁 Demo finished. Ready to analyze your trades!") 