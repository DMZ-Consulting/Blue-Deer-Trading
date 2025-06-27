"""
Example usage of the Theta Data Options Toolkit

This example demonstrates how to use the ThetaDataOptionsTools toolkit
to retrieve historical options data from the Theta Data API.

Prerequisites:
1. Theta Data subscription (at least free tier for EOD data)
2. Theta Data Terminal running locally on port 25510
3. The required Python packages (agno, requests, pandas, etc.)
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path to import the toolkit
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from toolkits.theta_data_options import ThetaDataOptionsTools


def main():
    """Main example function"""
    print("🚀 Theta Data Options Toolkit Example")
    print("=" * 50)
    
    # Initialize the toolkit
    theta_tools = ThetaDataOptionsTools()
    
    # Example parameters for AAPL options
    root = "AAPL"
    exp = 20240315  # March 15, 2024 expiration
    strike = 180000  # $180.00 strike (in 1/10th cent format)
    right = "C"  # Call option
    
    # Date range for historical data (example: one day)
    start_date = 20240301  # March 1, 2024
    end_date = 20240301    # March 1, 2024
    
    print(f"📊 Getting data for {root} {strike/100000:.2f} {right} expiring {exp}")
    print(f"📅 Date range: {start_date} to {end_date}")
    print()
    
    # Example 1: List available expirations for AAPL
    print("1️⃣ Listing available expirations for AAPL...")
    expirations = theta_tools.list_options_expirations(root)
    
    if expirations["success"]:
        print(f"✅ Found {expirations['count']} expirations")
        # Show first 5 expirations
        for i, exp_info in enumerate(expirations["expirations"][:5]):
            print(f"   {i+1}. {exp_info['formatted_date']} ({exp_info['days_to_expiration']} days)")
    else:
        print(f"❌ Error: {expirations['error']}")
    
    print()
    
    # Example 2: List available strikes for a specific expiration
    print(f"2️⃣ Listing available strikes for {root} expiring {exp}...")
    strikes = theta_tools.list_options_strikes(root, exp)
    
    if strikes["success"]:
        print(f"✅ Found {strikes['count']} strikes")
        # Show ATM strikes (around $180)
        for strike_info in strikes["strikes"]:
            if 175.0 <= strike_info["strike_price_dollars"] <= 185.0:
                print(f"   ${strike_info['strike_price_dollars']:.2f}")
    else:
        print(f"❌ Error: {strikes['error']}")
    
    print()
    
    # Example 3: Get historical OHLC data
    print("3️⃣ Getting historical OHLC data...")
    ohlc_data = theta_tools.get_historical_options_ohlc(
        root=root,
        exp=exp,
        strike=strike,
        right=right,
        start_date=start_date,
        end_date=end_date,
        ivl=60000,  # 1-minute intervals
        rth=True
    )
    
    if ohlc_data["success"]:
        print(f"✅ Retrieved {ohlc_data['count']} OHLC records")
        print(f"   Contract: {ohlc_data['contract']['root']} ${ohlc_data['contract']['strike_price_dollars']:.2f} {ohlc_data['contract']['right']}")
        print(f"   Expiration: {ohlc_data['contract']['expiration_date_formatted']}")
        
        # Show first few records if available
        if ohlc_data["data"]:
            print("   Sample data:")
            for i, record in enumerate(ohlc_data["data"][:3]):
                time_str = record.get("time_formatted", "N/A")
                open_price = record.get("open", 0)
                high_price = record.get("high", 0)
                low_price = record.get("low", 0)
                close_price = record.get("close", 0)
                volume = record.get("volume", 0)
                print(f"     {time_str}: O:{open_price:.2f} H:{high_price:.2f} L:{low_price:.2f} C:{close_price:.2f} V:{volume}")
    else:
        print(f"❌ Error: {ohlc_data['error']}")
    
    print()
    
    # Example 4: Get historical quotes (bid/ask)
    print("4️⃣ Getting historical quotes data...")
    quotes_data = theta_tools.get_historical_options_quotes(
        root=root,
        exp=exp,
        strike=strike,
        right=right,
        start_date=start_date,
        end_date=end_date,
        ivl=0,  # Tick-level data
        rth=True
    )
    
    if quotes_data["success"]:
        print(f"✅ Retrieved {quotes_data['count']} quote records")
        
        # Show first few records if available
        if quotes_data["data"]:
            print("   Sample quote data:")
            for i, record in enumerate(quotes_data["data"][:3]):
                time_str = record.get("time_formatted", "N/A")
                bid = record.get("bid", 0)
                ask = record.get("ask", 0)
                bid_size = record.get("bid_size", 0)
                ask_size = record.get("ask_size", 0)
                print(f"     {time_str}: Bid:{bid:.2f}x{bid_size} Ask:{ask:.2f}x{ask_size}")
    else:
        print(f"❌ Error: {quotes_data['error']}")
    
    print()
    
    # Example 5: Get Greeks data
    print("5️⃣ Getting historical Greeks data...")
    greeks_data = theta_tools.get_historical_options_greeks(
        root=root,
        exp=exp,
        strike=strike,
        right=right,
        start_date=start_date,
        end_date=end_date,
        ivl=900000,  # 15-minute intervals
        rth=True
    )
    
    if greeks_data["success"]:
        print(f"✅ Retrieved {greeks_data['count']} Greeks records")
        
        # Show first few records if available
        if greeks_data["data"]:
            print("   Sample Greeks data:")
            for i, record in enumerate(greeks_data["data"][:3]):
                time_str = record.get("time_formatted", "N/A")
                delta = record.get("delta", 0)
                gamma = record.get("gamma", 0)
                theta = record.get("theta", 0)
                vega = record.get("vega", 0)
                iv = record.get("implied_vol", 0)
                print(f"     {time_str}: Δ:{delta:.4f} Γ:{gamma:.4f} Θ:{theta:.4f} ν:{vega:.4f} IV:{iv:.4f}")
    else:
        print(f"❌ Error: {greeks_data['error']}")
    
    print()
    
    # Example 6: Analyze the data
    if ohlc_data["success"]:
        print("6️⃣ Analyzing OHLC data...")
        analysis = theta_tools.analyze_options_historical_data(ohlc_data, "summary")
        
        if analysis["success"]:
            print("✅ Analysis complete:")
            summary = analysis["summary"]
            print(f"   Total records: {summary['total_records']}")
            if "price_range" in summary:
                print(f"   Price range: ${summary['price_range']['min']:.2f} - ${summary['price_range']['max']:.2f}")
                print(f"   Average close: ${summary['average_close']:.2f}")
                print(f"   Price change: ${summary['price_change']:.2f}")
        else:
            print(f"❌ Analysis error: {analysis['error']}")
    
    print()
    
    # Example 7: Comprehensive NVDA Call Analysis
    print("7️⃣ Comprehensive NVDA Call Options Analysis...")
    print("=" * 60)
    
    # NVDA call parameters for May 2025 expiration
    nvda_root = "NVDA"
    nvda_exp = 20250516  # May 16, 2025 expiration
    nvda_strike = 118000  # $118.00 strike (in 1/10th cent format)
    nvda_right = "C"  # Call option
    nvda_start_date = 20250506  # May 6, 2025
    nvda_end_date = 20250513    # May 13, 2025
    
    print(f"🎯 Analyzing {nvda_root} ${nvda_strike/1000:.2f} {nvda_right} expiring {nvda_exp}")
    print(f"📅 Analysis period: {nvda_start_date} to {nvda_end_date}")
    print()
    
    # Get comprehensive data for NVDA
    nvda_data = {}
    
    # 7a: OHLC Data with 5-minute intervals
    print("📈 Getting NVDA OHLC data (5-minute intervals)...")
    nvda_ohlc = theta_tools.get_historical_options_ohlc(
        root=nvda_root,
        exp=nvda_exp,
        strike=nvda_strike,
        right=nvda_right,
        start_date=nvda_start_date,
        end_date=nvda_end_date,
        ivl=300000,  # 5-minute intervals
        rth=True
    )
    nvda_data['ohlc'] = nvda_ohlc
    
    if nvda_ohlc["success"]:
        print(f"✅ Retrieved {nvda_ohlc['count']} OHLC records")
        if nvda_ohlc["data"]:
            first_record = nvda_ohlc["data"][0]
            last_record = nvda_ohlc["data"][-1]
            print(f"   Opening price: ${first_record.get('open', 0):.2f}")
            print(f"   Closing price: ${last_record.get('close', 0):.2f}")
            print(f"   Price change: ${last_record.get('close', 0) - first_record.get('open', 0):.2f}")
    else:
        print(f"❌ OHLC Error: {nvda_ohlc['error']}")
    
    print()
    
    # 7b: Trade Data
    print("💰 Getting NVDA trade data...")
    nvda_trades = theta_tools.get_historical_options_trades(
        root=nvda_root,
        exp=nvda_exp,
        strike=nvda_strike,
        right=nvda_right,
        start_date=nvda_start_date,
        end_date=nvda_end_date,
        ivl=0,  # Tick-level trade data
        rth=True
    )
    nvda_data['trades'] = nvda_trades
    
    if nvda_trades["success"]:
        print(f"✅ Retrieved {nvda_trades['count']} trade records")
        if nvda_trades["data"]:
            # Calculate total volume and average price
            total_volume = sum(record.get('size', 0) for record in nvda_trades["data"])
            total_value = sum(record.get('price', 0) * record.get('size', 0) for record in nvda_trades["data"])
            avg_price = total_value / total_volume if total_volume > 0 else 0
            print(f"   Total volume: {total_volume:,} contracts")
            print(f"   Volume-weighted avg price: ${avg_price:.2f}")
    else:
        print(f"❌ Trades Error: {nvda_trades['error']}")
    
    print()
    
    # 7c: Greeks Data
    print("🔬 Getting NVDA Greeks data (15-minute intervals)...")
    nvda_greeks = theta_tools.get_historical_options_greeks(
        root=nvda_root,
        exp=nvda_exp,
        strike=nvda_strike,
        right=nvda_right,
        start_date=nvda_start_date,
        end_date=nvda_end_date,
        ivl=900000,  # 15-minute intervals
        rth=True
    )
    nvda_data['greeks'] = nvda_greeks
    
    if nvda_greeks["success"]:
        print(f"✅ Retrieved {nvda_greeks['count']} Greeks records")
        if nvda_greeks["data"]:
            first_greeks = nvda_greeks["data"][0]
            last_greeks = nvda_greeks["data"][-1]
            print(f"   Initial IV: {first_greeks.get('implied_vol', 0):.4f}")
            print(f"   Final IV: {last_greeks.get('implied_vol', 0):.4f}")
            print(f"   IV change: {last_greeks.get('implied_vol', 0) - first_greeks.get('implied_vol', 0):.4f}")
            print(f"   Final Delta: {last_greeks.get('delta', 0):.4f}")
            print(f"   Final Gamma: {last_greeks.get('gamma', 0):.4f}")
            print(f"   Final Theta: {last_greeks.get('theta', 0):.4f}")
    else:
        print(f"❌ Greeks Error: {nvda_greeks['error']}")
    
    print()
    
    # 7d: Implied Volatility Data
    print("📊 Getting NVDA implied volatility data...")
    nvda_iv = theta_tools.get_historical_options_implied_volatility(
        root=nvda_root,
        exp=nvda_exp,
        strike=nvda_strike,
        right=nvda_right,
        start_date=nvda_start_date,
        end_date=nvda_end_date,
        ivl=300000,  # 5-minute intervals
        rth=True
    )
    nvda_data['implied_volatility'] = nvda_iv
    
    if nvda_iv["success"]:
        print(f"✅ Retrieved {nvda_iv['count']} implied volatility records")
        if nvda_iv["data"]:
            first_iv = nvda_iv["data"][0]
            last_iv = nvda_iv["data"][-1]
            print(f"   Initial mid IV: {first_iv.get('implied_vol', 0):.4f} ({first_iv.get('implied_vol', 0):.1%})")
            print(f"   Final mid IV: {last_iv.get('implied_vol', 0):.4f} ({last_iv.get('implied_vol', 0):.1%})")
            print(f"   IV change: {last_iv.get('implied_vol', 0) - first_iv.get('implied_vol', 0):+.4f}")
            
            # Show bid-ask IV spread
            if 'bid_implied_vol' in last_iv and 'ask_implied_vol' in last_iv:
                iv_spread = last_iv.get('ask_implied_vol', 0) - last_iv.get('bid_implied_vol', 0)
                print(f"   Final IV spread: {iv_spread:.4f} (bid: {last_iv.get('bid_implied_vol', 0):.4f}, ask: {last_iv.get('ask_implied_vol', 0):.4f})")
    else:
        print(f"❌ Implied Volatility Error: {nvda_iv['error']}")
    
    print()
    
    # 7e: Open Interest Data
    print("📊 Getting NVDA open interest data...")
    nvda_oi = theta_tools.get_historical_options_open_interest(
        root=nvda_root,
        exp=nvda_exp,
        strike=nvda_strike,
        right=nvda_right,
        start_date=nvda_start_date,
        end_date=nvda_end_date
    )
    nvda_data['open_interest'] = nvda_oi
    
    if nvda_oi["success"]:
        print(f"✅ Retrieved {nvda_oi['count']} open interest records")
        if nvda_oi["data"]:
            first_oi = nvda_oi["data"][0].get('open_interest', 0)
            last_oi = nvda_oi["data"][-1].get('open_interest', 0)
            print(f"   Initial OI: {first_oi:,} contracts")
            print(f"   Final OI: {last_oi:,} contracts")
            print(f"   OI change: {last_oi - first_oi:,} contracts")
    else:
        print(f"❌ Open Interest Error: {nvda_oi['error']}")
    
    print()
    
    # 7f: Comprehensive Analysis
    print("🧮 Performing comprehensive analysis...")
    analysis_results = {}
    
    # Analyze each data type
    for data_type, data in nvda_data.items():
        if data["success"]:
            analysis = theta_tools.analyze_options_historical_data(data, "summary")
            if analysis["success"]:
                analysis_results[data_type] = analysis["summary"]
    
    # Print analysis summary
    if analysis_results:
        print("✅ Analysis Summary:")
        for data_type, summary in analysis_results.items():
            print(f"   📋 {data_type.upper()} Analysis:")
            print(f"      • Total records: {summary.get('total_records', 0)}")
            if 'price_range' in summary:
                price_range = summary['price_range']
                print(f"      • Price range: ${price_range['min']:.2f} - ${price_range['max']:.2f}")
                print(f"      • Price volatility: {((price_range['max'] - price_range['min']) / price_range['min'] * 100):.2f}%")
            if 'average_close' in summary:
                print(f"      • Average price: ${summary['average_close']:.2f}")
            if 'price_change' in summary:
                print(f"      • Price change: ${summary['price_change']:.2f}")
            print()
    
    # Perform specific IV analysis if available
    if nvda_iv["success"]:
        iv_analysis = theta_tools.analyze_options_historical_data(nvda_iv, "implied_volatility")
        if iv_analysis["success"]:
            print("   📊 Implied Volatility Analysis:")
            iv_stats = iv_analysis["iv_analysis"]["iv_statistics"]
            if "mid_iv" in iv_stats:
                mid_iv = iv_stats["mid_iv"]
                print(f"      • IV range: {mid_iv['min']:.4f} - {mid_iv['max']:.4f}")
                print(f"      • Average IV: {mid_iv['average']:.4f} ({mid_iv['average']:.1%})")
                print(f"      • IV change: {mid_iv['change']:+.4f} ({mid_iv['change_percent']:+.1f}%)")
            
            if "iv_level" in iv_analysis["iv_analysis"]:
                iv_level = iv_analysis["iv_analysis"]["iv_level"]
                print(f"      • IV classification: {iv_level['classification']}")
            print()
    
    # 7g: Generate trading insights
    print("💡 Trading Insights:")
    if nvda_ohlc["success"] and nvda_ohlc["data"]:
        price_data = nvda_ohlc["data"]
        prices = [record.get('close', 0) for record in price_data if record.get('close', 0) > 0]
        
        if len(prices) >= 2:
            price_trend = "📈 Bullish" if prices[-1] > prices[0] else "📉 Bearish"
            price_change_pct = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] > 0 else 0
            print(f"   • Price trend: {price_trend} ({price_change_pct:+.2f}%)")
            
            # Calculate simple moving average
            if len(prices) >= 5:
                sma_5 = sum(prices[-5:]) / 5
                current_vs_sma = "above" if prices[-1] > sma_5 else "below"
                print(f"   • Current price vs 5-period SMA: {current_vs_sma}")
    
    if nvda_greeks["success"] and nvda_greeks["data"]:
        greeks_data = nvda_greeks["data"]
        if greeks_data:
            final_delta = greeks_data[-1].get('delta', 0)
            final_iv = greeks_data[-1].get('implied_vol', 0)
            
            moneyness = "ITM" if final_delta > 0.5 else "OTM" if final_delta < 0.5 else "ATM"
            iv_level = "High" if final_iv > 0.3 else "Low" if final_iv < 0.2 else "Moderate"
            
            print(f"   • Option moneyness: {moneyness} (Δ={final_delta:.3f})")
            print(f"   • Implied volatility: {iv_level} ({final_iv:.1%})")
    
    print()
    print("🎯 NVDA Analysis Complete!")
    print("=" * 60)
    print()
    print("🎉 All examples complete!")
    print("\n💡 Tips:")
    print("   • Make sure Theta Data Terminal is running on port 25510")
    print("   • Free tier provides EOD data going back 1+ years")
    print("   • Paid tiers provide intraday and tick-level data")
    print("   • Strike prices are in 1/10th cent format (170000 = $170.00)")
    print("   • Dates are in YYYYMMDD format")
    print("   • NVDA example shows comprehensive multi-timeframe analysis")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Example interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Make sure the Theta Data Terminal is running and you have the required dependencies.") 