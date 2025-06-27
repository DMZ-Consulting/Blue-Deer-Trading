#!/usr/bin/env python3
"""
Test Enhanced Trade Analysis Agent with Specific Trade ID

This script tests the agent's ability to analyze a specific trade ID
and use PolygonOptionsTools properly for market analysis.
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append('.')

from agents.trade_analysis_agent import get_trade_analysis_agent

load_dotenv()

def test_specific_trade_analysis():
    """
    Test the agent with the specific trade ID GNUMT0M0
    """
    print("🎯 Testing Enhanced Trade Analysis Agent - Specific Trade")
    print("=" * 70)
    
    # Check environment
    has_db = bool(os.getenv("SUPABASE_DB_URL"))
    has_polygon = bool(os.getenv("POLYGON_API_KEY"))
    
    print(f"Database: {'✅' if has_db else '❌'}")
    print(f"Polygon API: {'✅' if has_polygon else '❌'}")
    
    if not has_db:
        print("❌ Cannot test without database access. Set SUPABASE_DB_URL.")
        return False
    
    try:
        print("\n🤖 Initializing Enhanced Trade Analysis Agent...")
        agent = get_trade_analysis_agent()
        print("✅ Agent initialized successfully!")
        
        print("\n🔍 Testing Trade ID Analysis: GNUMT0M0")
        print("=" * 50)
        
        # The specific query the user mentioned
        query = "Can you analyze the market against trade with id GNUMT0M0? I am curious how the trade evaluated against the actual contracts market"
        
        print(f"Query: {query}")
        print("-" * 50)
        
        print("🚀 Running analysis...")
        response = agent.run(query)
        
        print("\n📊 Agent Response:")
        print("=" * 50)
        print(response.content)
        
        print("\n" + "=" * 70)
        print("✅ Test completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_simple_database_query():
    """
    Test a simple database query first to make sure connectivity works
    """
    print("\n🔧 Testing Database Connectivity...")
    
    if not os.getenv("SUPABASE_DB_URL"):
        print("❌ No database URL configured")
        return False
    
    try:
        agent = get_trade_analysis_agent()
        
        # Simple test query
        response = agent.run("Show me the most recent trade from the database")
        print("✅ Database connection working")
        print(f"Sample response: {response.content[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """
    Main test function
    """
    print("🧪 Enhanced Trade Analysis Agent - Specific Trade Test")
    print("=" * 70)
    
    # Test 1: Database connectivity
    db_works = test_simple_database_query()
    
    if db_works:
        # Test 2: Specific trade analysis
        trade_analysis_works = test_specific_trade_analysis()
        
        if trade_analysis_works:
            print("\n🎉 All tests passed!")
            print("\n💡 The agent should now:")
            print("1. Query the database for trade ID GNUMT0M0")
            print("2. Extract trade details (symbol, strike, expiration, etc.)")
            print("3. Format the Polygon options ticker")
            print("4. Use PolygonOptionsTools methods for market analysis")
            print("5. Compare database data with actual market conditions")
        else:
            print("\n⚠️  Trade analysis test had issues")
    else:
        print("\n❌ Database connectivity failed")
    
    print(f"\n🏁 Test completed.")

if __name__ == "__main__":
    main() 