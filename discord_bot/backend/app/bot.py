# type: ignore[type-arg]

import asyncio
import io
import logging
import os
import traceback
import re
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from operator import attrgetter
from typing import List, Tuple

import aiofiles
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv

import app.models as models

from .supabase_client import (
    create_trade, add_to_trade, trim_trade, exit_trade, get_trade, get_open_trades,
    get_open_os_trades_for_autocomplete, get_open_trades_for_autocomplete, reopen_trade,
    create_os_trade, supabase, get_verification_config, add_verification_config, add_verification, get_trade_by_id
)

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True  # Enable guild events
intents.presences = True  # Enable presence updates
intents.guild_messages = True  # Enable guild message events

bot = commands.Bot(command_prefix='/', intents=intents, auto_sync_commands=False)

'''
class TradeStatus:
    OPEN = "open"
    CLOSED = "closed"

class TransactionType:
    OPEN = "open"
    ADD = "add"
    TRIM = "trim"
    EXIT = "exit"

class WinLoss:
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"

class TradeGroupEnum:
    DAY_TRADER = "day_trader"
    SWING_TRADER = "swing_trader"
    LONG_TERM_TRADER = "long_term_trader"

    def __str__(self):
        return self.value
'''
last_sync_time = None
SYNC_COOLDOWN = timedelta(hours=1)  # Only sync once per hour


def setup_bot():
    """Setup function to load cogs and configure the bot before running"""
    try:
        # Load all cogs
        bot.load_extension('app.cogs.members')
        bot.load_extension('app.cogs.admin')
        bot.load_extension('app.cogs.verification')
        bot.load_extension('app.cogs.trading')
        bot.load_extension('app.cogs.options_strategy')
        bot.load_extension('app.cogs.utility')
        bot.load_extension('app.cogs.logging')
        bot.load_extension('app.cogs.messages')
        print("Successfully loaded all cogs")
    except Exception as e:
        print(f"Error loading cogs: {e}")
        raise

# Somehow override the run function, or call this from the run function...
def run_bot(token=None):
    if token is None:
        if os.getenv("LOCAL_TEST", "false").lower() == "true":
            token = os.getenv('TEST_TOKEN')
        else:   
            token = os.getenv('DISCORD_TOKEN')

    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set.")
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    try:
        setup_bot()
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start the bot: {str(e)}")
        raise

@bot.event
async def on_ready():
    global last_sync_time
    print(f'{bot.user} has connected to Discord!')

    print("Loaded cogs:", [cog for cog in bot.cogs.keys()])
    
    # Force sync commands on startup
    print("Syncing commands...")
    
    # Check if we need to sync commands
    if last_sync_time is None or datetime.now() - last_sync_time > SYNC_COOLDOWN:
        await sync_commands()
        last_sync_time = datetime.now()
    else:
        print("Skipping command sync due to cooldown")

    print("Bot is ready!")









async def sync_commands():
    guild_ids = []
    if os.getenv("LOCAL_TEST", "false").lower() == "true":
        guild_ids = [os.getenv('TEST_GUILD_ID')]
    else:
        guild_ids = [os.getenv('PROD_GUILD_ID')]
    
    for guild_id in guild_ids:
        if guild_id:
            try:
                guild = discord.Object(id=int(guild_id))
                await sync_commands_with_backoff(guild)
            except Exception as e:
                print(f"Failed to sync commands to the guild with ID {guild_id}: {e}")
        else:
            print(f"Guild ID not set. Skipping command sync.")

async def sync_commands_with_backoff(guild, max_retries=5, base_delay=1):
    for attempt in range(max_retries):
        try:
            print(f"Attempting to sync commands for guild {guild.id} (attempt {attempt + 1}/{max_retries})")
            commands = await bot.sync_commands(guild_ids=[guild.id])
            print(f"Successfully synced {len(commands) if commands else 0} commands to guild {guild.id}")
            return
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limit error
                delay = base_delay * (2 ** attempt)
                print(f"Rate limited. Retrying in {delay} seconds.")
                await asyncio.sleep(delay)
            else:
                print(f"HTTP error while syncing commands: {e}")
                raise
        except Exception as e:
            print(f"Error syncing commands: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(base_delay * (2 ** attempt))
    print(f"Failed to sync commands after {max_retries} attempts.")

async def kill_interaction(interaction):
    await interaction.response.send_message("Processing...", ephemeral=True, delete_after=0)

class TradePaginator(discord.ui.View):
    def __init__(self, trades, interaction):
        super().__init__(timeout=180)
        self.trades = trades
        self.interaction = interaction
        self.current_page = 0
        self.items_per_page = 10

        self.prev_button = discord.ui.Button(label="Previous", style=discord.ButtonStyle.primary)
        self.next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.primary)
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def send_page(self):
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_trades = self.trades[start_idx:end_idx]

        embed = discord.Embed(title="Open Trades", color=discord.Color.blue())
        
        for trade in page_trades:
            # Format trade information
            if trade.get('strike') and trade.get('expiration_date'):
                strike_display = f"${float(trade['strike']):,.2f}" if float(trade['strike']) >= 0 else f"(${abs(float(trade['strike'])):,.2f})"
                trade_display = f"{trade['symbol']} {strike_display} {trade['expiration_date']} - {trade['trade_type']} @ ${float(trade['entry_price']):,.2f} x {format_size(trade['size'])}"
            else:
                trade_display = f"{trade['symbol']} COMMON - {trade['trade_type']} @ ${float(trade['entry_price']):,.2f} x {format_size(trade['size'])}"
            
            embed.add_field(name=f"Trade ID: {trade['trade_id']}", value=trade_display, inline=False)

        total_pages = (len(self.trades) + self.items_per_page - 1) // self.items_per_page
        embed.set_footer(text=f"Page {self.current_page + 1} of {total_pages}")

        if not hasattr(self, 'message'):
            self.message = await self.interaction.followup.send(embed=embed, view=self)
        else:
            await self.message.edit(embed=embed, view=self)

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.send_page()
        await interaction.response.defer()

    async def next_page(self, interaction: discord.Interaction):
        if (self.current_page + 1) * self.items_per_page < len(self.trades):
            self.current_page += 1
            await self.send_page()
        await interaction.response.defer()

'''
@bot.slash_command(name="scrape_channel_for_images", description="Scrape all messages from a channel and save images to a directory")
async def scrape_channel_for_images(
    interaction: discord.Interaction,
    channel: discord.Option(discord.TextChannel, description="The channel to scrape"),
    directory: discord.Option(str, description="The directory to save images to"),
):
    await kill_interaction(interaction)

    try:
        if not os.path.exists(directory):
            os.makedirs(directory)

        image_count = 0
        async for message in channel.history(limit=None):
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                    image_count += 1
                    filename = os.path.join(directory, f"{message.created_at.strftime('%Y%m%d_%H%M%S')}_{attachment.filename}")
                    await attachment.save(filename)

        await interaction.followup.send(f"Successfully saved {image_count} images to {directory}")
    except Exception as e:
        await interaction.followup.send(f"Error scraping images: {str(e)}")
'''
@bot.slash_command(name="help", description="List all available commands and their purposes")
async def help_command(interaction: discord.Interaction):
    """Display all available commands and their purposes."""
    await interaction.response.defer()

    logging_cog = bot.get_cog('LoggingCog')

    try:
        embed = discord.Embed(
            title="Blue Deer Trading Bot Commands",
            description="Here are all the available commands organized by category:",
            color=discord.Color.blue()
        )

        # Regular Trading Commands
        embed.add_field(
            name="📈 Regular Trading Commands",
            value="""
            **/bto** - Buy to open a new trade
            **/sto** - Sell to open a new trade
            **/fut** - Open a new futures trade
            **/lt** - Open a new long-term trade
            **/open** - Open a trade from a symbol string
            **/trades** - List all open trades
            """,
            inline=False
        )

        # Options Strategy Commands
        embed.add_field(
            name="🔄 Options Strategy Commands",
            value="""
            **/os_add** - Add to an existing options strategy trade
            **/os_trim** - Trim an existing options strategy trade
            **/os_exit** - Exit an existing options strategy trade
            **/os_note** - Add a note to an options strategy trade
            """,
            inline=False
        )

        # Trade Management Commands
        embed.add_field(
            name="⚙️ Trade Management Commands",
            value="""
            **/expire_trades** - Exit all expired trades
            **/sync** - Sync trades with external system
            """,
            inline=False
        )

        # Administrative Commands
        embed.add_field(
            name="🔧 Administrative Commands",
            value="""
            **/admin_reopen_trade** - Reopen a closed trade
            **/scrape_channel** - Scrape all messages from a channel
            **/scrape_channel_for_images** - Scrape and save images from a channel
            """,
            inline=False
        )

        # Help Command
        embed.add_field(
            name="❓ Help Command",
            value="""
            **/help** - Display this help message
            """,
            inline=False
        )

        embed.set_footer(text="Use / to access any command. Each command will guide you through the required parameters.")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        await logging_cog.log_to_channel(interaction.guild, f"User {interaction.user.name} executed HELP command.")

    except Exception as e:
        logger.error(f"Error in help command: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.followup.send("Error displaying help message. Please try again later.", ephemeral=True)
        await logging_cog.log_to_channel(interaction.guild, f"Error in HELP command by {interaction.user.name}: {str(e)}")
