from collections import defaultdict
import json
import os
import re
from datetime import datetime

def parse_trades(file_path):
    unsorted_trades = []
    
    # First, read all trades and store them with their timestamps
    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, 1):
            if '**LOTTO**' in line or '**BUY**' in line or '**SELL**' in line or '**TRIM**' in line or '**ADD**' in line:
                trade = parse_trade(line, line_number)
                timestamp = datetime.strptime(f"{trade['date']} {trade['time']}", '%Y-%m-%d %H:%M:%S')
                unsorted_trades.append((timestamp, trade))
    
    # Sort trades by timestamp
    sorted_trades = sorted(unsorted_trades, key=lambda x: x[0])
    
    trades = []
    trade_groups = defaultdict(list)
    group_counter = defaultdict(int)
    open_groups = set()
    closed_groups = set()
    group_positions = defaultdict(int)  # Track position size for each group

    for _, trade in sorted_trades:
        # Create a unique identifier for the trade group
        group_id = create_group_id(trade)
        if group_id:
            current_group_id = f"{group_id}_{group_counter[group_id]}"
            
            if trade['type'] == 'ENTRY':
                # Start a new group if it's an entry
                group_counter[group_id] += 1
                current_group_id = f"{group_id}_{group_counter[group_id]}"
                open_groups.add(current_group_id)
                group_positions[current_group_id] = trade['size']
            elif current_group_id in open_groups:
                # Adjust the trade type based on the current position
                trade = adjust_trade_type(trade, group_positions[current_group_id])
                
                # Update the position size
                if trade['type'] == 'ADJUSTMENT':
                    if trade['adjustmentType'] == 'ADD':
                        group_positions[current_group_id] += trade['size']
                    elif trade['adjustmentType'] == 'TRIM':
                        group_positions[current_group_id] -= trade['size']
                elif trade['type'] == 'EXIT':
                    group_positions[current_group_id] = 0
            else:
                # If it's not an entry and the group is not open, skip this trade
                continue
            
            trade['groupId'] = current_group_id
            trade_groups[current_group_id].append(trade)
            
            # If this is an exit trade, move the group from open to closed
            if trade['type'] == 'EXIT':
                open_groups.remove(current_group_id)
                closed_groups.add(current_group_id)

        trades.append(trade)

    # Link related trades
    linked_trades = link_related_trades(trades, trade_groups)
    return linked_trades

def adjust_trade_type(trade, current_position):
    if trade['type'] == 'EXIT' and trade['size'] < current_position:
        trade['type'] = 'ADJUSTMENT'
        trade['adjustmentType'] = 'TRIM'
    return trade

def create_group_id(trade):
    if trade['asset'] != 'Unspecified' and trade['strike'] and trade['expiration']:
        return f"{trade['asset']}_{trade['strike']}_{trade['expiration']}"
    return None

def link_related_trades(trades, trade_groups):
    for trade in trades:
        if 'groupId' in trade:
            group = trade_groups[trade['groupId']]
            trade['relatedTrades'] = [
                {
                    'lineNumber': t['lineNumber'],
                    'type': t['type'],
                    'adjustmentType': t['adjustmentType'],
                    'date': t['date'],
                    'time': t['time']
                }
                for t in group if t['lineNumber'] != trade['lineNumber']
            ]
    return trades

def parse_trade(line, line_number):
    # Extract date and time
    date_time_match = re.search(r'(\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})', line)
    if date_time_match:
        date_time = datetime.strptime(date_time_match.group(1), '%m/%d/%y %H:%M:%S')
    else:
        date_time = None

    # Extract trade details
    details = line.split('**LOTTO**' if '**LOTTO**' in line else '**' in line and line.split('**')[1])[-1].strip()

    # Parse trade type and direction
    trade_type, direction, adjustment_type = parse_trade_type(line, details)

    # Parse asset, strike, expiration, and contract type
    asset, strike, expiration, contract_type = parse_asset_details(details)

    # Parse price and size
    price, size = parse_price_size(details)

    return {
        "lineNumber": line_number,
        "originalText": line.strip(),
        "date": date_time.strftime('%Y-%m-%d') if date_time else None,
        "time": date_time.strftime('%H:%M:%S') if date_time else None,
        "type": trade_type,
        "adjustmentType": adjustment_type,
        "direction": direction,
        "asset": asset,
        "strike": strike,
        "expiration": expiration,
        "contractType": contract_type,
        "price": price,
        "size": size,
        "isLotto": '**LOTTO**' in line,
        "notes": f"{'LOTTO trade, ' if '**LOTTO**' in line else ''}{details}"
    }

def parse_trade_type(line, details):
    if '**BUY**' in line or 'Long' in details:
        return 'ENTRY', 'LONG', None
    elif '**SELL**' in line or 'exit' in details.lower() or 'out' in details.lower():
        return 'EXIT', 'SHORT' if 'short' in details.lower() else 'LONG', 'FULL_EXIT'
    elif '**ADD**' in line or 'add' in details.lower():
        return 'ADJUSTMENT', 'LONG', 'ADD'
    elif '**TRIM**' in line or 'trim' in details.lower():
        return 'ADJUSTMENT', 'LONG', 'TRIM'
    elif 'cover' in details.lower():
        return 'EXIT', 'SHORT', 'FULL_EXIT'
    elif 'short' in details.lower():
        return 'ENTRY', 'SHORT', None
    else:
        return 'ENTRY', 'LONG', None

def parse_asset_details(details):
    asset_match = re.search(r'\b([A-Z]{1,5})\b', details)
    asset = asset_match.group(1) if asset_match else 'Unspecified'

    strike_match = re.search(r'(\d+(?:/\d+)?[cp]?)', details)
    strike = strike_match.group(1) if strike_match else None

    expiration_match = re.search(r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?|weekly|same day|tomorrow xp|next week)', details, re.IGNORECASE)
    expiration = expiration_match.group(1) if expiration_match else None

    if strike:
        if 'c' in strike.lower():
            contract_type = 'CALL'
        elif 'p' in strike.lower():
            contract_type = 'PUT'
        else:
            contract_type = 'Unspecified'
    elif 'call' in details.lower():
        contract_type = 'CALL'
    elif 'put' in details.lower():
        contract_type = 'PUT'
    else:
        contract_type = 'Unspecified'

    return asset, strike, expiration, contract_type

def parse_price_size(details):
    price_match = re.search(r'(\d+(?:\.\d+)?)', details)
    price = float(price_match.group(1)) if price_match else None

    size_match = re.search(r'(\d+)x', details)
    size = int(size_match.group(1)) if size_match else None

    return price, size

def main(input_file, output_file):
    trades = parse_trades(input_file)
    with open(output_file, 'w') as f:
        json.dump(trades, f, indent=2)

if __name__ == "__main__":
    working_directory = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(working_directory, '../data/trade-alerts.txt')
    output_file = os.path.join(working_directory, '../data/all_trades.json')
    main(input_file, output_file)
