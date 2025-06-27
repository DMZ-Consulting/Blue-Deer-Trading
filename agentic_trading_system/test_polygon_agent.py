#!/usr/bin/env python3
"""
Test the specialized PolygonOptionsAgent to ensure it actually makes API calls.
"""

import sys
sys.path.append('.')

from agents.polygon_options_agent import get_polygon_options_agent
import os
from dotenv import load_dotenv

load_dotenv()

def test_polygon_agent():
    print("🔧 Testing PolygonOptionsAgent API Calls")
    print("=" * 60)
    
    if not os.getenv("POLYGON_API_KEY"):
        print("❌ Need POLYGON_API_KEY to test")
        return
        
    try:
        agent = get_polygon_options_agent()
        print("✅ PolygonOptionsAgent initialized")
        
        # Test 1: Simple contract details
        print("\n🎯 Test 1: Get contract details")
        print("-" * 40)
        query1 = "Get options contract details for O:NVDA250516C00118000"
        response1 = agent.run(query1)
        print(f"Response: {response1.content[:300]}...")
        
        # Test 2: Historical aggregates  
        print("\n🎯 Test 2: Get historical aggregates")
        print("-" * 40)
        query2 = "Get historical options aggregates for O:NVDA250516C00118000 from 2025-05-06 to 2025-05-13"
        response2 = agent.run(query2)
        print(f"Response: {response2.content[:300]}...")
        
        # Test 3: Trade execution analysis
        print("\n🎯 Test 3: Analyze trade execution")
        print("-" * 40)
        query3 = "Analyze options trade execution for O:NVDA250516C00118000 with entry_time 2025-05-06T13:35:00 and exit_time 2025-05-13T13:38:00"
        response3 = agent.run(query3)
        print(f"Response: {response3.content[:300]}...")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_polygon_agent() 