# type: ignore[type-arg]

import discord
from discord.ext import commands
import logging
from datetime import datetime, date
from typing import Dict, Any
import os
import re
import traceback

from ..supabase_client import (
    create_trade, add_to_trade, trim_trade, exit_trade,
    get_trade_by_id, get_open_trades_for_autocomplete, get_single_trade
)

logger = logging.getLogger(__name__)

# Toggle to control whether size is displayed in Discord embeds
DISPLAY_SIZE_IN_EMBEDS = False

class TradeGroupEnum:
    DAY_TRADER = "day_trader"
    SWING_TRADER = "swing_trader"
    LONG_TERM_TRADER = "long_term_trader"



'''
async def get_trade_groups(ctx: discord.AutocompleteContext) -> list[discord.OptionChoice]:
        """Get available trade groups for autocomplete."""
        try:
            # Get trade groups from Supabase
            response = await supabase.table('trade_configurations').select('name').execute()
            if response.data:
                return [
                    discord.OptionChoice(name=config['name'].replace('_', ' ').title(), value=config['name'])
                    for config in response.data if current.lower() in config['name'].lower()
                ][:25]
        except Exception as e:
            logger.error(f"Error getting trade groups: {str(e)}")
        
        # Return default trade groups if Supabase query fails
        groups = ["DAY_TRADER", "LONG_TERM_TRADER", "SWING_TRADER"]  # Add your actual groups
        return [
            discord.OptionChoice(name=group, value=group)
            for group in groups if current.lower() in group.lower()
        ][:25]
'''


async def get_open_trade_ids(
    ctx: discord.AutocompleteContext,
) -> list[discord.OptionChoice]:
    """Get open trades for autocomplete."""
    try:
        trades = await get_open_trades_for_autocomplete()
        if not trades:
            return []
        
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
                sort_key = (symbol, "9999-12-31", 0)
            
            trade_info.append((trade['trade_id'], display, sort_key))
        
        sorted_trades = sorted(trade_info, key=lambda x: x[2])
        return [
            discord.OptionChoice(name=f"{display} (ID: {trade_id})", value=trade_id)
            for trade_id, display, _ in sorted_trades
        ][:25]
    except Exception as e:
        logger.error(f"Error in get_open_trade_ids: {str(e)}")
        return []

class TradingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_utility_cog(self):
        return self.bot.get_cog('UtilityCog')

    async def get_logging_cog(self):
        return self.bot.get_cog('LoggingCog')

    async def kill_interaction(self, ctx):
        await ctx.response.send_message("Processing...", ephemeral=True, delete_after=0)

    async def create_trade_oneliner(self, trade: Dict[str, Any], price: float = 0, size: float = 0) -> str:
        """Create a one-liner summary of the trade."""
        if trade.get('option_type'):
            if trade['option_type'].startswith("C"):
                option_type = "CALL"
            elif trade['option_type'].startswith("P"):
                option_type = "PUT"   
            else:
                option_type = trade['option_type']
        else:
            option_type = ""

        if size == 0:
            size = trade.get('current_size', None) if trade.get('current_size') else trade.get('size', None)
        if price == 0:
            price = trade.get('average_price', None)
        display_price = f"${price:.2f}"
        
        if trade.get('is_contract'):
            utility_cog = await self.get_utility_cog()
            expiration = utility_cog.convert_to_two_digit_year(trade.get('expiration_date')) if trade.get('expiration_date') else "No Exp"
            strike = f"${trade.get('strike'):.2f}"
            if DISPLAY_SIZE_IN_EMBEDS:
                return f"### {expiration} {trade.get('symbol')} {strike} {option_type} @ {display_price} {size} risk"
            else:
                return f"### {expiration} {trade.get('symbol')} {strike} {option_type} @ {display_price}"
        else:
            if DISPLAY_SIZE_IN_EMBEDS:
                return f"### {trade.get('symbol')} @ {display_price} {size} risk"
            else:
                return f"### {trade.get('symbol')} @ {display_price}"

    async def create_transaction_oneliner(self, trade: Dict[str, Any], type: str, size: float, price: float) -> str:
        """Create a one-line summary of a transaction."""
        if trade.get('option_type'):
            if trade['option_type'].startswith("C"):
                option_type = "CALL"
            elif trade['option_type'].startswith("P"):
                option_type = "PUT"   
            else:
                option_type = trade['option_type']
        else:
            option_type = ""

        risk_identifier = "risk" if type == "ADD" else "size"

        if trade.get('is_contract'):
            utility_cog = await self.get_utility_cog()
            expiration = utility_cog.convert_to_two_digit_year(trade.get('expiration_date')) if trade.get('expiration_date') else "No Exp"
            strike = f"{trade.get('strike'):.2f}"
            if DISPLAY_SIZE_IN_EMBEDS:
                return f"### {type} {expiration} {trade.get('symbol')} {strike} {option_type} @ {price:.2f} {size} {risk_identifier}"
            else:
                return f"### {type} {expiration} {trade.get('symbol')} {strike} {option_type} @ {price:.2f}"
        else:
            if DISPLAY_SIZE_IN_EMBEDS:
                return f"### {type} {trade.get('symbol')} @ {price:.2f} {size} {risk_identifier}"
            else:
                return f"### {type} {trade.get('symbol')} @ {price:.2f}"

    @commands.slash_command(name="open", description="Open a trade from a symbol string")
    async def open_trade(
        self,
        ctx: discord.ApplicationContext,
        trade_string: discord.Option(str, description="The trade string to parse"),
        price: discord.Option(float, description="The price of the trade"),
        note: discord.Option(str, description="Optional note from the trader") = None,
        size: discord.Option(str, description="The size of the trade default is 1") = "1",
    ):
        """Open a new trade."""
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        utility_cog = await self.get_utility_cog()
        logging_cog = await self.get_logging_cog()
        try:
            # Parse the trade string
            parsed = utility_cog.parse_option_symbol(trade_string)
            if not parsed:
                await logging_cog.log_to_channel(ctx.guild, f"Invalid trade string format by {ctx.user.name}: {trade_string}")
                return

            # Determine trade group
            trade_group = await utility_cog.determine_trade_group(
                parsed['expiration_date'].strftime("%m/%d/%y"), 
                parsed['trade_type'], 
                parsed['symbol']
            )

            # Get configuration for trade group
            config = await utility_cog.get_configuration(trade_group)
            if not config:
                await logging_cog.log_to_channel(ctx.guild, f"No configuration found for trade group {trade_group} by {ctx.user.name}")
                return

            # Create trade using Supabase edge function
            trade_data = await create_trade(
                symbol=parsed['symbol'],
                trade_type=parsed['trade_type'],
                entry_price=price,
                size=size,
                configuration_id=config['id'],
                expiration_date=parsed['expiration_date'].strftime("%m/%d/%y"),
                strike=parsed['strike'],
                is_contract=True,
                is_day_trade=(trade_group == TradeGroupEnum.DAY_TRADER),
                option_type=parsed['option_type']
            )

            if trade_data:
                # Create and send embed
                embed = discord.Embed(title="New Trade Opened", color=discord.Color.green())
                embed.description = await self.create_trade_oneliner(trade_data, price, size)
                embed.add_field(name="Symbol", value=parsed['symbol'], inline=True)
                embed.add_field(name="Type", value=parsed['trade_type'], inline=True)
                embed.add_field(name="Entry Price", value=f"${price:,.2f}", inline=True)
                if DISPLAY_SIZE_IN_EMBEDS:
                    embed.add_field(name="Risk Level (1-6)", value=size, inline=True)
                embed.add_field(name="Expiration", value=parsed['expiration_date'].strftime("%m/%d/%y"), inline=True)
                embed.add_field(name="Strike", value=f"${parsed['strike']:,.2f}", inline=True)
                embed.add_field(name="Option Type", value="CALL" if parsed['option_type'] == "C" else "PUT", inline=True)
                if trade_group == TradeGroupEnum.DAY_TRADER:
                    embed.add_field(name="Disclaimer", value="This is a day trade. Set a 50% sell at 100% profit to lock in a no risk situation.", inline=True)
                else:
                    embed.add_field(name="Disclaimer", value="Swing Trades & Long Term Trades are less volatile, Blue Deer will mention and size up if it is a CORE Position", inline=True)
                embed.set_footer(text=f"Trade ID: {trade_data['trade_id']}")
                if note:
                    embed.add_field(name="Note", value=note, inline=False)

                await utility_cog.send_embed_by_configuration_id(ctx, config['id'], embed)
                await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed OPEN command: Trade has been opened successfully.")

            else:
                await logging_cog.log_to_channel(ctx.guild, f"Error in open_trade command, trade data returned: {trade_data}")

        except Exception as e:
            logger.error(f"Error in open_trade command: {str(e)}")
            logger.error(traceback.format_exc())
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in OPEN command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="fut", description="Buy to open a new futures trade")
    async def future_trade(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, description="The symbol of the security"),
        entry_price: discord.Option(float, description="The price at which the trade was opened"),
        note: discord.Option(str, description="Optional note from the trader") = None,
        size: discord.Option(str, description="The size of the trade") = "1",
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        await self.common_stock_trade(ctx, TradeGroupEnum.DAY_TRADER, symbol, entry_price, size, note)

    @commands.slash_command(name="lt", description="Buy to open a new long-term trade")
    async def lt_trade(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, description="The symbol of the security"),
        entry_price: discord.Option(float, description="The price at which the trade was opened"),
        note: discord.Option(str, description="Optional note from the trader") = None,
        size: discord.Option(str, description="The size of the trade") = "1",
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        await self.common_stock_trade(ctx, TradeGroupEnum.LONG_TERM_TRADER, symbol, entry_price, size, note)

    async def common_stock_trade(
        self,
        ctx: discord.ApplicationContext,
        trade_group: str,
        symbol: str,
        entry_price: float,
        size: str,
        note: str = None,
    ):
        try:
            utility_cog = await self.get_utility_cog()
            logging_cog = await self.get_logging_cog()

            # Get configuration for trade group
            config = await utility_cog.get_configuration(trade_group)
            if not config:
                await logging_cog.log_to_channel(ctx.guild, f"No configuration found for trade group {trade_group} by {ctx.user.name}")
                return

            # Create trade using Supabase edge function
            trade_data = await create_trade(
                symbol=symbol,
                trade_type="BTO",
                entry_price=entry_price,
                size=size,
                configuration_id=config['id'],
                is_day_trade=(trade_group == TradeGroupEnum.DAY_TRADER)
            )

            if trade_data:
                # Create and send embed
                embed = discord.Embed(title="New Trade Opened", color=discord.Color.green())
                embed.description = await self.create_trade_oneliner(trade_data, entry_price, size)
                embed.add_field(name="Symbol", value=symbol, inline=True)
                embed.add_field(name="Type", value="BTO", inline=True)
                embed.add_field(name="Entry Price", value=f"${entry_price:,.2f}", inline=True)
                if DISPLAY_SIZE_IN_EMBEDS:
                    embed.add_field(name="Risk Level (1-6)", value=size, inline=True)
                embed.set_footer(text=f"Trade ID: {trade_data['trade_id']}")
                
                note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None

                await utility_cog.send_embed_by_configuration_id(ctx, config['id'], embed, note_embed)
                await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed {trade_group.upper()} command: Trade has been opened successfully.")

            else:
                await logging_cog.log_to_channel(ctx.guild, f"Error in {trade_group} command, trade data returned: {trade_data}")

        except Exception as e:
            logger.error(f"Error in {trade_group} command: {str(e)}")
            logger.error(traceback.format_exc())
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in {trade_group.upper()} command by {ctx.user.name}: {str(e)}")




    @commands.slash_command(name="add", description="Add to an existing trade")
    async def add_action(
        self,
        ctx: discord.ApplicationContext,
        trade_id: discord.Option(str, description="The ID of the trade to add to", autocomplete=discord.utils.basic_autocomplete(get_open_trade_ids)),
        price: discord.Option(float, description="The price of the trade"),
        note: discord.Option(str, description="Optional note from the trader") = None,
        size: discord.Option(str, description="The size to add default is 1") = "1",
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        logging_cog = await self.get_logging_cog()
        utility_cog = await self.get_utility_cog()
        try:
            trade_data = await add_to_trade(trade_id, price, size)

            # Create an embed with the updated trade information
            embed = discord.Embed(title="Added to Trade", color=discord.Color.blue())
            embed.description = await self.create_transaction_oneliner(trade_data, "ADD", size, price)
            if DISPLAY_SIZE_IN_EMBEDS:
                embed.add_field(name="New Total Size", value=trade_data.get('current_size', None), inline=True)
            embed.add_field(name="New Average Price", value=f"${trade_data.get('average_price', None):.2f}", inline=True)
            if trade_data.get('is_day_trade'):
                embed.add_field(name="Disclaimer", value="NEW AVERAGE PRICE! Update your 50% sell at 100% profit to lock in a no risk situation.", inline=True)
            embed.set_footer(text=f"Trade ID: {trade_data.get('trade_id', None)}")
            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None

            await utility_cog.send_embed_by_configuration_id(ctx, trade_data['configuration_id'], embed, note_embed)
            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed ADD command: Added to trade {trade_id} successfully.")

        except Exception as e:
            logger.error(f"Error in add_action command: {str(e)}")
            logger.error(traceback.format_exc())
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in ADD command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="trim", description="Trim an existing trade")
    async def trim_action(
        self,
        ctx: discord.ApplicationContext,
        trade_id: discord.Option(str, description="The ID of the trade to trim", autocomplete=discord.utils.basic_autocomplete(get_open_trade_ids)),
        price: discord.Option(float, description="The price of the trade"),
        note: discord.Option(str, description="Optional note from the trader") = None,
        size: discord.Option(str, description="The size to trim default is 0.25") = "0.25",
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)

        try:
            logging_cog = await self.get_logging_cog()
            utility_cog = await self.get_utility_cog()
            trade_data = await get_single_trade(trade_id)
            if float(trade_data.get("current_size", 0.01)) - float(size) <= 0:
                size = float(trade_data.get("current_size", 0.01)) / 2
            trade_data = await trim_trade(trade_id, price, size)

            # Calculate percentage change
            entry_price = trade_data.get('average_price', 0)
            exit_price = trade_data.get('average_exit_price', price)
            
            if entry_price and entry_price > 0:
                percent_change = ((exit_price - entry_price) / entry_price) * 100
                change_sign = "+" if percent_change >= 0 else ""
            
                if trade_data.get("trade_type") == "STO":
                    percent_change = -percent_change
                    change_sign = "+" if percent_change >= 0 else ""

            # Create an embed with the updated trade information
            embed = discord.Embed(title="Trimmed Trade", color=discord.Color.yellow())
            embed.description = await self.create_transaction_oneliner(trade_data, "TRIM", size, price)
            if DISPLAY_SIZE_IN_EMBEDS:
                embed.add_field(name="Size Remaining", value=trade_data.get('current_size', None), inline=True)
            embed.add_field(name="Percent Change", value=f"{change_sign}{percent_change:.2f}%", inline=True)
            embed.set_footer(text=f"Trade ID: {trade_data.get('trade_id', None)}")

            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None
            await utility_cog.send_embed_by_configuration_id(ctx, trade_data['configuration_id'], embed, note_embed)

            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed TRIM command: Trimmed trade {trade_id} successfully.")

        except Exception as e:
            logger.error(f"Error in trim_action command: {str(e)}")
            logger.error(traceback.format_exc())
            await ctx.followup.send(f"Error trimming trade: {str(e)}", ephemeral=True)
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in TRIM command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="exit", description="Exit an existing trade")
    async def exit_action(
        self,
        ctx: discord.ApplicationContext,
        trade_id: discord.Option(str, description="The ID of the trade to exit", autocomplete=discord.utils.basic_autocomplete(get_open_trade_ids)),
        price: discord.Option(float, description="The price of the trade"),
        note: discord.Option(str, description="Optional note from the trader") = None,
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)

        logging_cog = await self.get_logging_cog()
        utility_cog = await self.get_utility_cog()
        try:
            trade_data = await exit_trade(trade_id, price)

            # Create an embed with the closed trade information
            embed = discord.Embed(title="Trade Closed", color=discord.Color.gold())
            embed.description = await self.create_transaction_oneliner(trade_data, "EXIT", trade_data.get('exit_size', -1), price)

            unit_type = "contract" if trade_data.get('is_contract', False) else "share"
            unit_profit_loss = trade_data.get('unit_profit_loss', 0) * 100 if unit_type == "contract" else trade_data.get('unit_profit_loss', 0)

            # Calculate percentage change
            entry_price = trade_data.get('average_price', 0)
            exit_price = trade_data.get('average_exit_price', price)
            
            if entry_price and entry_price > 0:
                percent_change = ((exit_price - entry_price) / entry_price) * 100
                change_sign = "+" if percent_change >= 0 else ""
                if trade_data.get("trade_type") == "STO":
                    percent_change = -percent_change
                    change_sign = "+" if percent_change >= 0 else ""
                    unit_profit_loss = -unit_profit_loss

                embed.add_field(name="Percent Change", value=f"{change_sign}{percent_change:.2f}%", inline=True)


            embed.add_field(name=f"Trade P/L per {unit_type}", value=f"${unit_profit_loss:.2f}", inline=True)
            embed.add_field(name="Avg Entry Price", value=f"${trade_data.get('average_price', None):.2f}", inline=True)
            embed.add_field(name="Avg Exit Price", value=f"${trade_data.get('average_exit_price', price):.2f}", inline=True)
            embed.set_footer(text=f"Trade ID: {trade_data.get('trade_id', None)}")
            
            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None
            await utility_cog.send_embed_by_configuration_id(ctx, trade_data['configuration_id'], embed, note_embed)

            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed EXIT command: Exited trade {trade_id} successfully.")

        except Exception as e:
            logger.error(f"Error in exit_action command: {str(e)}")
            logger.error(traceback.format_exc())
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in EXIT command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="note", description="Add a note to an existing trade")
    async def note_action(
        self,
        ctx: discord.ApplicationContext,
        trade_id: discord.Option(str, description="The ID of the trade to add the note to", autocomplete=discord.utils.basic_autocomplete(get_open_trade_ids)),
        note: discord.Option(str, description="The note to add")
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        logging_cog = await self.get_logging_cog()
        utility_cog = await self.get_utility_cog()
        try:
            trade_data = await get_single_trade(trade_id)
            if not trade_data:
                await logging_cog.log_to_channel(ctx.guild, f"Trade {trade_id} not found by {ctx.user.name}")
                return

            embed = discord.Embed(title="Trade Note", color=discord.Color.blue())
            embed.description = f"{await self.create_trade_oneliner(trade_data, trade_data['average_price'], trade_data['size'])}"
            embed.add_field(name="Note", value=note, inline=False)
            embed.set_footer(text=f"Trade ID: {trade_data['trade_id']}")

            await utility_cog.send_embed_by_configuration_id(ctx, trade_data['configuration_id'], embed)
            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed NOTE command: Note added to trade {trade_id}.")

        except Exception as e:
            logger.error(f"Error in note_action command: {str(e)}")
            logger.error(traceback.format_exc())
            await logging_cog.log_to_channel(ctx.guild, f"Error in NOTE command by {ctx.user.name}: {str(e)}")







def setup(bot):
    bot.add_cog(TradingCog(bot)) 