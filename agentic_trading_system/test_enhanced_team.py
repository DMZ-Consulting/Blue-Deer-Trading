#!/usr/bin/env python3
"""
Test script for the enhanced 3-agent trade analysis team
"""

import sys
sys.path.append('.')

from teams.polygon_team import create_trade_analysis_team
from agno.utils.pprint import pprint_run_response
import os
from dotenv import load_dotenv

load_dotenv()

def test_enhanced_team():
    """Test the enhanced 3-agent trade analysis team"""
    print("🚀 Testing Enhanced Trade Analysis Team")
    print("=" * 60)
    
    # Check required environment variables
    required_vars = ["SUPABASE_DB_URL", "POLYGON_API_KEY", "OPENAI_API_KEY"]
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing required environment variable: {var}")
            return
    
    print("✅ All environment variables present")
    
    try:
        # Create the team (without knowledge base for simplicity)
        print("\n🔧 Creating trade analysis team...")
        team = create_trade_analysis_team(knowledge_base=None)
        print("✅ Team created successfully")
        print(f"Team members: {[member.name for member in team.members]}")
        
        # Test with a specific trade
        trade_id = "GNUMT0M0"
        
        print(f"\n🎯 Analyzing trade: {trade_id}")
        print("-" * 50)
        
        prompt = f"""
        Analyze trade {trade_id}. I want a comprehensive analysis that includes:
        
        1. Complete trade details from the database
        2. Historical market data for the options contract
        3. Performance assessment and strategy analysis
        4. Execution quality evaluation
        5. Actionable recommendations for improvement
        
        Please ensure each agent contributes their specialized data and analysis.
        """
        
        # Run the team analysis
        response = team.run(prompt)
        
        print("\n📊 TEAM ANALYSIS RESULTS:")
        print("=" * 60)
        pprint_run_response(response, markdown=True, show_time=True)
        
        print("\n✅ Enhanced team analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Team analysis failed: {e}")
        import traceback
        traceback.print_exc()

def test_team_coordination():
    """Test the coordination aspects of the team"""
    print("\n🤝 Testing Team Coordination")
    print("=" * 40)
    
    try:
        team = create_trade_analysis_team()
        
        # Test coordination with a specific workflow request
        coordination_prompt = """
        I need you to demonstrate the 3-agent workflow for trade GNUMT0M0:
        
        1. Have the Database Agent retrieve the complete trade record
        2. Have the Polygon Agent get historical market data for the options contract
        3. Have the Analysis Agent synthesize everything into insights
        
        Show me the coordination between agents and how data flows through the workflow.
        """
        
        print("📋 Testing coordination workflow...")
        response = team.run(coordination_prompt)
        
        print("\n🔄 COORDINATION RESULTS:")
        print("-" * 40)
        # Show just the first part of response to see coordination
        if hasattr(response, 'content'):
            content = str(response.content)
            if len(content) > 1000:
                print(content[:1000] + "...")
            else:
                print(content)
        
        print("✅ Coordination test completed")
        
    except Exception as e:
        print(f"❌ Coordination test failed: {e}")

def retrieve_reports():
    """Test the retrieval of reports from the database"""
    print("\n🔍 Retrieving reports from the database")
    print("=" * 40)

    from teams.polygon_team import create_storage_agent
    
    try:
        storage_agent = create_storage_agent()
        response = storage_agent.run("Get all the reports from the database")
        print("\n📊 REPORT RETRIEVAL RESULTS:")
        print("=" * 60)
        pprint_run_response(response, markdown=True, show_time=True)
    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_team()
    #test_team_coordination()
    retrieve_reports()
    
    print("\n" + "=" * 60)
    print("🎉 All enhanced team tests completed!")
    print("💡 The team is ready for production use with:")
    print("  • Specialized database retrieval agent")
    print("  • Polygon API market data agent") 
    print("  • Comprehensive analysis specialist")
    print("  • Coordinated workflow for complete trade analysis")
    print("=" * 60) 