#!/usr/bin/env python3
"""
Example usage of the Trade Analysis Workflow

This demonstrates various ways to use the comprehensive trade analysis workflow:
1. Basic trade analysis
2. Batch processing multiple trades
3. Extending with custom analysis modules
4. Searching historical analysis reports
"""

import sys
sys.path.append('.')

from workflows.trade_analysis_workflow import create_trade_analysis_workflow, TradeData
from agno.utils.pprint import pprint_run_response
from datetime import datetime
import json

def basic_trade_analysis_example():
    """Example: Basic trade analysis for a single trade"""
    print("📊 Example 1: Basic Trade Analysis")
    print("=" * 50)
    
    # Create workflow
    workflow = create_trade_analysis_workflow(session_id="basic-analysis-demo")
    
    # Analyze a single trade
    trade_id = "GNUMT0M0"
    
    print(f"Analyzing trade: {trade_id}")
    analysis_stream = workflow.run(
        trade_id=trade_id,
        include_similar_trades=True
    )
    
    # Process results
    for response in analysis_stream:
        print(f"Status: {response.content}")
        if response.event.value == "workflow_completed":
            # Save the final report
            try:
                report_data = json.loads(response.content)
                print("\n📋 Analysis Summary:")
                print(f"Strategy: {report_data.get('strategy_analysis', {}).get('strategy_type', 'Unknown')}")
                print(f"Executive Summary: {report_data.get('executive_summary', 'N/A')[:200]}...")
            except:
                print("Report generated successfully")

def batch_analysis_example():
    """Example: Batch processing multiple trades"""
    print("\n🔄 Example 2: Batch Trade Analysis")
    print("=" * 50)
    
    # List of trades to analyze
    trade_ids = ["GNUMT0M0"]  # Add more trade IDs as needed
    
    results = {}
    
    for trade_id in trade_ids:
        print(f"\nProcessing trade: {trade_id}")
        
        # Create unique session for each trade
        workflow = create_trade_analysis_workflow(session_id=f"batch-{trade_id}")
        
        try:
            analysis_stream = workflow.run(
                trade_id=trade_id,
                include_similar_trades=False  # Skip similar trades for batch processing
            )
            
            # Extract final result
            final_response = None
            for response in analysis_stream:
                if response.event.value == "workflow_completed":
                    final_response = response
                    break
            
            if final_response:
                results[trade_id] = "✅ Success"
            else:
                results[trade_id] = "❌ Failed"
                
        except Exception as e:
            results[trade_id] = f"❌ Error: {str(e)}"
    
    print("\n📊 Batch Processing Results:")
    for trade_id, status in results.items():
        print(f"  {trade_id}: {status}")

def extended_analysis_example():
    """Example: Using workflow extensions for enhanced analysis"""
    print("\n🔧 Example 3: Extended Analysis with Custom Modules")
    print("=" * 50)
    
    # Define comprehensive extensions
    extensions = {
        "volatility_analysis": {
            "type": "advanced_volatility",
            "parameters": {
                "models": ["GARCH", "EWMA", "historical"],
                "forecast_horizon": 30,
                "confidence_intervals": [0.95, 0.99]
            }
        },
        "market_regime_analysis": {
            "type": "market_regime",
            "parameters": {
                "regime_indicators": ["VIX", "term_structure", "credit_spreads"],
                "lookback_period": 252
            }
        },
        "sentiment_analysis": {
            "type": "news_sentiment",
            "parameters": {
                "sources": ["bloomberg", "reuters", "twitter"],
                "sentiment_threshold": 0.6,
                "relevance_filter": True
            }
        },
        "peer_comparison": {
            "type": "peer_analysis",
            "parameters": {
                "peer_selection": "sector_similar",
                "metrics": ["P&L", "timing", "risk_adjusted_returns"],
                "benchmark_period": "same_quarter"
            }
        }
    }
    
    # Create workflow with extensions
    workflow = create_trade_analysis_workflow(session_id="extended-analysis-demo")
    
    print("📋 Extensions to be applied:")
    for ext_name, ext_config in extensions.items():
        print(f"  • {ext_name}: {ext_config['type']}")
    
    # Run analysis with all extensions
    trade_id = "GNUMT0M0"
    analysis_stream = workflow.run(
        trade_id=trade_id,
        include_similar_trades=True,
        extend_with=extensions
    )
    
    print(f"\nRunning extended analysis for {trade_id}...")
    
    # Process results
    for response in analysis_stream:
        if "extensions" in response.content.lower():
            print(f"Extension Status: {response.content}")

def knowledge_base_search_example():
    """Example: Searching historical analysis reports"""
    print("\n🔍 Example 4: Knowledge Base Search")
    print("=" * 50)
    
    # Create workflow to access knowledge base
    workflow = create_trade_analysis_workflow(session_id="search-demo")
    
    # Example searches
    search_queries = [
        "NVDA call options analysis",
        "strategy:directional symbol:NVDA",
        "poor execution quality",
        "high volatility trades"
    ]
    
    print("🔍 Searching historical analysis reports:")
    
    for query in search_queries:
        try:
            results = workflow.knowledge_base.search(query=query, num_documents=3)
            print(f"\nQuery: '{query}'")
            print(f"Results found: {len(results)}")
            
            for i, result in enumerate(results, 1):
                trade_id = result.meta_data.get("trade_id", "Unknown")
                symbol = result.meta_data.get("symbol", "Unknown")
                strategy = result.meta_data.get("strategy_type", "Unknown")
                print(f"  {i}. Trade {trade_id} ({symbol}) - {strategy}")
                
        except Exception as e:
            print(f"Search failed for '{query}': {e}")

def custom_workflow_integration_example():
    """Example: Integrating workflow into existing systems"""
    print("\n🔗 Example 5: Custom Integration")
    print("=" * 50)
    
    class TradeAnalysisService:
        """Example service class showing integration patterns"""
        
        def __init__(self):
            self.workflow = create_trade_analysis_workflow(session_id="service-integration")
        
        def analyze_trade(self, trade_id: str, options: dict = None):
            """Analyze a single trade with custom options"""
            options = options or {}
            
            return self.workflow.run(
                trade_id=trade_id,
                include_similar_trades=options.get("include_similar", True),
                extend_with=options.get("extensions", {})
            )
        
        def get_trade_insights(self, symbol: str, limit: int = 5):
            """Get insights for trades involving a specific symbol"""
            query = f"symbol:{symbol} analysis"
            try:
                results = self.workflow.knowledge_base.search(query=query, num_documents=limit)
                return [result.meta_data for result in results]
            except:
                return []
        
        def compare_strategies(self, strategy_type: str):
            """Compare trades using a specific strategy"""
            query = f"strategy:{strategy_type}"
            try:
                results = self.workflow.knowledge_base.search(query=query, num_documents=10)
                return results
            except:
                return []
    
    # Demonstrate the service
    service = TradeAnalysisService()
    
    print("📊 Trade Analysis Service Demo:")
    print("  • Analyze trade: GNUMT0M0")
    print("  • Get NVDA insights")
    print("  • Compare directional strategies")
    
    # Example usage
    insights = service.get_trade_insights("NVDA", limit=3)
    print(f"NVDA insights found: {len(insights)}")

if __name__ == "__main__":
    print("🚀 Trade Analysis Workflow Examples")
    print("=" * 60)
    
    # Run all examples
    basic_trade_analysis_example()
    batch_analysis_example()
    extended_analysis_example()
    knowledge_base_search_example()
    custom_workflow_integration_example()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("💡 These examples show different ways to use the trade analysis workflow")
    print("🔧 Extend them based on your specific use cases")
    print("=" * 60) 