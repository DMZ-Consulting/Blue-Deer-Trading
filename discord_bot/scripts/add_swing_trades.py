import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"  # Adjust this to your API's URL

def parse_date(date_str):
    """Convert date string to ISO format"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%m/%d/%y").isoformat()
    except ValueError:
        return None

def add_trade(trade_data):
    """Add a trade (common or option)"""
    url = f"{BASE_URL}/trades/"  # Updated endpoint
    
    # Determine if the trade is an option or common stock
    is_option = "strike" in trade_data
    payload = {
        "symbol": trade_data["symbol"],
        "trade_type": trade_data["trade_type"].lower(),
        "entry_price": float(trade_data["price"]),
        "size": str(trade_data["size"]),
        "is_contract": is_option,
        "is_day_trade": False,
        "status": "open",  # Added required field
        "trade_group": "swing_trader",  # Added required field
        "configuration_id": trade_data["configuration_id"]
    }
    
    if is_option:
        payload["strike"] = float(trade_data["strike"])
        payload["option_type"] = trade_data["option_type"].upper()
        payload["expiration_date"] = parse_date(trade_data["expiration_date"])
    else:
        if "expiration_date" in trade_data:
            payload["expiration_date"] = parse_date(trade_data["expiration_date"])
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(f"Successfully added {'option' if is_option else 'common'} trade for {trade_data['symbol']}")
    else:
        print(f"Error adding {'option' if is_option else 'common'} trade for {trade_data['symbol']}: {response.text}")

def add_options_strategy(strategy_data):
    """Add an options strategy trade"""
    url = f"{BASE_URL}/trades/options-strategy"  # Updated endpoint
    
    payload = {
        "name": strategy_data["name"],
        "underlying_symbol": strategy_data["underlying_symbol"],
        "trade_group": strategy_data["trade_group"],
        "status": strategy_data["status"],
        "legs": strategy_data["legs"],
        "net_cost": float(strategy_data["net_cost"]),
        "size": str(strategy_data["size"]),
        "current_size": str(strategy_data["size"]),  # Added required field
        "average_net_cost": float(strategy_data["net_cost"]),  # Added required field
        "configuration_id": strategy_data["configuration_id"]
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(f"Successfully added options strategy {strategy_data['name']}")
    else:
        print(f"Error adding options strategy {strategy_data['name']}: {response.text}")

# Combined trades data
trades = [
    {"symbol": "UVXY", "trade_type": "BTO", "price": 26.44, "size": "3", "configuration_id":2},
    {"symbol": "COIN", "trade_type": "BTO", "price": 195.56, "size": "9", "configuration_id":2},
    {"symbol": "UVXY", "trade_type": "BTO", "price": 25.01, "size": "6", "configuration_id":2},
    {"symbol": "OXY", "trade_type": "BTO", "price": 50.75, "size": "6", "configuration_id":2},
    {"symbol": "CVNA", "trade_type": "STO", "price": 174.62, "size": "4", "configuration_id":2},
    {"symbol": "MSTR", "trade_type": "STO", "price": 190.74, "size": "2", "configuration_id":2},
    {"symbol": "SOXL", "trade_type": "STO", "price": 37.28, "size": "7", "configuration_id":2},
    {"symbol": "VIX", "strike": 45, "option_type": "CALL", "trade_type": "BTO", "price": 0.51, "size": "6", "expiration_date": "11/20/24", "configuration_id":2},
    {"symbol": "VIX", "strike": 25, "option_type": "CALL", "trade_type": "BTO", "price": 1.38, "size": "6", "expiration_date": "11/20/24", "configuration_id":2},
    {"symbol": "OXY", "strike": 55, "option_type": "CALL", "trade_type": "BTO", "price": 1.97, "size": "6", "expiration_date": "11/15/24", "configuration_id":2},
    {"symbol": "OXY", "strike": 60, "option_type": "CALL", "trade_type": "BTO", "price": 0.62, "size": "6", "expiration_date": "12/20/24", "configuration_id":2},
    {"symbol": "OXY", "strike": 60, "option_type": "CALL", "trade_type": "BTO", "price": 0.62, "size": "6", "expiration_date": "12/20/24", "configuration_id":2},
    {"symbol": "XLE", "strike": 100, "option_type": "CALL", "trade_type": "BTO", "price": 4.30, "size": "2", "expiration_date": "1/1/25", "configuration_id":2},
    {"symbol": "COIN", "strike": 160, "option_type": "PUT", "trade_type": "BTO", "price": 7.80, "size": "6", "expiration_date": "11/1/24", "configuration_id":2}, # HEDGE
]

options_strategy_trades = [
    {"name" : "NVDA Cal Spread", "underlying_symbol": "NVDA", "trade_group": "swing_trader", "status": "open", "legs": "NVDA011725130C-NVDA011525130P", "net_cost": 6.35, "size": "6", "configuration_id":2},
    {"name" : "VIX Strangle", "underlying_symbol": "VIX", "trade_group": "swing_trader", "status": "open", "legs": "VIX11202435C-VIX11202445C", "net_cost": 0.22, "size": "3", "configuration_id":2},
    {"name" : "GLD/OXY Bull Call Spread", "underlying_symbol": "GLD", "trade_group": "swing_trader", "status": "open", "legs": "GLD122024245C-OXY122024250C", "net_cost": 0.27, "size": "10", "configuration_id":2},
    {"name" : "OXY Bull Call Spread", "underlying_symbol": "OXY", "trade_group": "swing_trader", "status": "open", "legs": "OXY011726090C-OXY011726100C", "net_cost": 0.32, "size": "6", "configuration_id":2},
]

def main():
    # Add trades
    print("Adding trades...")
    for trade in trades:
        add_trade(trade)
    
    # Add options strategy trades
    print("\nAdding options strategy trades...")
    for strategy in options_strategy_trades:
        add_options_strategy(strategy)

if __name__ == "__main__":
    main()