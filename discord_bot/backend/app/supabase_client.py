from supabase import create_client, create_async_client, AsyncClient
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import traceback
import json

# Load environment variables
load_dotenv()

# set up file logging
logging.basicConfig(filename='supabase_client.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    logger.error(f"Supabase configuration missing - URL: {'present' if supabase_url else 'missing'}, Key: {'present' if supabase_key else 'missing'}")

supabase = AsyncClient(supabase_url, supabase_key) if supabase_url and supabase_key else None

class TradeStatus:
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    CANCELLED = 'CANCELLED'

# Autocomplete functions (direct table access)
async def get_open_trades_for_autocomplete() -> List[Dict[str, Any]]:
    """Get all open trades directly from the trades table for autocomplete."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        # TODO: All status and types should be capitalized
        #response = await supabase.table('trades').select('*').eq('status', 'open').execute()
        response = await supabase.table('trades').select('*').in_('status', [TradeStatus.OPEN]).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting open trades for autocomplete: {str(e)}")
        return []

async def get_open_os_trades_for_autocomplete() -> List[Dict[str, Any]]:
    """Get all open options strategy trades directly from the table for autocomplete."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        response = await supabase.table('options_strategy_trades').select('*').eq('status', TradeStatus.OPEN).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting open options strategy trades for autocomplete: {str(e)}")
        return []

# Regular trade functions
async def create_trade(
    symbol: str,
    trade_type: str,
    entry_price: float,
    size: str,
    configuration_id: int,
    expiration_date: Optional[str] = None,
    strike: Optional[float] = None,
    is_contract: bool = False,
    is_day_trade: bool = False,
    option_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new trade using the Supabase edge function."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    input_data = {
        "symbol": symbol,
        "trade_type": trade_type,
        "entry_price": entry_price,
        "size": size,
        "configuration_id": configuration_id,
        "is_contract": is_contract,
        "is_day_trade": is_day_trade,
    }

    if expiration_date:
        input_data["expiration_date"] = expiration_date
    if strike:
        input_data["strike"] = strike
    if option_type:
        input_data["option_type"] = option_type

    logger.info(f"Calling trades edge function with action=createTrade and input={input_data}")
    try:
        response = await supabase.functions.invoke(
            "trades",
            invoke_options={"body": {"action": "createTrade", "input": input_data}}
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error creating trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Exception in create_trade edge function: {str(e)}")
        logger.error(f"Full exception: {traceback.format_exc()}")
        raise

async def add_to_trade(trade_id: str, price: float, size: str) -> Dict[str, Any]:
    """Add to an existing trade using the Supabase edge function."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    logger.info(f"Calling trades edge function with action=addToTrade, trade_id={trade_id}, price={price}, size={size}")
    try:
        response = await supabase.functions.invoke(
            "trades",
            invoke_options={"body": {"action": "addToTrade", "trade_id": trade_id, "price": price, "size": size}}
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error adding to trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Exception in add_to_trade edge function: {str(e)}")
        logger.error(f"Full exception: {traceback.format_exc()}")
        raise

async def trim_trade(trade_id: str, price: float, size: str) -> Dict[str, Any]:
    """Trim an existing trade using the Supabase edge function."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    logger.info(f"Calling trades edge function with action=trimTrade, trade_id={trade_id}, price={price}, size={size}")
    try:
        response = await supabase.functions.invoke(
            "trades",
            invoke_options={"body": {"action": "trimTrade", "trade_id": trade_id, "price": price, "size": size}}
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error trimming trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Exception in trim_trade edge function: {str(e)}")
        logger.error(f"Full exception: {traceback.format_exc()}")
        raise

async def exit_trade(trade_id: str, price: float) -> Dict[str, Any]:
    """Exit an existing trade using direct table access."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    logger.info(f"Calling trades edge function with action=exitTrade, trade_id={trade_id}, price={price}")
    try:
        response = await supabase.functions.invoke(
            "trades",
            invoke_options={"body": {"action": "exitTrade", "trade_id": trade_id, "price": price}}
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error exiting trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Exception in exit_trade edge function: {str(e)}")
        logger.error(f"Full exception: {traceback.format_exc()}")
        raise

async def get_trade(trade_id: str) -> Optional[Dict[str, Any]]:
    """Get a trade by ID using the Supabase edge function."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    logger.info(f"Calling trades edge function with action=getTrades, trade_id={trade_id}")
    try:
        response = await supabase.functions.invoke(
            "trades",
            invoke_options={"body": {"action": "getTrades", "filters": {"trade_id": trade_id}}}
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error getting trade: {response_json['error']}")

        return response_json[0] if response_json else None
    except Exception as e:
        logger.error(f"Exception in get_trade edge function: {str(e)}")
        logger.error(f"Full exception: {traceback.format_exc()}")
        raise

async def get_single_trade(trade_id: str) -> Optional[Dict[str, Any]]:
    """Get a single trade by ID using direct table access."""
    if not supabase:
        raise Exception("Supabase client not initialized")
    response = await supabase.table('trades').select('*').eq('trade_id', trade_id).execute()
    return response.data[0] if response.data else None

async def get_open_trades() -> List[Dict[str, Any]]:
    """Get all open trades using direct table query."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        response = await supabase.table('trades').select('*').eq('status', 'open').execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting open trades: {str(e)}")
        return []

# Options Strategy functions

async def get_os_trade(strategy_id: str) -> Optional[Dict[str, Any]]:
    """Get an options strategy trade by ID."""
    if not supabase:
        raise Exception("Supabase client not initialized")
    print(strategy_id)
    response = await supabase.table('options_strategy_trades').select('*').eq('strategy_id', strategy_id).execute()
    print(response)
    return response.data[0] if response.data else None

async def create_os_trade(
    strategy_name: str,
    underlying_symbol: str,
    net_cost: float,
    size: str,
    legs: List[Dict[str, Any]],
    trade_group: str,
    configuration_id: int,
) -> Optional[Dict[str, Any]]:
    """Create a new options strategy trade."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        # Serialize legs for database storage
        serialized_legs = []
        for leg in legs:
            serialized_legs.append({
                'symbol': leg['symbol'],
                'strike': leg['strike'],
                'expiration_date': leg['expiration_date'].isoformat() if leg['expiration_date'] else None,
                'option_type': leg['option_type'],
                'trade_type': leg['trade_type'],
                'multiplier': leg.get('multiplier', 1)
            })

        response = await supabase.functions.invoke(
            "options-strategies",
            invoke_options={
                "body": {
                    "action": "createOptionsStrategy",
                    "input": {
                        "name": strategy_name,
                        "underlying_symbol": underlying_symbol,
                        "legs": json.dumps(serialized_legs),
                        "net_cost": net_cost,
                        "size": size,
                        "trade_group": trade_group,
                        "configuration_id": configuration_id
                    }
                }
            }
        )
        
        if isinstance(response, bytes):
            response_data = json.loads(response.decode('utf-8'))
        else:
            response_data = response

        if response_data:
            logger.info(f"Created options strategy trade: {response_data}")
            return response_data
        return None

    except Exception as e:
        logger.error(f"Error creating options strategy trade: {str(e)}")
        raise

async def get_open_os_trades() -> List[Dict[str, Any]]:
    """Get all open options strategy trades."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        response = await supabase.functions.invoke(
            "options-strategies",
            invoke_options={"body": {"action": "getOSTrades", "filters": {"status": "OPEN"}}}
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error getting open OS trades: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Error getting open options strategy trades: {str(e)}")
        return []

async def add_to_os_trade(
    strategy_id: str,
    net_cost: float,
    size: str,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """Add to an existing options strategy trade."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        response = await supabase.functions.invoke(
            "options-strategies",
            invoke_options={
                "body": {
                    "action": "addToStrategy",
                    "strategy_id": strategy_id,
                    "net_cost": net_cost,
                    "size": size,
                    "note": note
                }
            }
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error adding to OS trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Error adding to options strategy trade: {str(e)}")
        raise

async def trim_os_trade(
    strategy_id: str,
    net_cost: float,
    size: str,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """Trim an existing options strategy trade."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        response = await supabase.functions.invoke(
            "options-strategies",
            invoke_options={
                "body": {
                    "action": "trimStrategy",
                    "strategy_id": strategy_id,
                    "net_cost": net_cost,
                    "size": size,
                    "note": note
                }
            }
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error trimming OS trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Error trimming options strategy trade: {str(e)}")
        raise

async def exit_os_trade(
    strategy_id: str,
    net_cost: float,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """Exit an existing options strategy trade."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        response = await supabase.functions.invoke(
            "options-strategies",
            invoke_options={
                "body": {
                    "action": "exitStrategy",
                    "strategy_id": strategy_id,
                    "net_cost": net_cost,
                    "note": note
                }
            }
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error exiting OS trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Error exiting options strategy trade: {str(e)}")
        raise

async def add_note_to_os_trade(
    strategy_id: str,
    note: str
) -> Dict[str, Any]:
    """Add a note to an options strategy trade."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        response = await supabase.functions.invoke(
            "options-strategies",
            invoke_options={
                "body": {
                    "action": "addNoteToStrategy",
                    "strategy_id": strategy_id,
                    "note": note
                }
            }
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error adding note to OS trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Error adding note to options strategy trade: {str(e)}")
        raise

async def reopen_trade(trade_id: str) -> Dict[str, Any]:
    """Reopen a closed trade."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    try:
        response = await supabase.functions.invoke(
            "trades",
            invoke_options={
                "body": {
                    "action": "reopenTrade",
                    "trade_id": trade_id
                }
            }
        )
        logger.info(f"Edge function raw response: {response}")
        
        # Decode bytes response to JSON
        if isinstance(response, bytes):
            response_json = json.loads(response.decode('utf-8'))
        else:
            response_json = response
            
        logger.info(f"Edge function decoded response: {response_json}")

        if response_json.get("error"):
            logger.error(f"Edge function error: {response_json['error']}")
            raise Exception(f"Error reopening trade: {response_json['error']}")

        return response_json
    except Exception as e:
        logger.error(f"Error reopening trade: {str(e)}")
        raise 

async def get_verification_config(message_id: str) -> Dict[str, Any]:
    """Get the verification config for a message."""
    if not supabase:
        raise Exception("Supabase client not initialized")

    return await supabase.table('verification_configs').select('*').eq('message_id', message_id).single()

async def get_verification_configs() -> list[dict]:
    """Get all verification configurations"""
    try:
        response = await supabase.table('verification_configs').select('*').execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting verification configs: {str(e)}")
        return []

async def add_verification_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new verification config."""
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    # Convert SQLAlchemy model to dict if needed
    config_data = config.to_dict() if hasattr(config, 'to_dict') else config
    return await supabase.table('verification_configs').insert(config_data).execute()

async def add_verification(verification: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new verification."""
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    # Convert SQLAlchemy model to dict if needed
    verification_data = verification.to_dict() if hasattr(verification, 'to_dict') else verification
    return await supabase.table('verifications').insert(verification_data).execute()

async def get_trade_by_id(trade_id: str) -> Dict[str, Any]:
    """Get a trade by ID."""
    if not supabase:
        raise Exception("Supabase client not initialized")
    return await supabase.table('trades').select('*').eq('trade_id', trade_id).single()