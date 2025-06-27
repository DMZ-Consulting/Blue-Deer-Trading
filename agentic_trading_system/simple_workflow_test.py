#!/usr/bin/env python3
"""
Simple test to debug the trade analysis workflow database issue
"""

import sys
sys.path.append('.')

from workflows.trade_analysis_workflow import create_trade_analysis_workflow
import os
from dotenv import load_dotenv

load_dotenv()

def test_simple_database_query():
    """Test just the database agent part"""
    print("🔧 Testing Database Agent Only")
    print("=" * 40)
    
    try:
        # Create workflow
        workflow = create_trade_analysis_workflow(session_id="debug-test")
        
        # Test simple database query
        trade_id = "GNUMT0M0"
        query = f"SELECT trade_id, symbol, strike, expiration_date, option_type, created_at, closed_at, entry_price, exit_price, current_size, profit_loss FROM trades WHERE trade_id = '{trade_id}'"
        
        print(f"Executing query: {query}")
        
        response = workflow.database_agent.run(f"Execute this query: {query}")
        
        print(f"Response type: {type(response)}")
        print(f"Response content type: {type(response.content) if response else 'None'}")
        print(f"Response content: {response.content if response else 'None'}")
        
        return response
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_simple_workflow_single_step():
    """Test workflow with just one step to isolate the issue"""
    print("\n🔧 Testing Single Step Workflow")
    print("=" * 40)
    
    try:
        workflow = create_trade_analysis_workflow(session_id="single-step-test")
        
        # Execute just one iteration to see what happens
        trade_id = "GNUMT0M0"
        
        workflow_generator = workflow.run(trade_id=trade_id)
        
        # Get just the first few responses
        for i, response in enumerate(workflow_generator):
            print(f"Response {i+1}: {response.content}")
            if i >= 5:  # Stop after 6 responses to prevent infinite loop
                print("Stopping after 6 responses to prevent infinite loop")
                break
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_database_query()
    test_simple_workflow_single_step() 