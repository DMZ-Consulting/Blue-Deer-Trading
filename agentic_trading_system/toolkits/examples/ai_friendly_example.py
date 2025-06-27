"""
AI-Friendly Theta Data Options Example

This example demonstrates how to use the Theta Data toolkit's AI-friendly features
for getting compressed, meaningful data suitable for AI agent consumption.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path to import the toolkit
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from toolkits.theta_data_options import ThetaDataOptionsTools


def main():
    """Demonstrate AI-friendly data compression features"""
    print("🤖 AI-Friendly Theta Data Options Example")
    print("=" * 60)
    
    # Initialize the toolkit
    theta_tools = ThetaDataOptionsTools()
    
    # Example parameters for NVDA options
    root = "NVDA"
    exp = 20250516  # May 16, 2025 expiration
    strike = 118000  # $118.00 strike
    right = "C"  # Call option
    start_date = 20250506  # May 6, 2025
    end_date = 20250513    # May 13, 2025
    
    print(f"📊 Analyzing {root} ${strike/1000:.0f} {right} expiring {exp}")
    print(f"📅 Analysis period: {start_date} to {end_date}")
    print()
    
    # Example 1: Standard vs AI-Friendly comparison
    print("🔍 Comparison: Standard vs AI-Friendly Data")
    print("-" * 50)
    
    # Get standard data (full)
    standard_data = theta_tools.get_historical_options_ohlc(
        root=root, exp=exp, strike=strike, right=right,
        start_date=start_date, end_date=end_date,
        ivl=300000, ai_friendly=False
    )
    
    # Get AI-friendly data (compressed)
    ai_data = theta_tools.get_historical_options_ohlc(
        root=root, exp=exp, strike=strike, right=right,
        start_date=start_date, end_date=end_date,
        ivl=300000, ai_friendly=True, max_samples=3
    )
    
    if standard_data["success"] and ai_data["success"]:
        print(f"📈 Standard OHLC Data:")
        print(f"   • Total records: {standard_data['count']}")
        print(f"   • Data size: ~{len(str(standard_data)):,} characters")
        if standard_data.get("data"):
            print(f"   • Sample record: {list(standard_data['data'][0].keys())}")
        
        print(f"\n🤖 AI-Friendly OHLC Data:")
        print(f"   • Total records: {ai_data['total_records']}")
        print(f"   • Sample records included: {len(ai_data.get('samples', []))}")
        print(f"   • Data size: ~{len(str(ai_data)):,} characters")
        print(f"   • Compression ratio: {len(str(standard_data))/len(str(ai_data)):.1f}x smaller")
        
        # Show the insights
        if ai_data.get("insights"):
            print(f"   • Key insights:")
            for insight in ai_data["insights"]:
                print(f"     - {insight}")
        
        # Show statistics
        if ai_data.get("statistics"):
            stats = ai_data["statistics"]
            print(f"   • Statistics:")
            if "price_change_pct" in stats:
                print(f"     - Price change: {stats['price_change_pct']:+.1f}%")
            if "total_volume" in stats:
                print(f"     - Total volume: {stats['total_volume']:,}")
    
    print()
    
    # Example 2: Comprehensive AI Summary
    print("🎯 Comprehensive AI-Optimized Summary")
    print("-" * 50)
    
    # Get comprehensive summary optimized for AI
    summary = theta_tools.get_options_summary_for_ai(
        root=root, exp=exp, strike=strike, right=right,
        start_date=start_date, end_date=end_date,
        data_types=['ohlc', 'trades', 'implied_volatility', 'greeks'],
        max_samples_per_type=3
    )
    
    if summary["success"]:
        print(f"✅ Executive Summary:")
        print(f"   {summary['executive_summary']}")
        print()
        
        print(f"📊 Trading Signals: {', '.join(summary['trading_signals'])}")
        print()
        
        print(f"🎯 Key Insights:")
        for insight in summary['key_insights'][:5]:  # Show top 5
            print(f"   • {insight}")
        print()
        
        print(f"⚠️  Risk Metrics:")
        risk = summary['risk_metrics']
        for metric, value in risk.items():
            if isinstance(value, (int, float)):
                print(f"   • {metric.replace('_', ' ').title()}: {value:.3f}")
        print()
        
        print(f"📈 Data Summary:")
        for data_type, data_summary in summary['data_summary'].items():
            print(f"   • {data_type.upper()}: {data_summary['total_records']} records")
            if data_summary.get('insights'):
                for insight in data_summary['insights'][:2]:  # Top 2 per type
                    print(f"     - {insight}")
        
        print(f"\n📏 Data Efficiency:")
        print(f"   • Total data size: ~{len(str(summary)):,} characters")
        print(f"   • Perfect for AI context windows")
    
    print()
    
    # Example 3: Real-world AI Agent Usage
    print("🤖 Real-world AI Agent Usage Pattern")
    print("-" * 50)
    
    def ai_agent_decision_making(options_summary):
        """Simulate how an AI agent would use the compressed data"""
        if not options_summary.get("success"):
            return "Unable to analyze - data unavailable"
        
        signals = options_summary.get('trading_signals', [])
        risk_metrics = options_summary.get('risk_metrics', {})
        executive_summary = options_summary.get('executive_summary', '')
        
        # AI decision logic based on compressed data
        decision = "NEUTRAL"
        reasoning = []
        
        # Check signals
        bullish_signals = [s for s in signals if s in ['BULLISH', 'STRONG_BULLISH', 'HIGH_VOLUME']]
        bearish_signals = [s for s in signals if s in ['BEARISH', 'STRONG_BEARISH']]
        
        if len(bullish_signals) > len(bearish_signals):
            decision = "BULLISH"
            reasoning.append(f"Multiple bullish signals: {', '.join(bullish_signals)}")
        elif len(bearish_signals) > len(bullish_signals):
            decision = "BEARISH"
            reasoning.append(f"Multiple bearish signals: {', '.join(bearish_signals)}")
        
        # Check risk levels
        if risk_metrics.get('iv_level', 0) > 0.4:
            reasoning.append("High IV suggests elevated risk/opportunity")
        
        if risk_metrics.get('liquidity_score', 0) < 3:
            reasoning.append("Low liquidity - be cautious with position sizing")
        
        return {
            "decision": decision,
            "confidence": min(len(reasoning) * 0.3, 1.0),
            "reasoning": reasoning,
            "executive_summary": executive_summary
        }
    
    # Simulate AI agent analysis
    ai_decision = ai_agent_decision_making(summary)
    
    print(f"🧠 AI Agent Decision: {ai_decision['decision']}")
    print(f"🎯 Confidence: {ai_decision['confidence']:.1%}")
    print(f"💭 Reasoning:")
    for reason in ai_decision['reasoning']:
        print(f"   • {reason}")
    
    print()
    print("✨ Benefits of AI-Friendly Data:")
    print("   • 5-10x smaller data size")
    print("   • Pre-computed insights and signals")
    print("   • Structured for easy AI interpretation")
    print("   • Preserves essential trading information")
    print("   • Reduces token usage for LLM APIs")
    print("   • Faster processing and decision making")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Example interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Make sure the Theta Data Terminal is running and you have the required dependencies.") 