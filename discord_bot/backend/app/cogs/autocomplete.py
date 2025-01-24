import discord
from discord.ext import commands
import logging
from datetime import datetime
import json
from discord import app_commands

from ..supabase_client import (
    get_open_trades_for_autocomplete,
    get_open_os_trades_for_autocomplete,
    supabase
)

logger = logging.getLogger(__name__)

class AutocompleteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def get_open_trade_ids(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Get open trades for autocomplete."""
        try:
            # Get open trades directly from the database
            trades = await get_open_trades_for_autocomplete()
            if not trades:
                return []
            
            # Format trade information
            trade_info = []
            for trade in trades:
                symbol = trade['symbol']
                strike = trade.get('strike')
                if trade.get('expiration_date'):
                    exp_date = datetime.strptime(trade.get('expiration_date').split('T')[0], '%Y-%m-%d')
                    current_year = datetime.now().year
                    if exp_date.year == current_year:
                        expiration = exp_date.strftime('%m/%d')
                    else:
                        expiration = exp_date.strftime('%m/%d/%y')
                else:
                    expiration = None
                
                if strike is not None and expiration:
                    strike_display = f"${float(strike):,.2f}" if float(strike) >= 0 else f"(${abs(float(strike)):,.2f})"
                    display = f"{symbol} {strike_display} {expiration}"
                    sort_key = (symbol, expiration, float(strike))
                else:
                    display = f"{symbol} COMMON"
                    sort_key = (symbol, "9999-12-31", 0)  # Put non-option trades at the bottom of their symbol group
                
                trade_info.append((trade['trade_id'], display, sort_key))
            
            # Sort the trades
            sorted_trades = sorted(trade_info, key=lambda x: x[2])
            
            # Create OptionChoice objects
            return [
                app_commands.Choice(name=f"{display} (ID: {trade_id})", value=str(trade_id))
                for trade_id, display, _ in sorted_trades if current.lower() in str(trade_id).lower()
            ][:25]
        except Exception as e:
            logger.error(f"Error in get_open_trade_ids: {str(e)}")
            return []

    @staticmethod
    async def get_open_os_trade_ids(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Get open options strategy trades for autocomplete."""
        try:
            # Get open trades directly from the database
            trades = await get_open_os_trades_for_autocomplete()
            if not trades:
                return []
            
            # Format trade information
            trade_info = []
            for trade in trades:
                symbol = trade['underlying_symbol']
                name = trade['name']
                expiration_date = None
                
                # Parse legs to find latest expiration
                legs = json.loads(trade['legs']) if trade.get('legs') else []
                for leg in legs:
                    leg_expiration = leg.get('expiration_date')
                    if leg_expiration:
                        leg_date = datetime.fromisoformat(leg_expiration)
                        if not expiration_date or leg_date > expiration_date:
                            expiration_date = leg_date
                
                if expiration_date:
                    display = f"{symbol} {expiration_date.strftime('%m/%d/%y')} @ {float(trade['average_net_cost']):.2f} - {name}"
                    sort_key = (symbol, expiration_date, name)
                else:
                    display = f"{symbol} @ {float(trade['average_net_cost']):.2f} - {name}"
                    sort_key = (symbol, datetime.max, name)
                
                trade_info.append((trade['trade_id'], display, sort_key))
            
            # Sort the trades
            sorted_trades = sorted(trade_info, key=lambda x: x[2])
            
            # Create OptionChoice objects
            return [
                app_commands.Choice(name=f"{display} (ID: {trade_id})", value=str(trade_id))
                for trade_id, display, _ in sorted_trades if current.lower() in str(trade_id).lower()
            ][:25]
        except Exception as e:
            logger.error(f"Error in get_open_os_trade_ids: {str(e)}")
            return []

    @staticmethod
    async def get_trade_groups(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Get available trade groups for autocomplete."""
        try:
            # Get trade groups from Supabase
            response = await supabase.table('trade_configurations').select('name').execute()
            if response.data:
                return [
                    app_commands.Choice(name=config['name'].replace('_', ' ').title(), value=config['name'])
                    for config in response.data if current.lower() in config['name'].lower()
                ][:25]
        except Exception as e:
            logger.error(f"Error getting trade groups: {str(e)}")
        
        # Return default trade groups if Supabase query fails
        groups = ["DAY_TRADER", "LONG_TERM_TRADER", "SWING_TRADER"]  # Add your actual groups
        return [
            app_commands.Choice(name=group, value=group)
            for group in groups if current.lower() in group.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(AutocompleteCog(bot)) 