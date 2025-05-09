# type: ignore[type-arg]
import discord
from discord.ext import commands
import logging
import traceback
import json
from datetime import datetime

from ..supabase_client import (
    create_os_trade,
    add_to_os_trade,
    trim_os_trade,
    exit_os_trade,
    add_note_to_os_trade,
    get_open_os_trades_for_autocomplete,
    get_os_trade
)

logger = logging.getLogger(__name__)

# Toggle to control whether size is displayed in Discord embeds
DISPLAY_SIZE_IN_EMBEDS = False

async def get_open_os_trade_ids(ctx: discord.AutocompleteContext) -> list[discord.OptionChoice]:
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
            
            trade_info.append((trade['strategy_id'], display, sort_key))
        
        # Sort the trades
        sorted_trades = sorted(trade_info, key=lambda x: x[2])
        
        return [discord.OptionChoice(name=f"{display} (ID: {strategy_id})", value=strategy_id) for strategy_id, display, _ in sorted_trades]
    except Exception as e:
        logger.error(f"Error in get_open_os_trade_ids: {str(e)}")
        return []

class OptionsStrategyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_utility_cog(self):
        return self.bot.get_cog('UtilityCog')

    async def get_logging_cog(self):
        return self.bot.get_cog('LoggingCog')

    def split_option_legs(self, leg_string: str) -> list[str]:
        # First leg is implicitly positive if no sign
        if not leg_string.startswith('+') and not leg_string.startswith('-'):
            leg_string = '+' + leg_string
        
        # Split the string by + or - while keeping the signs
        legs = []
        current_leg = ''
        
        for char in leg_string:
            if char in ['+', '-'] and current_leg:
                legs.append(current_leg)
                current_leg = char
            else:
                current_leg += char
        
        # Add the last leg
        if current_leg:
            legs.append(current_leg)
            
        return legs

    @commands.slash_command(name="os", description="Open a new options strategy trade")
    async def os_trade(
        self,
        ctx: discord.ApplicationContext,
        strategy_name: discord.Option(str, description="The name of the strategy (e.g., 'Iron Condor', 'Call Spread')"),
        net_cost: discord.Option(float, description="The net cost of the strategy"),
        legs: discord.Option(str, description="The legs of the strategy in format: 'SPY240119C510,SPY240119P500,...'"),
        note: discord.Option(str, description="Optional note from the trader") = None,
        size: discord.Option(str, description="The size of the strategy default is 1") = "1",
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        utility_cog = await self.get_utility_cog()
        logging_cog = await self.get_logging_cog()

        try:
            # Parse legs
            leg_list = []
            underlying_symbol = None

            for leg in self.split_option_legs(legs):
                parsed = utility_cog.parse_option_symbol(leg.strip())
                if not parsed:
                    await logging_cog.log_to_channel(ctx.guild, f"Invalid option symbol format: {leg} by {ctx.user.name}")
                    return
                leg_list.append(parsed)
                if not underlying_symbol:
                    underlying_symbol = parsed['symbol']
                elif underlying_symbol != parsed['symbol']:
                    await logging_cog.log_to_channel(ctx.guild, f"All legs must have the same underlying symbol by {ctx.user.name}")
                    return

            # Determine trade group
            trade_group = await utility_cog.determine_trade_group(
                leg_list[0]['expiration_date'].strftime("%m/%d/%y"),
                "BTO",  # Default to BTO for options strategies
                leg_list[0]['symbol']
            )

            # Get configuration for trade group
            config = await utility_cog.get_configuration(trade_group)
            if not config:
                await logging_cog.log_to_channel(ctx.guild, f"No configuration found for trade group {trade_group} by {ctx.user.name}")
                return

            # Create trade using Supabase edge function
            trade_data = await create_os_trade(
                strategy_name=strategy_name,
                underlying_symbol=leg_list[0]['symbol'],
                net_cost=net_cost,
                size=size,
                legs=leg_list,
                configuration_id=config['id'],
                trade_group=trade_group
            )

            if trade_data:
                # Create and send embed
                embed = discord.Embed(title="New Options Strategy Created", color=discord.Color.green())
                embed.description = f"### {strategy_name}\n{self.create_trade_oneliner_os(trade_data, utility_cog)}"
                embed.add_field(name="Symbol", value=leg_list[0]['symbol'], inline=True)
                embed.add_field(name="Entry Cost", value=f"${net_cost:,.2f}", inline=True)
                if DISPLAY_SIZE_IN_EMBEDS:
                    embed.add_field(name="Size", value=size, inline=True)

                embed.set_footer(text=f"Strategy ID: {trade_data['strategy_id']}")
                
                # Add leg details
                for i, leg in enumerate(leg_list, 1):
                    leg_str = (
                        f"{leg['trade_type']} {leg['symbol']} ${leg['strike']:,.2f} "
                        f"{leg['expiration_date'].strftime('%m/%d/%y')} {leg['option_type']}"
                    )
                    embed.add_field(name=f"Leg {i}", value=leg_str, inline=False)

                note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None
                await utility_cog.send_embed_by_configuration_id(ctx, config['id'], embed, note_embed)
                await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed OS command: Options strategy has been opened successfully.")

        except ValueError as e:
            await logging_cog.log_to_channel(ctx.guild, f"Error parsing option symbols: {str(e)} by {ctx.user.name}")
        except Exception as e:
            logger.error(f"Error in os_trade command: {str(e)}")
            logger.error(traceback.format_exc())
            await logging_cog.log_to_channel(ctx.guild, f"Error in OS command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="os_add", description="Add to an existing options strategy trade")
    async def os_add(
        self,
        ctx: discord.ApplicationContext,
        strategy_id: discord.Option(str, description="The ID of the options strategy trade to add to", autocomplete=discord.utils.basic_autocomplete(get_open_os_trade_ids)),
        net_cost: discord.Option(float, description="The net cost of the addition"),
        note: discord.Option(str, description="Optional note from the trader") = None,
        size: discord.Option(str, description="The size to add default is 1") = "1",
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        logging_cog = await self.get_logging_cog()
        utility_cog = await self.get_utility_cog()

        try:

            # Add to trade using Supabase function
            updated_trade = await add_to_os_trade(strategy_id, net_cost, size, note)
            if not updated_trade:
                await logging_cog.log_to_channel(ctx.guild, f"Trade {strategy_id} not found by {ctx.user.name}")
                return

            # Create embed
            embed = discord.Embed(title="Added to Options Strategy", color=discord.Color.blue())
            embed.description = f"### {updated_trade['name']}\n{self.create_trade_oneliner_os(updated_trade, utility_cog)}"

            embed.add_field(name="Add Price", value=f"${net_cost:.2f}", inline=True)
            if DISPLAY_SIZE_IN_EMBEDS:
                embed.add_field(name="Added Size", value=utility_cog.format_size(size), inline=True)
                embed.add_field(name="New Size", value=utility_cog.format_size(updated_trade['current_size']), inline=True)
            embed.add_field(name="New Avg Entry", value=f"${float(updated_trade['average_net_cost']):.2f}", inline=True)
            if note:
                embed.add_field(name="Note", value=note, inline=False)
            embed.set_footer(text=f"Strategy ID: {strategy_id}")    

            await utility_cog.send_embed_by_configuration_id(ctx, updated_trade['configuration_id'], embed)
            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed OS_ADD command: Added to options strategy {strategy_id} successfully.")

        except Exception as e:
            logger.error(f"Error adding to options strategy trade: {str(e)}")
            logger.error(traceback.format_exc())
            await ctx.followup.send(f"Error adding to options strategy: {str(e)}", ephemeral=True)
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in OS_ADD command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="os_trim", description="Trim an existing options strategy trade")
    async def os_trim(
        self,
        ctx: discord.ApplicationContext,
        strategy_id: discord.Option(str, description="The ID of the options strategy trade to trim", autocomplete=discord.utils.basic_autocomplete(get_open_os_trade_ids)),
        net_cost: discord.Option(float, description="The net cost of the trim"),
        note: discord.Option(str, description="Optional note from the trader") = None,
        size: discord.Option(str, description="The size to trim default is 0.25") = "0.25",
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        logging_cog = await self.get_logging_cog()
        utility_cog = await self.get_utility_cog()
        try:
            # Trim trade using Supabase function
            updated_trade = await trim_os_trade(strategy_id, net_cost, size, note)
            if not updated_trade:
                await logging_cog.log_to_channel(ctx.guild, f"Trade {strategy_id} not found by {ctx.user.name}")
                return

            # Create embed
            embed = discord.Embed(title="Trimmed Options Strategy", color=discord.Color.yellow())
            embed.description = f"### {updated_trade['name']}\n{self.create_trade_oneliner_os(updated_trade, utility_cog)}"
            embed.add_field(name="Trim Price", value=f"${net_cost:.2f}", inline=True)
            if DISPLAY_SIZE_IN_EMBEDS:
                embed.add_field(name="Trimmed Size", value=utility_cog.format_size(size), inline=True)
                embed.add_field(name="New Size", value=utility_cog.format_size(updated_trade['current_size']), inline=True)
            embed.add_field(name="Avg Entry Cost", value=f"${float(updated_trade['average_net_cost']):.2f}", inline=True)
            
            embed.set_footer(text=f"Strategy ID: {strategy_id}")

            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None
            await utility_cog.send_embed_by_configuration_id(ctx, updated_trade['configuration_id'], embed, note_embed)
            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed OS_TRIM command: Trimmed options strategy {strategy_id} successfully.")

        except Exception as e:
            logger.error(f"Error trimming options strategy trade: {str(e)}")
            logger.error(traceback.format_exc())
            await logging_cog.log_to_channel(ctx.guild, f"Error in OS_TRIM command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="os_exit", description="Exit an existing options strategy trade")
    async def os_exit(
        self,
        ctx: discord.ApplicationContext,
        strategy_id: discord.Option(str, description="The ID of the options strategy trade to exit", autocomplete=discord.utils.basic_autocomplete(get_open_os_trade_ids)),
        net_cost: discord.Option(float, description="The net cost of the exit"),
        note: discord.Option(str, description="Optional note from the trader") = None,
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        logging_cog = await self.get_logging_cog()
        utility_cog = await self.get_utility_cog()

        try:
            # Exit trade using Supabase function
            updated_trade = await exit_os_trade(strategy_id, net_cost, note)
            if not updated_trade:
                await logging_cog.log_to_channel(ctx.guild, f"Trade {strategy_id} not found by {ctx.user.name}")
                return

            # Calculate P/L
            avg_entry_cost = float(updated_trade['average_net_cost'])
            avg_exit_cost = float(updated_trade['average_exit_cost'])
            pl_per_contract = avg_exit_cost - avg_entry_cost

            # Calculate percentage change
            if avg_entry_cost and avg_entry_cost != 0:
                percent_change = ((avg_exit_cost - avg_entry_cost) / abs(avg_entry_cost)) * 100
                change_sign = "+" if percent_change >= 0 else ""
            else:
                percent_change = 0
                change_sign = ""

            # Create embed
            embed = discord.Embed(title="Exited Options Strategy", color=discord.Color.red())
            embed.description = f"### {updated_trade['name']}\n{self.create_trade_oneliner_os(updated_trade, utility_cog)}"
            embed.add_field(name="Exit Price", value=f"${net_cost:.2f}", inline=True)
            if DISPLAY_SIZE_IN_EMBEDS:
                embed.add_field(name="Exited Size", value=updated_trade['current_size'], inline=True)
            embed.add_field(name="Percent Change", value=f"{change_sign}{percent_change:.2f}%", inline=True)
            embed.add_field(name="Avg Entry Cost", value=f"${avg_entry_cost:.2f}", inline=True)
            embed.add_field(name="Avg Exit Price", value=f"${avg_exit_cost:.2f}", inline=True)
            embed.add_field(name="P/L per Contract", value=f"${pl_per_contract:.2f}", inline=True)
            embed.set_footer(text=f"Strategy ID: {strategy_id}")

            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None
            await utility_cog.send_embed_by_configuration_id(ctx, updated_trade['configuration_id'], embed, note_embed)
            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed OS_EXIT command: Exited options strategy {strategy_id} successfully.")

        except Exception as e:
            logger.error(f"Error exiting options strategy trade: {str(e)}")
            logger.error(traceback.format_exc())
            await logging_cog.log_to_channel(ctx.guild, f"Error in OS_EXIT command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="os_note", description="Add a note to an options strategy trade")
    async def os_note(
        self,
        ctx: discord.ApplicationContext,
        strategy_id: discord.Option(str, description="The strategy to add the note to", autocomplete=discord.utils.basic_autocomplete(get_open_os_trade_ids)),
        note: discord.Option(str, description="The note to add")
    ):
        await ctx.respond("Processing...", ephemeral=True, delete_after=0)
        logging_cog = await self.get_logging_cog()
        utility_cog = await self.get_utility_cog()
        try:
            # Add note using Supabase function
            trade_data = await get_os_trade(strategy_id)
            if not trade_data:
                await logging_cog.log_to_channel(ctx.guild, f"Trade {strategy_id} not found by {ctx.user.name}")
                return

            # Create embed
            embed = discord.Embed(title="Trade Note", color=discord.Color.blue())
            embed.description = f"### {trade_data['underlying_symbol']} - {trade_data['name']}\n{self.create_trade_oneliner_os(trade_data, utility_cog)}"
            embed.add_field(name="Note", value=note, inline=False)
            embed.set_footer(text=f"Posted by {ctx.user.name}")

            await utility_cog.send_embed_by_configuration_id(ctx, trade_data['configuration_id'], embed)
            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed OS_NOTE command: Note added to trade {strategy_id}.")

        except Exception as e:
            logger.error(f"Error adding note to options strategy trade: {str(e)}")
            logger.error(traceback.format_exc())
            await logging_cog.log_to_channel(ctx.guild, f"Error in OS_NOTE command by {ctx.user.name}: {str(e)}")

    def create_trade_oneliner_os(self, strategy, utility_cog) -> str:
        """Create a one-line summary of an options strategy trade."""
        try:
            legs = self.deserialize_legs(strategy['legs'])
            legs_str = ""
            latest_expiration = None
            for leg in legs:
                if not latest_expiration or leg['expiration_date'] > latest_expiration:
                    latest_expiration = leg['expiration_date']
                if legs_str != "":
                    if leg['trade_type'] == 'BTO':
                        legs_str += " + "
                    else:
                        legs_str += " - "
                legs_str += f"{leg['strike']}{leg['option_type'][0]}"
            
            if latest_expiration:
                expiration_str = latest_expiration.strftime('%m/%d/%y')
                return f"{strategy['underlying_symbol']} - {strategy['name']} ({expiration_str}) {legs_str}"
            else:
                return f"{strategy['underlying_symbol']} - {strategy['name']} {legs_str}"
        except Exception as e:
            logger.error(f"Error in create_trade_oneliner_os: {str(e)}")
            return "Error creating strategy summary"
    
    def serialize_legs(self, legs):
        """Serialize legs for database storage."""
        return json.dumps([{
            'symbol': leg['symbol'],
            'strike': leg['strike'],
            'expiration_date': leg['expiration_date'].isoformat() if leg['expiration_date'] else None,
            'option_type': leg['option_type'],
            'size': leg['size'],
            'net_cost': leg['net_cost']
        } for leg in legs])

    def deserialize_legs(self, legs_json):
        """Deserialize legs from database storage."""
        if not legs_json:
            return []
        legs = json.loads(legs_json)
        for leg in legs:
            if leg['expiration_date']:
                leg['expiration_date'] = datetime.fromisoformat(leg['expiration_date'])
        return legs


def setup(bot):
    bot.add_cog(OptionsStrategyCog(bot)) 