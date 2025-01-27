import discord
from discord.ext import commands
import logging
from datetime import datetime, date
import re
import traceback
import os

from ..supabase_client import supabase

logger = logging.getLogger(__name__)

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def convert_to_two_digit_year(date_string: str) -> str:
        """Convert a date string to use 2-digit year if it's not already."""
        try:
            date = datetime.strptime(date_string, "%m/%d/%Y")
            return date.strftime("%m/%d/%y")
        except ValueError:
            try:
                # It will be in this format 2025-01-18T##:##:## or 2025-04-20T20:30:00+00:00
                if '+' in date_string:
                    date = datetime.strptime(date_string.split('+')[0], "%Y-%m-%dT%H:%M:%S")
                else:
                    date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
                return date.strftime("%m/%d/%y")
            except ValueError:
                return date_string

    @staticmethod
    def parse_option_symbol(option_string: str) -> dict:
        """Parse an option symbol string into its components.
        
        Format examples:
        - .SPY240119C510 (Weekly)
        - SPY240119C510 (Standard)
        """
        try:
            if option_string.startswith('+'):
                buy_sell = 'BTO'
                option_string = option_string[1:]
            elif option_string.startswith('-'):
                buy_sell = 'STO'
                option_string = option_string[1:]
            else:
                buy_sell = 'BTO'
            # Remove any leading dots (for weeklies)
            clean_string = option_string.strip('.')
            
            # Extract the base symbol (letters at the start)
            match = re.match(r'^([A-Z]+)', clean_string)
            if not match:
                raise ValueError("Invalid option symbol format: No valid symbol found")
            
            symbol = match.group(1)
            remaining = clean_string[len(symbol):]
            
            # Extract date (YYMMDD)
            if len(remaining) < 6:
                raise ValueError("Invalid option symbol format: No valid date found")
            
            date_str = remaining[:6]
            try:
                expiration_date = datetime.strptime(date_str, '%y%m%d')
            except ValueError:
                raise ValueError("Invalid date format in option symbol")
            
            # Extract option type (C/P)
            option_type = remaining[6:7].upper()
            if option_type not in ['C', 'P']:
                raise ValueError("Invalid option type: Must be 'C' or 'P'")
            
            # Extract strike price
            strike_str = remaining[7:]
            if not strike_str:
                raise ValueError("No strike price found in option symbol")
            
            # Convert strike price (handle decimal point)
            strike = float(strike_str) / 1000 if len(strike_str) >= 4 else float(strike_str)
            
            return {
                'symbol': symbol,
                'expiration_date': expiration_date,
                'strike': strike,
                'option_type': option_type,
                'trade_type': buy_sell
            }
        except Exception as e:
            logger.error(f"Error parsing option symbol: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    async def determine_trade_group(expiration_date: str, trade_type: str, symbol: str) -> str:
        """Determine the trade group based on trade parameters."""
        if os.getenv("LOCAL_TEST", "false").lower() == "true":
            return "day_trader"
        
        try:
            # Get trade group configuration from Supabase
            config = await supabase.table('trade_group_rules').select('*').execute()
            if not config.data:
                return "day_trader"  # Default to day trader if no rules found

            # Parse expiration date
            exp_date = datetime.strptime(expiration_date, "%m/%d/%y").date()
            days_to_expiration = (exp_date - date.today()).days

            # Apply rules to determine trade group
            for rule in config.data:
                if (
                    rule.get('min_days') <= days_to_expiration <= rule.get('max_days') and
                    (not rule.get('trade_types') or trade_type in rule.get('trade_types')) and
                    (not rule.get('symbols') or symbol in rule.get('symbols'))
                ):
                    return rule['trade_group']

            return "day_trader"  # Default to day trader if no rules match

        except Exception as e:
            logger.error(f"Error determining trade group: {str(e)}")
            return "day_trader"  # Default to day trader on error

    @staticmethod
    async def get_configuration(trade_group: str):
        """Get trade configuration from Supabase."""
        if os.getenv("LOCAL_TEST", "false").lower() == "true":
            return {
                'id': 1,
                'name': 'day_trader',
                'channel_id': 1283513132546920650,
                'role_id': 1329165857259257947
            }
        
        try:
            response = supabase.table('trade_configurations').select('*').eq('name', trade_group).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting trade configuration: {str(e)}")
            return None

    @staticmethod
    def format_size(size):
        """Format size to remove decimal places if it's a whole number."""
        try:
            float_size = float(size)
            if float_size.is_integer():
                return str(int(float_size))
            return f"{float_size:.2f}"
        except ValueError:
            return size
        
    @staticmethod
    async def get_configuration_by_id(configuration_id: str):
        """Get trade configuration from Supabase by ID."""
        if os.getenv("LOCAL_TEST", "false").lower() == "true":
            #debugging
            return {
                'id': 1,
                'name': 'day_trader',
                'channel_id': 1283513132546920650,
                'role_id': 1284994394554105877
            }
        
        try:
            response = supabase.table('trade_configurations').select('*').eq('id', configuration_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting trade configuration: {str(e)}")
        return None
    
    @staticmethod
    async def send_embed_by_configuration_id(ctx: discord.ApplicationContext, configuration_id: str, embed: discord.Embed, note_embed: discord.Embed = None):
        config = await UtilityCog.get_configuration_by_id(configuration_id)
        try:
            # Send the embed to the configured channel with role ping
            channel = ctx.guild.get_channel(int(config.get('channel_id', None)))
            role = ctx.guild.get_role(int(config.get('role_id', None)))
            await channel.send(content=f"{role.mention}", embed=embed)
            if note_embed:
                await channel.send(embed=note_embed)
            return True
        except Exception as e:
            logger.error(f"Error sending embed by configuration ID: {str(e)}")
            logger.error(traceback.format_exc())

    @commands.slash_command(name="wl", description="Send a watchlist update")
    async def watchlist_update(
        self,
        ctx: discord.ApplicationContext,
        message: discord.Option(str, description="The watchlist update message")
    ):
        logging_cog = self.bot.get_cog('LoggingCog')
        try:
            config = await supabase.table('bot_configurations').select('watchlist_channel_id').single().execute()
            if not config or not config.data or not config.data.get('watchlist_channel_id', None):
                await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed WL command: Watchlist channel not configured. Use /set_watchlist_channel first.")
                await ctx.response.defer(ephemeral=True)
                return

            channel = ctx.guild.get_channel(int(config.data.get('watchlist_channel_id', None)))
            if not channel:
                await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed WL command: Configured watchlist channel not found.")
                await ctx.response.defer(ephemeral=True)
                return

            embed = discord.Embed(title="Watchlist Update", description=message, color=discord.Color.blue())
            embed.set_footer(text=f"Posted by {ctx.user.name}")
            await channel.send(embed=embed)
            await ctx.response.send_message("Watchlist update sent successfully.", ephemeral=True)
            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed WL command: Watchlist update sent successfully.")
        except Exception as e:
            logger.error(f"Error sending watchlist update: {str(e)}")
            logger.error(traceback.format_exc())
            await logging_cog.log_to_channel(ctx.guild, f"Error in WL command by {ctx.user.name}: {str(e)}")
            await ctx.response.defer(ephemeral=True)

def setup(bot):
    bot.add_cog(UtilityCog(bot)) 