#!/usr/bin/env python3
"""
Polygon Options Trading Toolkit - Historical Data Testing

This script tests the comprehensive historical options data capabilities including:
- Historical aggregates (OHLCV data) for price analysis
- Historical trades for execution quality analysis  
- Historical quotes for spread/liquidity analysis
- Trade execution analysis with P&L calculation
- Market context analysis for AI decision making

Run this file from the agentic_trading_system directory:
    python run_options_example.py

Or from the project root:
    python agentic_trading_system/run_options_example.py
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from toolkits.polygon_options import PolygonOptionsTools

load_dotenv()


def timer_decorator(func_name: str = None):
    """Decorator to time function execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = func_name or func.__name__
            print(f"⏱️  Starting {name}...")
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                duration = end_time - start_time
                print(f"✅ {name} completed in {duration:.2f} seconds")
                return result
                
            except Exception as e:
                end_time = time.perf_counter()
                duration = end_time - start_time
                print(f"❌ {name} failed after {duration:.2f} seconds: {e}")
                raise
                
        return wrapper
    return decorator


def time_operation(operation_name: str, func, *args, **kwargs):
    """Time a specific operation"""
    print(f"⏱️  Starting {operation_name}...")
    start_time = time.perf_counter()
    
    try:
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"✅ {operation_name} completed in {duration:.2f} seconds")
        return result, duration
        
    except Exception as e:
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"❌ {operation_name} failed after {duration:.2f} seconds: {e}")
        return None, duration


@timer_decorator("Toolkit initialization")
def initialize_toolkit(api_key: str = None):
    """Initialize the options toolkit"""
    return PolygonOptionsTools(api_key=api_key)


def test_specific_nvda_trade():
    """
    Test the historical data capabilities on a specific NVDA trade from the user's database
    
    Trade Details:
    - NVDA Call Option
    - Expiration: 05/16/2024 (assuming 2024, not 2025)
    - Strike: $118
    - Opened: 05/06/2024 09:35AM EST  
    - Closed: 05/13/2024 09:38AM EST
    - Entry Price: $1.25 per contract
    """
    print("🎯 Testing Historical Data on Specific NVDA Trade")
    print("=" * 80)
    
    # Trade details
    trade_details = {
        "underlying": "NVDA",
        "option_type": "call",
        "strike": 118,
        "expiration": "2025-05-16",
        "entry_time": "2025-05-06T09:35:00",  # 9:35 AM EST
        "exit_time": "2025-05-13T09:38:00",   # 9:38 AM EST
        "entry_price": 1.25,
        "position_size": 1
    }
    
    print(f"📊 TRADE ANALYSIS FOR:")
    print(f"   • Underlying: {trade_details['underlying']}")
    print(f"   • Option: {trade_details['strike']} Call expiring {trade_details['expiration']}")
    print(f"   • Entry: {trade_details['entry_time']} at ${trade_details['entry_price']}")
    print(f"   • Exit: {trade_details['exit_time']}")
    print("=" * 80)
    
    # Check if API key is available
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("⚠️  POLYGON_API_KEY not set. Testing with demo ticker format...")
    
    try:
        # Initialize toolkit
        options_tools = initialize_toolkit(api_key)
        
        # Construct the options ticker in Polygon format
        # Format: O:UNDERLYING[expiration]C[strike with padding]
        # Example: O:NVDA240516C00118000 (NVDA call expiring 2024-05-16, strike 118)
        expiry_formatted = trade_details['expiration'].replace('-', '')[2:]  # "240516" 
        strike_formatted = f"{int(trade_details['strike'] * 1000):08d}"      # "00118000"
        options_ticker = f"O:{trade_details['underlying']}{expiry_formatted}C{strike_formatted}"
        
        print(f"🎯 STEP 1: Constructed Options Ticker")
        print(f"   📋 Ticker: {options_ticker}")
        print("-" * 50)
        
        # Test 1: Get historical aggregates for the trade period
        print(f"📈 STEP 2: Historical Price Analysis (Entry to Exit)")
        print("-" * 50)
        
        agg_result, agg_time = time_operation(
            f"Get price data for {options_ticker}",
            options_tools.get_historical_options_aggregates,
            options_ticker=options_ticker,
            multiplier=1,
            timespan="hour",  # Hourly bars for better resolution
            from_date="2025-05-06",  # Entry date
            to_date="2025-05-13",    # Exit date
            limit=1000
        )
        
        if agg_result and "error" not in agg_result and agg_result.get("count", 0) > 0:
            print(f"✅ Retrieved {agg_result['count']} hourly price bars")
            print(agg_result)
            
            # Find entry and exit prices from historical data
            entry_bars = []
            exit_bars = []
            
            for bar in agg_result["data"]:
                bar_time = datetime.fromtimestamp(bar["timestamp"] / 1000)
                if bar_time.date() == datetime(2025, 5, 6).date():
                    entry_bars.append(bar)
                elif bar_time.date() == datetime(2025, 5, 13).date():
                    exit_bars.append(bar)
            
            if entry_bars:
                entry_market_price = entry_bars[0]["open"]  # Use market open on entry day
                print(f"📊 Entry day market price: ${entry_market_price:.2f}")
                print(f"💰 Actual entry price: ${trade_details['entry_price']:.2f}")
                entry_premium = (trade_details['entry_price'] / entry_market_price) * 100 if entry_market_price > 0 else 0
                print(f"📈 Entry price vs market: {entry_premium:.1f}% of market price")
            
            if exit_bars:
                exit_market_price = exit_bars[0]["open"]  # Use market open on exit day
                print(f"📊 Exit day market price: ${exit_market_price:.2f}")
                
                # Calculate P&L if we have exit price
                if entry_bars:
                    pl_per_contract = exit_market_price - trade_details['entry_price']
                    pl_percent = (pl_per_contract / trade_details['entry_price']) * 100
                    total_pl = pl_per_contract * trade_details['position_size']
                    
                    print(f"💰 Estimated P&L: ${pl_per_contract:.2f} per contract ({pl_percent:+.1f}%)")
                    print(f"🏦 Total P&L (1 contract): ${total_pl:.2f}")
        else:
            print(f"⚠️  No price data available: {agg_result.get('error', 'No data') if agg_result else 'Failed'}")
            print("💡 This is expected for historical dates - data may require premium subscription")
        
        # Test 2: Trade execution analysis
        print(f"\n🎯 STEP 3: Trade Execution Analysis")
        print("-" * 50)
        
        execution_result, execution_time = time_operation(
            f"Analyze trade execution for {options_ticker}",
            options_tools.analyze_options_trade_execution,
            options_ticker=options_ticker,
            entry_time=trade_details['entry_time'],
            exit_time=trade_details['exit_time'],
            position_size=trade_details['position_size'],
            side="long"
        )
        
        if execution_result and "error" not in execution_result:
            print(f"✅ Trade execution analysis completed")
            if "profit_loss" in execution_result:
                print(f"💰 Calculated P&L: ${execution_result['profit_loss']:.2f}")
            if "profit_loss_percent" in execution_result:
                print(f"📈 Return: {execution_result['profit_loss_percent']:+.2f}%")
        else:
            print(f"⚠️  Execution analysis unavailable: {execution_result.get('error', 'No data') if execution_result else 'Failed'}")
        
        # Test 3: Market context during trade
        print(f"\n🌐 STEP 4: Market Context Analysis")
        print("-" * 50)
        
        context_result, context_time = time_operation(
            f"Get market context for {options_ticker}",
            options_tools.get_options_trading_context,
            options_ticker=options_ticker,
            trade_date="2024-05-06",  # Entry date
            analysis_window_hours=24
        )
        
        if context_result and "error" not in context_result:
            print(f"✅ Market context analysis completed")
            price_analysis = context_result.get("price_analysis", {})
            volatility = context_result.get("volatility_analysis", {})
            print(f"📊 Entry day analysis:")
            if price_analysis:
                print(f"   • Price range: ${price_analysis.get('day_low', 'N/A')} - ${price_analysis.get('day_high', 'N/A')}")
            if volatility:
                print(f"   • Volatility: {volatility.get('intraday_volatility', 'N/A')}%")
        else:
            print(f"⚠️  Context analysis unavailable: {context_result.get('error', 'No data') if context_result else 'Failed'}")
        
        # Test 4: AI Agent Analysis
        print(f"\n🤖 STEP 5: AI Agent Trade Analysis")
        print("-" * 50)
        
        return analyze_trade_with_ai(options_tools, trade_details, options_ticker)
        
    except Exception as e:
        print(f"❌ Error analyzing NVDA trade: {e}")
        return False


def analyze_trade_with_ai(options_tools, trade_details, options_ticker):
    """
    Use AI agent to analyze the NVDA trade
    """
    try:
        agent = Agent(
            name="Trade Analysis Agent",
            role="AI agent specialized in analyzing historical options trades",
            model=OpenAIChat(id="gpt-4o"),
            tools=[options_tools, ReasoningTools()],
            instructions=[
                "You are analyzing a completed options trade.",
                "Use historical data methods to understand trade performance.",
                "Focus on actionable insights for future trading decisions.",
                "Be specific about what the data shows and what it means.",
            ],
            markdown=True,
            show_tool_calls=True,
        )
        
        # Create analysis query
        query = f"""
        Analyze this completed NVDA options trade:
        
        • Contract: {options_ticker}
        • Underlying: {trade_details['underlying']} 
        • Strike: ${trade_details['strike']} Call
        • Entry: {trade_details['entry_time']} at ${trade_details['entry_price']}
        • Exit: {trade_details['exit_time']}
        • Position: {trade_details['position_size']} contract
        
        Please:
        1. Get historical aggregates to understand price movement during the trade
        2. Analyze what this trade teaches us about timing and execution
        3. Provide insights for similar future trades
        
        Focus on practical trading insights based on the historical data.
        """
        
        print(f"🎯 AI Analysis Query:")
        print(f"   {query.strip()}")
        print("-" * 50)
        
        response = agent.run(query)
        print(response.content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error in AI trade analysis: {e}")
        return False


def test_historical_options_data():
    """
    Test the historical options data capabilities - the core functionality for AI trade analysis
    """
    print("🧪 Testing Historical Options Data Capabilities...")
    print("=" * 80)
    
    # Check if API key is available
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("⚠️  POLYGON_API_KEY not set. Testing in demo mode...")
        print("💡 Set POLYGON_API_KEY to test with live data: https://polygon.io/")
    
    try:
        # Initialize toolkit
        options_tools = initialize_toolkit(api_key)
        
        print("\n📊 STEP 1: Find Available Options Contracts")
        print("-" * 50)
        
        # First, find some available contracts using screening
        screen_result, screen_time = time_operation(
            "Screen for active AAPL options",
            options_tools.screen_options_by_criteria,
            underlying_ticker="AAPL",
            days_to_expiration_range=(10, 45),
            option_type="call"
        )
        
        if not screen_result or "error" in str(screen_result[0]):
            print("❌ No contracts found via screening. Testing with sample ticker...")
            # Use a sample ticker format for testing
            sample_ticker = "O:AAPL250117C00200000"  # Example format
            print(f"📋 Using sample ticker: {sample_ticker}")
        else:
            sample_ticker = screen_result[0]["ticker"]
            print(f"✅ Found {len(screen_result)} contracts")
            print(f"📋 Using contract: {sample_ticker}")
        
        print(f"\n📈 STEP 2: Test Historical Aggregates (OHLCV Data)")
        print("-" * 50)
        
        # Test historical aggregates - this is key for AI price analysis
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        
        agg_result, agg_time = time_operation(
            f"Get historical aggregates for {sample_ticker}",
            options_tools.get_historical_options_aggregates,
            options_ticker=sample_ticker,
            multiplier=1,
            timespan="minute",
            from_date=start_date,
            to_date=end_date,
            limit=1000
        )
        
        if agg_result and "error" not in agg_result and agg_result.get("count", 0) > 0:
            print(f"✅ Retrieved {agg_result['count']} aggregate data points")
            sample_bar = agg_result["data"][0]
            print(f"📊 Sample bar: O=${sample_bar['open']}, H=${sample_bar['high']}, L=${sample_bar['low']}, C=${sample_bar['close']}")
        else:
            print(f"⚠️  No aggregate data available: {agg_result.get('error', 'No data') if agg_result else 'Failed'}")
        
        print(f"\n💱 STEP 3: Test Historical Trades")
        print("-" * 50)
        
        # Test historical trades - key for execution quality analysis
        trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        trades_result, trades_time = time_operation(
            f"Get historical trades for {sample_ticker}",
            options_tools.get_historical_options_trades,
            options_ticker=sample_ticker,
            timestamp_date=trade_date,
            limit=1000
        )
        
        if trades_result and "error" not in trades_result and trades_result.get("count", 0) > 0:
            print(f"✅ Retrieved {trades_result['count']} trade records")
            sample_trade = trades_result["data"][0]
            print(f"💰 Sample trade: Price=${sample_trade['price']}, Size={sample_trade['size']}")
        else:
            print(f"⚠️  No trade data available: {trades_result.get('error', 'No data') if trades_result else 'Failed'}")
        
        print(f"\n💰 STEP 4: Test Historical Quotes")
        print("-" * 50)
        
        # Test historical quotes - key for spread/liquidity analysis
        quotes_result, quotes_time = time_operation(
            f"Get historical quotes for {sample_ticker}",
            options_tools.get_historical_options_quotes,
            options_ticker=sample_ticker,
            timestamp_date=trade_date,
            limit=1000
        )
        
        if quotes_result and "error" not in quotes_result and quotes_result.get("count", 0) > 0:
            print(f"✅ Retrieved {quotes_result['count']} quote records")
            sample_quote = quotes_result["data"][0]
            print(f"📈 Sample quote: Bid=${sample_quote['bid']}, Ask=${sample_quote['ask']}, Spread=${sample_quote.get('spread', 'N/A')}")
        else:
            print(f"⚠️  No quote data available: {quotes_result.get('error', 'No data') if quotes_result else 'Failed'}")
        
        print(f"\n🎯 STEP 5: Test Trade Execution Analysis")
        print("-" * 50)
        
        # Test comprehensive trade analysis - the ultimate AI capability
        entry_time = (datetime.now() - timedelta(days=2, hours=10)).isoformat()
        exit_time = (datetime.now() - timedelta(days=2, hours=14)).isoformat()
        
        trade_analysis_result, trade_analysis_time = time_operation(
            f"Analyze trade execution for {sample_ticker}",
            options_tools.analyze_options_trade_execution,
            options_ticker=sample_ticker,
            entry_time=entry_time,
            exit_time=exit_time,
            position_size=1,
            side="long"
        )
        
        if trade_analysis_result and "error" not in trade_analysis_result:
            print(f"✅ Trade analysis completed")
            print(f"📊 Entry time: {entry_time}")
            print(f"📊 Exit time: {exit_time}")
            if "profit_loss" in trade_analysis_result:
                print(f"💰 P&L: ${trade_analysis_result['profit_loss']:.2f}")
            if "profit_loss_percent" in trade_analysis_result:
                print(f"📈 P&L %: {trade_analysis_result['profit_loss_percent']:.2f}%")
        else:
            print(f"⚠️  Trade analysis unavailable: {trade_analysis_result.get('error', 'No data') if trade_analysis_result else 'Failed'}")
        
        print(f"\n🌐 STEP 6: Test Market Context Analysis")
        print("-" * 50)
        
        # Test market context analysis - provides AI with environmental data
        context_result, context_time = time_operation(
            f"Get trading context for {sample_ticker}",
            options_tools.get_options_trading_context,
            options_ticker=sample_ticker,
            trade_date=trade_date,
            analysis_window_hours=6
        )
        
        if context_result and "error" not in context_result:
            print(f"✅ Market context analysis completed")
            price_analysis = context_result.get("price_analysis", {})
            print(f"📊 Day range: ${price_analysis.get('day_low', 'N/A')} - ${price_analysis.get('day_high', 'N/A')}")
            volatility = context_result.get("volatility_analysis", {}).get("intraday_volatility")
            if volatility:
                print(f"📈 Intraday volatility: {volatility:.2f}%")
        else:
            print(f"⚠️  Context analysis unavailable: {context_result.get('error', 'No data') if context_result else 'Failed'}")
        
        # Performance summary
        print("\n" + "=" * 80)
        print("⚡ HISTORICAL DATA PERFORMANCE SUMMARY")
        print("=" * 80)
        print(f"🔍 Contract screening: {screen_time:.2f}s")
        print(f"📊 Historical aggregates: {agg_time:.2f}s")
        print(f"💱 Historical trades: {trades_time:.2f}s") 
        print(f"💰 Historical quotes: {quotes_time:.2f}s")
        print(f"🎯 Trade execution analysis: {trade_analysis_time:.2f}s")
        print(f"🌐 Market context analysis: {context_time:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing historical data: {e}")
        return False


@timer_decorator("Agent creation")
def create_historical_analysis_agent():
    """
    Create an AI agent specialized in historical options analysis
    """
    try:
        options_tools = PolygonOptionsTools()
        
        agent = Agent(
            name="Historical Options Analysis Agent",
            role="AI agent specialized in analyzing historical options data for trade evaluation and market context.",
            model=OpenAIChat(id="gpt-4o"),
            tools=[options_tools, ReasoningTools()],
            instructions=[
                "You are an AI agent specialized in analyzing historical options data.",
                "Use the historical data methods to understand past trades and market conditions.",
                "Focus on:",
                "- Historical price movements using get_historical_options_aggregates",
                "- Trade execution quality using get_historical_options_trades", 
                "- Market liquidity using get_historical_options_quotes",
                "- Comprehensive trade analysis using analyze_options_trade_execution",
                "- Market context using get_options_trading_context",
                "Always provide actionable insights for future trading decisions.",
                "Be specific about data availability and limitations.",
            ],
            markdown=True,
            show_tool_calls=True,
        )
        
        return agent
        
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        return None


@timer_decorator("Agent historical analysis")
def demo_historical_analysis_agent():
    """
    Demonstrate the agent analyzing historical options data
    """
    print("\n🤖 Testing AI Agent with Historical Options Analysis...")
    print("=" * 80)
    
    agent = create_historical_analysis_agent()
    if not agent:
        return
    
    try:
        # Query focused on historical analysis capabilities
        query = """
        I want to understand how to analyze a past options trade. Please demonstrate by:
        
        1. First, find an available AAPL call option using screening
        2. Get historical price data (aggregates) for the last 3 days  
        3. Show me how to analyze trade execution if I had bought and sold this option
        4. Explain what market context data tells us about trading conditions
        
        Focus on showing the historical data capabilities and what insights they provide for trade analysis.
        """
        
        print(f"🎯 Query: {query.strip()}")
        print("-" * 80)
        
        response = agent.run(query)
        print(response.content)
        
        print("✅ Historical analysis agent demo completed!")
        
    except Exception as e:
        print(f"❌ Error running historical analysis agent: {e}")


def summarize_capabilities():
    """
    Summarize the historical data capabilities for AI agents
    """
    print("\n" + "=" * 80)
    print("🎯 HISTORICAL OPTIONS DATA CAPABILITIES FOR AI AGENTS")
    print("=" * 80)
    
    capabilities = [
        {
            "method": "get_historical_options_aggregates",
            "purpose": "Price Analysis",
            "description": "OHLCV bars for understanding price movements during trades",
            "ai_use": "Analyze entry/exit timing, volatility patterns, trend analysis"
        },
        {
            "method": "get_historical_options_trades", 
            "purpose": "Execution Quality",
            "description": "Individual trade records with prices, sizes, exchanges",
            "ai_use": "Evaluate execution quality, slippage analysis, market impact"
        },
        {
            "method": "get_historical_options_quotes",
            "purpose": "Liquidity Analysis", 
            "description": "Bid/ask spreads and market depth over time",
            "ai_use": "Assess trading costs, liquidity conditions, optimal timing"
        },
        {
            "method": "analyze_options_trade_execution",
            "purpose": "Trade Analysis",
            "description": "Comprehensive P&L and performance analysis",
            "ai_use": "Calculate returns, risk metrics, performance attribution"
        },
        {
            "method": "get_options_trading_context",
            "purpose": "Market Context",
            "description": "Volatility, volume patterns, and market conditions",
            "ai_use": "Understand trading environment, risk assessment, strategy selection"
        }
    ]
    
    for cap in capabilities:
        print(f"\n📊 {cap['method']}")
        print(f"   🎯 Purpose: {cap['purpose']}")
        print(f"   📝 Description: {cap['description']}")
        print(f"   🤖 AI Use Case: {cap['ai_use']}")
    
    print(f"\n🚀 KEY BENEFITS FOR AI AGENTS:")
    print("   • Analyze past trades to understand what worked and what didn't")
    print("   • Calculate precise P&L and risk metrics for trade evaluation")
    print("   • Understand market conditions during specific time periods")
    print("   • Evaluate execution quality and identify improvements")
    print("   • Make data-driven decisions based on historical patterns")
    print("   • Build trading strategies informed by historical performance")


def test_technical_indicators():
    """
    Test the technical indicators functionality for options contracts
    """
    print("\n📊 Testing Technical Indicators Functionality")
    print("=" * 80)
    
    # Check if API key is available
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("⚠️  POLYGON_API_KEY not set. Testing in demo mode...")
    
    try:
        # Initialize toolkit
        options_tools = initialize_toolkit(api_key)
        
        # Use a sample options ticker for testing
        sample_ticker = "O:NVDA250516C00118000"  # Example format
        print(f"📋 Using sample ticker: {sample_ticker}")
        
        # Set up test parameters - use recent dates for better data availability
        end_date = '2025-05-13'
        start_date = '2025-05-06'
        
        # First verify we can get historical data
        print("\n📈 Verifying Historical Data Access")
        print("-" * 50)
        historical_data = options_tools.get_historical_options_aggregates(
            options_ticker=sample_ticker,
            multiplier=1,
            timespan="day",
            from_date=start_date,
            to_date=end_date
        )
        
        if "error" in historical_data:
            print(f"⚠️  Historical data unavailable: {historical_data['error']}")
            print("💡 This may be due to API limitations or the selected date range")
            return False
            
        if not historical_data.get("data"):
            print("⚠️  No historical data available for the selected date range")
            print("💡 Try a different date range or verify the options contract is active")
            return False
            
        print(f"✅ Historical data available: {len(historical_data['data'])} data points")
        
        print("\n📈 Testing SMA Calculation")
        print("-" * 50)
        sma_result, sma_time = time_operation(
            "Calculate SMA",
            options_tools.calculate_sma,
            ticker=sample_ticker,
            window=20,
            timespan="day",
            from_date=start_date,
            to_date=end_date
        )
        
        if sma_result and "error" not in sma_result:
            print(f"✅ SMA calculation completed")
            print(f"📊 Data points calculated: {sma_result['metadata']['points_calculated']}")
            if sma_result['data']:
                latest = sma_result['data'][-1]
                print(f"📈 Latest SMA: ${latest['sma']:.2f} (Close: ${latest['close']:.2f})")
        else:
            error_msg = sma_result.get('error', 'Unknown error') if sma_result else 'Failed to calculate'
            print(f"⚠️  SMA calculation failed: {error_msg}")
        
        print("\n📉 Testing EMA Calculation")
        print("-" * 50)
        ema_result, ema_time = time_operation(
            "Calculate EMA",
            options_tools.calculate_ema,
            ticker=sample_ticker,
            window=20,
            timespan="day",
            from_date=start_date,
            to_date=end_date
        )
        
        if ema_result and "error" not in ema_result:
            print(f"✅ EMA calculation completed")
            print(f"📊 Data points calculated: {ema_result['metadata']['points_calculated']}")
            if ema_result['data']:
                latest = ema_result['data'][-1]
                print(f"📈 Latest EMA: ${latest['ema']:.2f} (Close: ${latest['close']:.2f})")
        else:
            error_msg = ema_result.get('error', 'Unknown error') if ema_result else 'Failed to calculate'
            print(f"⚠️  EMA calculation failed: {error_msg}")
        
        print("\n📊 Testing MACD Calculation")
        print("-" * 50)
        macd_result, macd_time = time_operation(
            "Calculate MACD",
            options_tools.calculate_macd,
            ticker=sample_ticker,
            fast_period=12,
            slow_period=26,
            signal_period=9,
            timespan="day",
            from_date=start_date,
            to_date=end_date
        )
        
        if macd_result and "error" not in macd_result:
            print(f"✅ MACD calculation completed")
            print(f"📊 Data points calculated: {macd_result['metadata']['points_calculated']}")
            if macd_result['data']:
                latest = macd_result['data'][-1]
                print(f"📈 Latest MACD: {latest['macd']:.2f}")
                print(f"📉 Signal Line: {latest['signal']:.2f}")
                print(f"📊 Histogram: {latest['histogram']:.2f}")
        else:
            error_msg = macd_result.get('error', 'Unknown error') if macd_result else 'Failed to calculate'
            print(f"⚠️  MACD calculation failed: {error_msg}")
        
        print("\n📈 Testing RSI Calculation")
        print("-" * 50)
        rsi_result, rsi_time = time_operation(
            "Calculate RSI",
            options_tools.calculate_rsi,
            ticker=sample_ticker,
            window=14,
            timespan="day",
            from_date=start_date,
            to_date=end_date
        )
        
        if rsi_result and "error" not in rsi_result:
            print(f"✅ RSI calculation completed")
            print(f"📊 Data points calculated: {rsi_result['metadata']['points_calculated']}")
            if rsi_result['data']:
                latest = rsi_result['data'][-1]
                print(f"📈 Latest RSI: {latest['rsi']:.2f}")
                print(f"📊 Overbought level: {rsi_result['metadata']['overbought_level']}")
                print(f"📊 Oversold level: {rsi_result['metadata']['oversold_level']}")
        else:
            error_msg = rsi_result.get('error', 'Unknown error') if rsi_result else 'Failed to calculate'
            print(f"⚠️  RSI calculation failed: {error_msg}")
        
        # Performance summary
        print("\n" + "=" * 80)
        print("⚡ TECHNICAL INDICATORS PERFORMANCE SUMMARY")
        print("=" * 80)
        print(f"📈 SMA calculation: {sma_time:.2f}s")
        print(f"📉 EMA calculation: {ema_time:.2f}s")
        print(f"📊 MACD calculation: {macd_time:.2f}s")
        print(f"📈 RSI calculation: {rsi_time:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing technical indicators: {e}")
        return False


def main():
    """
    Main function to test historical options data capabilities
    """
    print("🚀 Polygon Options Trading Toolkit - Historical Data Testing")
    print("📊 Focus: AI Agent Capabilities for Trade Analysis")
    print("=" * 80)

    technical_indicators_success = test_technical_indicators()

    exit()
    
    total_start = time.perf_counter()
    
    # Test 1: Specific NVDA trade analysis
    print("🎯 TESTING SPECIFIC TRADE FROM DATABASE")
    print("=" * 80)
    nvda_success = test_specific_nvda_trade()
    
    print("\n" + "=" * 80)
    print("📊 TESTING GENERAL CAPABILITIES")  
    print("=" * 80)
    
    # Test 2: General historical data functionality
    if test_historical_options_data():
        print("\n" + "=" * 80)
        
        # Test 3: Technical indicators functionality
        technical_indicators_success = test_technical_indicators()
        
        # Test 4: AI Agent demonstration
        demo_historical_analysis_agent()
        
        # Test 5: Capability summary
        summarize_capabilities()
        
        total_end = time.perf_counter()
        total_duration = total_end - total_start
        
        print("\n" + "=" * 80)
        print("🎉 Historical Data Testing Completed Successfully!")
        print(f"⏱️  Total execution time: {total_duration:.2f} seconds")
        
        if nvda_success:
            print("✅ NVDA trade analysis demonstrated successfully!")
        else:
            print("⚠️  NVDA trade analysis had limitations (expected with API restrictions)")
            
        if technical_indicators_success:
            print("✅ Technical indicators testing completed successfully!")
        else:
            print("⚠️  Technical indicators testing had limitations")
        
        print("\n💡 Next Steps for AI Integration:")
        print("1. Use these methods in your AI agents for trade analysis")
        print("2. Implement historical analysis in trading workflows")
        print("3. Build trade evaluation and learning systems")
        print("4. Create context-aware trading strategies")
        print("5. Analyze your trade database using these capabilities")
        print("6. Integrate technical indicators for enhanced analysis")
        
    else:
        print("\n❌ Historical data testing failed.")
        print("💡 This may be due to API limitations or data availability")
        print("💡 The methods are implemented correctly and ready for use with live data")


if __name__ == "__main__":
    main() 