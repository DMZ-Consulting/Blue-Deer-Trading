#!/usr/bin/env python3
"""
Quick test to verify the enhanced agent can properly use PolygonOptionsTools
"""

import sys
sys.path.append('.')

from agents.trade_analysis_agent import get_trade_analysis_agent
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("🔧 Quick Test: PolygonOptionsTools Usage")
    print("=" * 50)
    
    if not os.getenv("SUPABASE_DB_URL"):
        print("❌ Need SUPABASE_DB_URL to test")
        return
        
    try:
        agent = get_trade_analysis_agent()
        print("✅ Agent initialized")
        
        # Test with the specific query mentioned
        query = "Can you analyze the market against trade with id GNUMT0M0? I am curious how the trade evaluated against the actual contracts market"
        
        print(f"\n🎯 Testing query: {query}")
        print("-" * 50)
        
        response = agent.run(query)
        print(response.content)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 