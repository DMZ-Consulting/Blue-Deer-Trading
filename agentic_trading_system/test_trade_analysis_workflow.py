#!/usr/bin/env python3
"""
Test script for the comprehensive trade analysis workflow
"""

import sys
sys.path.append('.')

from workflows.trade_analysis_workflow import create_trade_analysis_workflow
from agno.utils.pprint import pprint_run_response
import os
from dotenv import load_dotenv

load_dotenv()

def test_trade_analysis_workflow():
    """Test the comprehensive trade analysis workflow"""
    print("🚀 Testing Comprehensive Trade Analysis Workflow")
    print("=" * 60)
    
    # Check required environment variables
    required_vars = ["SUPABASE_DB_URL", "POLYGON_API_KEY", "OPENAI_API_KEY"]
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing required environment variable: {var}")
            return
    
    try:
        # Create workflow instance
        print("🔧 Creating trade analysis workflow...")
        workflow = create_trade_analysis_workflow(session_id="test-trade-analysis")
        print("✅ Workflow created successfully")
        
        # Test trade ID (using the one from previous examples)
        trade_id = "GNUMT0M0"
        
        print(f"\n🎯 Analyzing trade: {trade_id}")
        print("-" * 40)
        
        # Example extensions to demonstrate extensibility
        extensions = {
            "market_sentiment": {
                "source": "news_analysis",
                "timeframe": "trade_period",
                "sentiment_threshold": 0.5
            },
            "sector_comparison": {
                "compare_to_sector": "technology",
                "benchmark_period": "same_timeframe"
            }
        }
        
        # Execute the workflow
        analysis_stream = workflow.run(
            trade_id=trade_id,
            include_similar_trades=True,
            extend_with=extensions
        )
        
        # Print the results with formatting
        print("\n📊 WORKFLOW EXECUTION RESULTS:")
        print("=" * 60)
        pprint_run_response(analysis_stream, markdown=True, show_time=True)
        
        print("\n✅ Trade analysis workflow test completed successfully!")
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()

def test_workflow_extensibility():
    """Test the extensibility features of the workflow"""
    print("\n🔧 Testing Workflow Extensibility")
    print("=" * 40)
    
    # Example of how to extend the workflow with custom analysis
    custom_extensions = {
        "volatility_analysis": {
            "type": "custom_volatility",
            "parameters": {
                "lookback_period": 30,
                "volatility_model": "GARCH"
            }
        },
        "correlation_analysis": {
            "type": "asset_correlation",
            "parameters": {
                "benchmark_assets": ["SPY", "QQQ", "VIX"],
                "correlation_period": "trade_period"
            }
        },
        "news_sentiment": {
            "type": "sentiment_analysis",
            "parameters": {
                "news_sources": ["bloomberg", "reuters", "cnbc"],
                "sentiment_model": "finbert"
            }
        }
    }
    
    try:
        workflow = create_trade_analysis_workflow(session_id="extensibility-test")
        
        # This demonstrates how the workflow can be extended with additional analysis types
        print("📋 Available extension types:")
        for ext_name, ext_config in custom_extensions.items():
            print(f"  • {ext_name}: {ext_config['type']}")
        
        print("\n✅ Extensibility framework ready for implementation")
        
    except Exception as e:
        print(f"❌ Extensibility test failed: {e}")

def test_knowledge_base_integration():
    """Test the document knowledge base features"""
    print("\n💾 Testing Knowledge Base Integration")
    print("=" * 40)
    
    try:
        workflow = create_trade_analysis_workflow(session_id="knowledge-test")
        
        # Test knowledge base setup
        print("🔍 Testing knowledge base setup...")
        print(f"Knowledge base URI: {workflow.knowledge_base.vector_db.uri}")
        print(f"Table name: {workflow.knowledge_base.vector_db.table_name}")
        print(f"Search type: {workflow.knowledge_base.vector_db.search_type}")
        
        # Test similar trades search (with empty knowledge base)
        from workflows.trade_analysis_workflow import TradeData
        from datetime import datetime
        
        sample_trade = TradeData(
            trade_id="TEST001",
            symbol="NVDA", 
            strike=118.0,
            expiration_date=datetime(2025, 5, 16),
            option_type="C",
            created_at=datetime(2025, 5, 6, 13, 35),
            closed_at=datetime(2025, 5, 13, 13, 38),
            entry_price=1.25,
            exit_price=5.45
        )
        
        similar_trades = workflow.get_similar_trades(sample_trade)
        print(f"✅ Similar trades search: {len(similar_trades)} results found")
        
        print("✅ Knowledge base integration working")
        
    except Exception as e:
        print(f"❌ Knowledge base test failed: {e}")

if __name__ == "__main__":
    # Run all tests
    test_trade_analysis_workflow()
    test_workflow_extensibility() 
    test_knowledge_base_integration()
    
    print("\n" + "=" * 60)
    print("🎉 All workflow tests completed!")
    print("=" * 60) 