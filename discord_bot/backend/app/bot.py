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
from discord.ext import tasks
from dotenv import load_dotenv

from .supabase_client import (
    create_trade, add_to_trade, trim_trade, exit_trade, get_trade, get_open_trades,
    get_open_os_trades_for_autocomplete, get_open_trades_for_autocomplete, reopen_trade,
    create_os_trade, supabase
)

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True  # Enable guild events
intents.presences = True  # Enable presence updates
intents.guild_messages = True  # Enable guild message events

bot = commands.Bot(command_prefix='/', intents=intents, auto_sync_commands=False)

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

last_sync_time = None
SYNC_COOLDOWN = timedelta(hours=1)  # Only sync once per hour

async def run_bot():
    if os.getenv("LOCAL_TEST", "false").lower() == "true":
        token = os.getenv('TEST_TOKEN')
    else:   
        token = os.getenv('DISCORD_TOKEN')

    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set.")
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    try:
        print("Starting bot setup...")
        # Load the members cog
        try:
            bot.load_extension('app.cogs.members')
            print("Successfully loaded members cog")
        except Exception as e:
            print(f"Error loading members cog: {e}")
        await bot.start(token)
    except Exception as e:
        logger.error(f"Failed to start the bot: {str(e)}")
        raise

@bot.event
async def on_ready():
    global last_sync_time
    print(f'{bot.user} has connected to Discord!')
    create_tables(engine)

    print("Loaded cogs:", [cog for cog in bot.cogs.keys()])
    
    # Force sync commands on startup
    print("Syncing commands...")
    
    if os.getenv("LOCAL_TEST", "false").lower() != "true":
        check_and_update_roles.start()
        check_and_exit_expired_trades.start()
    
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

async def log_command_usage(interaction: discord.Interaction, command_name: str, params: dict):
    """Log command usage to the log channel."""
    try:
        # Format parameters, excluding any None values
        param_str = ', '.join(f"{k}={v}" for k, v in params.items() if v is not None)
        log_message = f"Command executed: /{command_name} by {interaction.user.name} ({interaction.user.id})\nParameters: {param_str}"
        await log_to_channel(interaction.guild, log_message)
    except Exception as e:
        logger.error(f"Error logging command usage: {str(e)}")
        logger.error(traceback.format_exc())

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

def format_size(size):
    """Format size to remove decimal places if it's a whole number."""
    try:
        float_size = float(size)
        if float_size.is_integer():
            return str(int(float_size))
        return f"{float_size:.2f}"
    except ValueError:
        return size  # Return as is if it can't be converted to float

def serialize_legs(legs):
    """Serialize legs for database storage."""
    return json.dumps([{
        'symbol': leg['symbol'],
        'strike': leg['strike'],
        'expiration_date': leg['expiration_date'].isoformat() if leg['expiration_date'] else None,
        'option_type': leg['option_type'],
        'size': leg['size'],
        'net_cost': leg['net_cost']
    } for leg in legs])

def deserialize_legs(legs_json):
    """Deserialize legs from database storage."""
    if not legs_json:
        return []
    legs = json.loads(legs_json)
    for leg in legs:
        if leg['expiration_date']:
            leg['expiration_date'] = datetime.fromisoformat(leg['expiration_date'])
    return legs

def convert_to_two_digit_year(date_string: str) -> str:
    """Convert a date string to use 2-digit year if it's not already."""
    try:
        date = datetime.strptime(date_string, "%m/%d/%Y")
        return date.strftime("%m/%d/%y")
    except ValueError:
        try:
            # It will be in this format 2025-01-18T##:##:##
            date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
            return date.strftime("%m/%d/%y")
        except ValueError:
            return date_string

def convert_timestamp_string_to_two_digit_year(timestamp_string: str) -> str:
    """Convert a timestamp string to use 2-digit year if it's not already."""
    try:
        timestamp = datetime.fromisoformat(timestamp_string)
        return timestamp.strftime("%m/%d/%y")
    except ValueError:
        return timestamp_string

def create_transaction_oneliner(trade: dict, type: str, size: float, price: float):
    """Create a one-line summary of a transaction."""
    ot = trade.get('option_type', None)
    if ot:
        if ot.startswith("C"):
            option_type = "CALL"
        elif ot.startswith("P"):
            option_type = "PUT"   
        else:
            option_type = ot
    else:
        option_type = ""

    risk_identifier = "risk" if type == "ADD" else "size"

    if trade.get('is_contract'):
        expiration = convert_timestamp_string_to_two_digit_year(trade.get('expiration_date')) if trade.get('expiration_date', None) else "No Exp"
        strike = f"{trade.get('strike'):.2f}"
        return f"### {type} {expiration} {trade.get('symbol')} {strike} {option_type} @ {price:.2f} {size} {risk_identifier}"
    else:
        return f"### {type} {trade.get('symbol')} @ {price:.2f} {size} {risk_identifier}"

def create_trade_oneliner(trade: dict, price: float, size: float) -> str:
    """Create a one-line summary of a trade."""

    ot = trade.get('option_type', None)
    if ot:
        if ot.startswith("C"):
            option_type = "CALL"
        elif ot.startswith("P"):
            option_type = "PUT"   
        else:
            option_type = ot
    else:
        option_type = ""

    if size == 0:
        size = trade.get('current_size', None) if trade.get('current_size') else trade.get('size', None)
    if price == 0:
        price = trade.get('average_price', None)
    display_price = f"${price:.2f}"
    
    if trade.get('is_contract'):
        expiration = convert_to_two_digit_year(trade.get('expiration_date')) if trade.get('expiration_date') else "No Exp"
        strike = f"${trade.get('strike'):.2f}"
        return f"### {expiration} {trade.get('symbol')} {strike} {option_type} @ {display_price} {size} risk"
    else:
        return f"### {trade.get('symbol')} @ {display_price} {size} risk"

def create_trade_oneliner_os(strategy) -> str:
    """Create a one-line summary of an options strategy trade."""
    try:
        legs = deserialize_legs(strategy.legs)
        latest_expiration = None
        for leg in legs:
            if not latest_expiration or leg['expiration_date'] > latest_expiration:
                latest_expiration = leg['expiration_date']
        
        if latest_expiration:
            expiration_str = latest_expiration.strftime('%m/%d/%y')
            return f"{strategy['underlying_symbol']} {expiration_str} - {strategy['name']} @ ${strategy['average_net_cost']:,.2f} x {format_size(strategy['current_size'])}"
        else:
            return f"{strategy['underlying_symbol']} - {strategy['name']} @ ${strategy['average_net_cost']:,.2f} x {format_size(strategy['current_size'])}"
    except Exception as e:
        logger.error(f"Error in create_trade_oneliner_os: {str(e)}")
        return "Error creating strategy summary"
    
async def get_open_trade_ids(ctx: discord.AutocompleteContext):
    try:
        # Get open trades directly from the database
        trades = await get_open_trades_for_autocomplete()
        print(trades)
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
        return [discord.OptionChoice(name=f"{display} (ID: {trade_id})", value=trade_id) for trade_id, display, _ in sorted_trades]
    except Exception as e:
        logger.error(f"Error in get_open_trade_ids: {str(e)}")
        logger.error(traceback.format_exc())
        return []

async def get_open_os_trade_ids(ctx: discord.AutocompleteContext):
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
        return [discord.OptionChoice(name=f"{display} (ID: {trade_id})", value=trade_id) for trade_id, display, _ in sorted_trades]
    except Exception as e:
        logger.error(f"Error in get_open_os_trade_ids: {str(e)}")
        logger.error(traceback.format_exc())
        return []

async def get_trade_groups(ctx: discord.AutocompleteContext):
    """Get available trade groups for autocomplete."""
    try:
        # Get trade groups from Supabase
        response = await supabase.table('trade_configurations').select('name').execute()
        if response.data:
            return [
                discord.OptionChoice(name=config['name'].replace('_', ' ').title(), value=config['name'])
                for config in response.data
            ]
    except Exception as e:
        logger.error(f"Error getting trade groups: {str(e)}")
    
    # Return default trade groups if Supabase query fails
    return [
        discord.OptionChoice(name="Day Trader", value=TradeGroupEnum.DAY_TRADER),
        discord.OptionChoice(name="Swing Trader", value=TradeGroupEnum.SWING_TRADER),
        discord.OptionChoice(name="Long-Term Trader", value=TradeGroupEnum.LONG_TERM_TRADER),
    ]

async def get_configuration_by_id(configuration_id: str):
    if os.getenv("LOCAL_TEST", "false").lower() == "true":
        return {
            'id': 1,
            'name': 'day_trader',
            'channel_id': 1283513132546920650,
            'role_id': 1284994394554105877
        }

    response = supabase.table('trade_configurations').select('*').eq('id', configuration_id).execute()
    return response.data[0] if response.data else None

async def send_embed_by_configuration_id(interaction: discord.Interaction, configuration_id: str, embed: discord.Embed, note_embed: discord.Embed = None):
    config = await get_configuration_by_id(configuration_id)
    try:
        # Send the embed to the configured channel with role ping
        channel = interaction.guild.get_channel(int(config.get('channel_id', None)))
        role = interaction.guild.get_role(int(config.get('role_id', None)))
        await channel.send(content=f"{role.mention}", embed=embed)
        if note_embed:
            await channel.send(embed=note_embed)
        return True
    except Exception as e:
        logger.error(f"Error sending embed by configuration ID: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        db.close()

async def exit_expired_os_trade(trade: models.OptionsStrategyTrade):
    db = next(get_db())
    try:
        trade = db.merge(trade)

        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.id == trade.configuration_id).first()
        if not config:
            logger.error(f"Configuration for trade {trade.trade_id} not found.")
            return

        # Set exit price to max loss
        exit_price = 0

        trade.status = models.OptionsStrategyStatusEnum.CLOSED
        trade.exit_price = exit_price
        trade.closed_at = datetime.now()
        
        current_size = Decimal(trade.current_size)
        
        new_transaction = models.OptionsStrategyTransaction(
            strategy_id=trade.id,
            transaction_type=models.TransactionTypeEnum.CLOSE,
            net_cost=exit_price,
            size=str(current_size),
            created_at=datetime.now()
        )
        db.add(new_transaction)

        """# Calculate profit/loss
        open_transactions = crud.get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
        trim_transactions = crud.get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.TRIM])
        
        total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
        total_open_size = sum(Decimal(t.size) for t in open_transactions)
        
        average_cost = total_cost / total_open_size if total_open_size > 0 else 0

        close_transactions = crud.get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.CLOSE])
        avg_exit_price = sum(Decimal(t.amount) * Decimal(t.size) for t in close_transactions) / sum(Decimal(t.size) for t in close_transactions) if close_transactions else 0
        trade.average_exit_price = float(avg_exit_price)
        
        trim_profit_loss = 0
        if trim_transactions:
            trim_profit_loss = sum((Decimal(t.amount) - average_cost) * Decimal(t.size) for t in trim_transactions)
        exit_profit_loss = (Decimal(exit_price) - average_cost) * current_size
        
        total_profit_loss = trim_profit_loss + exit_profit_loss
        trade.profit_loss = float(total_profit_loss)

        # Determine win/loss
        trade.win_loss = models.WinLossEnum.LOSS"""

        logger.info(f"Exiting expired OS trade {trade.trade_id} with exit price {exit_price} and current size {current_size}")

        db.commit()
        db.refresh(trade)

        '''
        TODO: We are commenting this out for now. Fix this.

        # Create an embed with the closed trade information
        embed = discord.Embed(title="Trade Expired and Closed", color=discord.Color.red())
        embed.description = create_trade_oneliner(trade)
        embed.add_field(name="Exit Price", value=f"${exit_price:.2f}", inline=True)
        embed.add_field(name="Final Size", value=current_size, inline=True)
        embed.add_field(name="Total Profit/Loss", value=f"${total_profit_loss:.2f}", inline=True)
        embed.add_field(name="Result", value="Loss (Expired)", inline=True)
        embed.set_footer(text=f"Trade ID: {trade.trade_id}")

        # Send the embed to the configured channel with role ping
        channel = bot.get_channel(int(config.channel_id))
        role = channel.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)
        '''

    except Exception as e:
        logger.error(f"Error exiting expired trade {trade.trade_id}: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        db.close()

async def log_command_usage(interaction: discord.Interaction, command_name: str, params: dict):
    """Log command usage to the log channel."""
    try:
        # Format parameters, excluding any None values
        param_str = ', '.join(f"{k}={v}" for k, v in params.items() if v is not None)
        log_message = f"Command executed: /{command_name} by {interaction.user.name} ({interaction.user.id})\nParameters: {param_str}"
        await log_to_channel(interaction.guild, log_message)
    except Exception as e:
        logger.error(f"Error logging command usage: {str(e)}")
        logger.error(traceback.format_exc())

class VerificationModal(discord.ui.Modal):
    def __init__(self, config, terms_link, *args, **kwargs):
        super().__init__(title="Verification Form", *args, **kwargs)
        self.config = config
        
        # Confirmation of reading terms
        self.agreement = discord.ui.InputText(
            label="Terms Agreement",
            style=discord.InputTextStyle.short,
            placeholder="Type 'I AGREE' to confirm you have read and accept the terms",
            required=True,
            min_length=7,
            max_length=7
        )
        self.add_item(self.agreement)
        
        self.full_name = discord.ui.InputText(
            label="Full Name",
            style=discord.InputTextStyle.short,
            placeholder="Enter your full name",
            required=True,
            min_length=2,
            max_length=100
        )
        self.add_item(self.full_name)
        
        self.email = discord.ui.InputText(
            label="Email Address",
            style=discord.InputTextStyle.short,
            placeholder="Enter your email address",
            required=True,
            min_length=5,
            max_length=100
        )
        self.add_item(self.email)

    async def callback(self, interaction: discord.Interaction):
        print(f"agreement value: {self.agreement.value}")
        if str(self.agreement.value).upper() != "I AGREE":
            await interaction.response.send_message(
                "You must type 'I AGREE' to confirm you have read and accept the terms and conditions.", 
                ephemeral=True
            )
            return
        await handle_verification(interaction, self.config, str(self.full_name.value), str(self.email.value))

@bot.slash_command(name="setup_verification", description="Set up a verification message with terms and conditions")
async def setup_verification(
    interaction: discord.Interaction,
    channel: discord.Option(discord.TextChannel, description="The channel to send the verification message"),
    terms_link: discord.Option(str, description="Link to the terms and conditions document"),
    terms_summary: discord.Option(str, description="Brief summary of the terms (shown in message)"),
    role_to_remove: discord.Option(discord.Role, description="The role to remove upon verification"),
    role_to_add: discord.Option(discord.Role, description="The role to add upon verification"),
    log_channel: discord.Option(discord.TextChannel, description="The channel for logging verifications"),
):
    await interaction.response.defer(ephemeral=True)
    
    db = next(get_db())
    try:
        embed = discord.Embed(title="Verification Required", color=discord.Color.blue())
        embed.description = (
            f"{terms_summary}\n\n"
            f"**Please read our full Terms and Conditions here:**\n[Blue Deer Trading Terms and Conditions]({terms_link})\n\n"
            "Click the button below to start the verification process. "
            "You will need to confirm that you have read and agree to the terms."
        )
        button = discord.ui.Button(style=discord.ButtonStyle.green, label="Start Verification", custom_id="verify")
        view = discord.ui.View(timeout=None)
        view.add_item(button)
        message = await channel.send(embed=embed, view=view)

        new_config = models.VerificationConfig(
            message_id=str(message.id),
            channel_id=str(channel.id),
            role_to_remove_id=str(role_to_remove.id),
            role_to_add_id=str(role_to_add.id),
            log_channel_id=str(log_channel.id),
        )
        db.add(new_config)
        db.commit()

        await interaction.followup.send("Verification message set up successfully.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in setup_verification: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.followup.send(f"An error occurred while setting up verification: {str(e)}", ephemeral=True)
    finally:
        db.close()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        if interaction.type == discord.InteractionType.component:
            if interaction.data["custom_id"] == "verify":
                db = next(get_db())
                try:
                    config = db.query(models.VerificationConfig).filter_by(message_id=str(interaction.message.id)).first()
                    if not config:
                        await interaction.response.send_message("Verification configuration not found.", ephemeral=True)
                        return
                    
                    # Get the terms link from the original message's embed
                    terms_link = ""
                    if interaction.message.embeds:
                        description = interaction.message.embeds[0].description
                        # Extract the link from the description
                        for line in description.split('\n'):
                            if "http" in line:
                                terms_link = line.strip()
                                break
                    
                    modal = VerificationModal(config, terms_link)
                    await interaction.response.send_modal(modal)
                    return
                finally:
                    db.close()
        
        await bot.process_application_commands(interaction)
    except Exception as e:
        logger.error(f"Error in on_interaction: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)
async def handle_verification(interaction: discord.Interaction, config, full_name: str, email: str):
    db = next(get_db())
    try:
        role_to_remove = interaction.guild.get_role(int(config.role_to_remove_id))
        role_to_add = interaction.guild.get_role(int(config.role_to_add_id))
        log_channel = interaction.guild.get_channel(int(config.log_channel_id))

        await interaction.user.remove_roles(role_to_remove)
        await interaction.user.add_roles(role_to_add)

        log_embed = discord.Embed(
            title="User Verified",
            description=f"{interaction.user.mention} has accepted the terms and conditions.",
            color=discord.Color.green()
        )
        log_embed.add_field(name="Full Name", value=full_name)
        log_embed.add_field(name="Email", value=email)
        await log_channel.send(embed=log_embed)

        new_verification = models.Verification(
            user_id=str(interaction.user.id),
            username=str(interaction.user.name),
            #full_name=full_name,
            #email=email,
            timestamp=datetime.utcnow(),
            configuration_id=config.id
        )

        # Write the verification to a local file as well. Append it to the file in CSV format. If the file doesn't exist, create it.
        with open('verifications.csv', 'a') as f:
            f.write(f"{interaction.user.id},{interaction.user.name},{full_name},{email}\n")

        db.add(new_verification)
        db.commit()

        await interaction.response.send_message("You have been verified!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in handle_verification: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.response.send_message(f"An error occurred during verification: {str(e)}", ephemeral=True)
    finally:
        db.close()

def parse_option_symbol(option_string: str) -> dict:
    """Parse an option symbol string into its components.
    
    Format examples:
    - .SPY240119C510 (Weekly)
    - SPY240119C510 (Standard)
    
    Returns:
    - Dictionary containing symbol, expiration_date, strike, option_type, and trade_type
    """
    try:
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
            'trade_type': 'BTO'  # Default to BTO
        }

async def get_open_trade_ids(ctx: discord.AutocompleteContext):
    db = next(get_db())
    try:
        open_trades = crud.get_trades(db, status=models.TradeStatusEnum.OPEN)
        
        # Format trade information
        trade_info = []
        for trade in open_trades:
            symbol = trade.symbol
            strike = getattr(trade, 'strike', None)
            expiration = getattr(trade, 'expiration_date', None)
            
            if strike and expiration:
                strike_display = f"${strike:,.2f}" if strike >= 0 else f"(${abs(strike):,.2f})"
                display = f"{symbol} {strike_display} {expiration.strftime('%m/%d/%y')}"
                sort_key = (symbol, expiration, strike)
            else:
                display = f"{symbol} COMMON"
                sort_key = (symbol, datetime.max, 0)  # Put non-option trades at the bottom of their symbol group
            
            trade_info.append((trade.trade_id, display, sort_key))
        
        # Sort the trades
        sorted_trades = sorted(trade_info, key=lambda x: x[2])
        
        # Create OptionChoice objects
        return [discord.OptionChoice(name=f"{display} (ID: {trade_id})", value=trade_id) for trade_id, display, _ in sorted_trades]
    finally:
        db.close()

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

async def get_open_os_trade_ids(ctx: discord.AutocompleteContext):
    db = next(get_db())
    try:
        open_trades = crud.get_os_trades(db, status=models.OptionsStrategyStatusEnum.OPEN)
        
        # Format trade information
        trade_info = []
        for trade in open_trades:
            symbol = trade.underlying_symbol
            name = trade.name
            expiration_date = None
            for leg in deserialize_legs(trade.legs):
                if not expiration_date or leg['expiration_date'] > expiration_date:
                    expiration_date = leg['expiration_date']

            display = f"{symbol} {expiration_date.strftime('%m/%d/%y')} @ {trade.average_net_cost:.2f}- {name}"
            sort_key = (symbol, expiration_date, name)
            
            trade_info.append((trade.trade_id, display, sort_key))
        
        # Sort the trades
        sorted_trades = sorted(trade_info, key=lambda x: x[2])
        
        # Create OptionChoice objects
        return [discord.OptionChoice(name=f"{display} (ID: {trade_id})", value=trade_id) for trade_id, display, _ in sorted_trades]
    finally:
        db.close()

async def get_trade_groups(ctx: discord.AutocompleteContext):
    db = next(get_db())
    try:
        trade_groups = db.query(models.TradeConfiguration.name).distinct().all()
        return [group[0] for group in trade_groups]
    finally:
        db.close()

def convert_to_two_digit_year(date_string):
    """Convert a date string to use 2-digit year if it's not already."""
    try:
        date = datetime.strptime(date_string, "%m/%d/%Y")
        return date.strftime("%m/%d/%y")
    except ValueError:
        # If it's already in MM/DD/YY format, return as is
        return date_string

def determine_trade_group(expiration_date: str, trade_type: str, symbol: str) -> str:
    print("determine_trade_group called")
    if symbol == "ES":
        return TradeGroupEnum.DAY_TRADER
    
    if not expiration_date and (trade_type == "sto" or trade_type == "bto"):
        return TradeGroupEnum.SWING_TRADER
    
    try:
        # Try parsing with 2-digit year first
        exp_date = datetime.strptime(expiration_date, "%m/%d/%y").date()
    except ValueError:
        try:
            # If that fails, try with 4-digit year
            exp_date = datetime.strptime(expiration_date, "%m/%d/%Y").date()
        except ValueError:
            # If both fail, return default
            return TradeGroupEnum.SWING_TRADER
    
    days_to_expiration = (exp_date - datetime.now().date()).days
    print("days_to_expiration", days_to_expiration)
    
    if days_to_expiration <= 3:
        print(f"Returning DAY_TRADER for {expiration_date}")
        return TradeGroupEnum.DAY_TRADER
    elif days_to_expiration <= 90:
        print(f"Returning SWING_TRADER for {expiration_date}")
        return TradeGroupEnum.SWING_TRADER
    else:
        print(f"Returning LONG_TERM_TRADER for {expiration_date}")
        return TradeGroupEnum.LONG_TERM_TRADER

def get_configuration(db: Session, trade_group: str) -> models.TradeConfiguration:
    """
    Retrieve the trade configuration for a given trade group.
    
    Args:
    db (Session): The database session.
    trade_group (str): The name of the trade group.

    Returns:
    models.TradeConfiguration: The trade configuration for the given trade group, or None if not found.
    """
    return db.query(models.TradeConfiguration).filter(models.TradeConfiguration.name == trade_group).first()

def create_trade_oneliner(trade, price = 0, size = 0):
    """Create a one-liner summary of the trade."""
    if trade.option_type:
        if trade.option_type.startswith("C"):
            option_type = "CALL"
        elif trade.option_type.startswith("P"):
            option_type = "PUT"   
        else:
            option_type = trade.option_type
    else:
        option_type = ""

    if size == 0:
        size = trade.current_size if trade.current_size else trade.size
    if price == 0:
        price = trade.average_price
    display_price = f"${price:.2f}"
    
    if trade.is_contract:
        expiration = convert_to_two_digit_year(trade.expiration_date.strftime('%m/%d/%y')) if trade.expiration_date else "No Exp"
        strike = f"${trade.strike:.2f}"
        return f"### {expiration} {trade.symbol} {strike} {option_type} @ {display_price} {size} risk"
    else:
        return f"### {trade.symbol} @ {display_price} {size} risk"
    
def create_transaction_oneliner(trade, type, size, price):
    if trade.option_type:
        if trade.option_type.startswith("C"):
            option_type = "CALL"
        elif trade.option_type.startswith("P"):
            option_type = "PUT"   
        else:
            option_type = trade.option_type
    else:
        option_type = ""

    risk_identifier = "risk" if type == "ADD" else "size"

    if trade.is_contract:
        expiration = convert_to_two_digit_year(trade.expiration_date.strftime('%m/%d/%y')) if trade.expiration_date else "No Exp"
        strike = f"{trade.strike:.2f}"
        return f"### {type} {expiration} {trade.symbol} {strike} {option_type} @ {price:.2f} {size} {risk_identifier}"
    else:
        return f"### {type} {trade.symbol} @ {price:.2f} {size} {risk_identifier}"
    
def serialize_legs(legs):
    """Serialize the legs data for storage in the database."""
    return json.dumps([{**leg, 'expiration_date': leg['expiration_date'].strftime('%Y-%m-%d')} for leg in legs])

def deserialize_legs(legs_json):
    """Deserialize the legs data from the database."""
    legs = json.loads(legs_json)
    for leg in legs:
        leg['expiration_date'] = datetime.strptime(leg['expiration_date'], '%Y-%m-%d').date()
    return legs

def create_trade_oneliner_os(os_trade):
    add_date = True
    trade_oneliner = f"{os_trade.underlying_symbol} - {os_trade.name} "
    legs = deserialize_legs(os_trade.legs)  # Use the new deserialize_legs function
    for leg in legs:
        if add_date:
            trade_oneliner += f" ({leg['expiration_date'].strftime('%m/%d/%y')}) "
            add_date = False
        else:
            if leg['option_type'] == "C":
                trade_oneliner += "+"
            else:
                trade_oneliner += "-"
        
        trade_oneliner += f"{leg['strike']}{leg['option_type'][0]}"

    return trade_oneliner

@bot.slash_command(name="open", description="Open a trade from a symbol string")
async def open_trade(
    interaction: discord.Interaction,
    trade_string: discord.Option(str, description="The trade string to parse"),
    price: discord.Option(float, description="The price of the trade"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    """Open a new trade."""
    await kill_interaction(interaction)

    try:
        parsed = parse_option_symbol(trade_string)
        # Determine trade group
        trade_group = await determine_trade_group(
            parsed['expiration_date'].strftime("%m/%d/%y"), 
            parsed['trade_type'], 
            parsed['symbol']
        )

        # Get configuration for trade group
        config = await get_configuration(trade_group)

        # TODO Fix this
        if not config:
            await interaction.followup.send(f"No configuration found for trade group {trade_group}", ephemeral=True)
            return None

        # Create trade using Supabase edge function
        response = await create_trade(
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

        trade_data = response['trade']

        if trade_data:
            # Create and send embed
            embed = discord.Embed(title="New Trade Opened", color=discord.Color.green())
            embed.description = create_trade_oneliner(trade_data, price, size)
            embed.add_field(name="Symbol", value=parsed['symbol'], inline=True)
            embed.add_field(name="Type", value=parsed['trade_type'], inline=True)
            embed.add_field(name="Entry Price", value=f"${price:,.2f}", inline=True)
            embed.add_field(name="Risk Level (1-6)", value=size, inline=True)
            embed.add_field(name="Expiration", value=parsed['expiration_date'].strftime("%m/%d/%y"), inline=True)
            embed.add_field(name="Strike", value=f"${parsed['strike']:,.2f}", inline=True)
            embed.add_field(name="Option Type", value="CALL" if parsed['option_type'] == "C" else "PUT", inline=True)
            embed.set_footer(text=f"Trade ID: {trade_data['trade_id']}")
            if note:
                embed.add_field(name="Note", value=note, inline=False)

        channel = interaction.guild.get_channel(config.get('channel_id'))
        role = interaction.guild.get_role(config.get('role_id'))
        await channel.send(content=f"{role.mention if role else ''}", embed=embed)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OPEN command: Trade has been opened successfully.")
    except ValueError as e:
        await log_to_channel(interaction.guild, f"Error in OPEN command by {interaction.user.name}: {str(e)}")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in OPEN command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="add", description="Add to an existing trade")
async def add_action(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the trade to add to", autocomplete=get_open_trade_ids),
    price: discord.Option(float, description="The price of the trade"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)

    trade_data = await add_to_trade(trade_id, price, size)
    print(trade_data)

    # Create an embed with the transaction information
    embed = discord.Embed(title="Added to Trade", color=discord.Color.teal())
    embed.description = create_transaction_oneliner(trade_data, "ADD", size, price)
    embed.add_field(name="New Total Size", value=format_size(trade_data.get('current_size', None)), inline=True)
    embed.add_field(name="New Avg Price", value=f"${trade_data.get('average_price', None):.2f}", inline=True)

    embed.set_footer(text=f"Trade ID: {trade_data.get('trade_id', None)}")
    
    # Send an additional embed with the note if provided
    note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None
    if not await send_embed_by_configuration_id(interaction, trade_data.get('configuration_id', None), embed, note_embed):
        await log_to_channel(interaction.guild, f"User {interaction.user.name} **FAILED** ADD command: Trade {trade_id} NOT ADDED TO.")
        return
    
    await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD command: Transaction added to trade {trade_id} successfully.")

@bot.slash_command(name="trim", description="Trim an existing trade")
async def trim_action(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the trade to trim", autocomplete=get_open_trade_ids),
    price: discord.Option(float, description="The price of the trade"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)

    trade_data = await trim_trade(trade_id, price, size)
    print(trade_data)

    # Create an embed with the transaction information
    embed = discord.Embed(title="Trimmed Trade", color=discord.Color.orange())
    embed.description = create_transaction_oneliner(trade_data, "TRIM", size, price)
    embed.add_field(name="Size Remaining", value=format_size(trade_data.get('current_size', None)), inline=True)
    embed.set_footer(text=f"Trade ID: {trade_data.get('trade_id', None)}")
    
    # Send an additional embed with the note if provided
    note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None
    if not await send_embed_by_configuration_id(interaction, trade_data.get('configuration_id', None), embed, note_embed):
        await log_to_channel(interaction.guild, f"User {interaction.user.name} **FAILED** TRIM command: Trade {trade_id} NOT TRIMMED.")
        return
    
    await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TRIM command: Trade {trade_id} trimmed successfully.")

@bot.slash_command(name="exit", description="Exit an existing trade")
async def exit_action(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the trade to exit", autocomplete=get_open_trade_ids),
    price: discord.Option(float, description="The price of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)

    trade_data = await exit_trade(trade_id, price)
    print(trade_data)

    # Create an embed with the closed trade information
    embed = discord.Embed(title="Trade Closed", color=discord.Color.gold())
    embed.description = create_transaction_oneliner(trade_data, "EXIT", trade_data.get('exit_size'), price)

    # Calculate profit/loss per share or per contract
    if trade_data.get('is_contract'):
        profit_loss_per_unit = (trade_data.get('profit_loss') / float(trade_data.get('size'))) * 100 # Assuming 100 shares per contract
        unit_type = "contract"
    else:
        profit_loss_per_unit = trade_data.get('profit_loss') / float(trade_data.get('size'))
        unit_type = "share"
    
    embed.add_field(name=f"Trade P/L per {unit_type}", value=f"${profit_loss_per_unit:.2f}", inline=True)
    embed.add_field(name="Avg Entry Price", value=f"${trade_data.get('average_price', None):.2f}", inline=True)
    if trade_data.get('average_exit_price', None):
        embed.add_field(name="Avg Exit Price", value=f"${trade_data.get('average_exit_price', None):.2f}", inline=True)
    else:
        embed.add_field(name="Avg Exit Price", value=f"${price:.2f}", inline=True)
    embed.set_footer(text=f"Trade ID: {trade_data.get('trade_id', None)}")
    
    # Send an additional embed with the note if provided
    note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey()) if note else None
    if not await send_embed_by_configuration_id(interaction, trade_data.get('configuration_id', None), embed, note_embed):
        await log_to_channel(interaction.guild, f"User {interaction.user.name} **FAILED** EXIT command: Trade {trade_id} NOT EXITED.")
        return
    
    await log_to_channel(interaction.guild, f"User {interaction.user.name} executed EXIT command: Trade {trade_id} exited successfully.")

@bot.slash_command(name="fut", description="Buy to open a new futures trade")
async def future_trade(
    interaction: discord.Interaction,
    symbol: discord.Option(str, description="The symbol of the security"),
    entry_price: discord.Option(float, description="The price at which the trade was opened"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "fut", {
        "symbol": symbol,
        "entry_price": entry_price,
        "size": size,
        "note": note
    })
    await common_stock_trade(interaction, TradeGroupEnum.DAY_TRADER, symbol, entry_price, size, note)

@bot.slash_command(name="lt", description="Buy to open a new long-term trade")
async def lt_trade(
    interaction: discord.Interaction,
    symbol: discord.Option(str, description="The symbol of the security"),
    entry_price: discord.Option(float, description="The price at which the trade was opened"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "lt", {
        "symbol": symbol,
        "entry_price": entry_price,
        "size": size,
        "note": note
    })
    await common_stock_trade(interaction, TradeGroupEnum.LONG_TERM_TRADER, symbol, entry_price, size, note)

# Helper function for common stock trades
async def common_stock_trade(
    interaction: discord.Interaction,
    trade_group: TradeGroupEnum,
    symbol: str,
    entry_price: float,
    size: str,
    note: str = None,
):
    try:
        new_trade = await create_trade(
            interaction=interaction,
            symbol=symbol,
            entry_price=entry_price,
            size=size,
            trade_type="BTO",  # Common stock trades are typically BTO
            expiration_date=None,  # Stocks don't have expiration dates
            strike=None,  # Stocks don't have strike prices
            option_type=None,
            trade_group=trade_group,
            note=note
        )
        if new_trade:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed {trade_group} command: Trade has been opened successfully.")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in {trade_group} command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="scrape_channel", description="Scrape all messages from a channel and save to a file")
async def scrape_channel(
    interaction: discord.Interaction,
    channel: discord.Option(discord.TextChannel, description="The channel to scrape"),
    filename: discord.Option(str, description="The filename to save to"),
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "scrape_channel", {
        "channel": channel.name,
        "filename": filename
    })
    
    try:
        messages = []
        async for message in channel.history(limit=None):
            messages.append({
                'author': message.author.name,
                'content': message.content,
                'timestamp': message.created_at.isoformat(),
                'attachments': [attachment.url for attachment in message.attachments]
            })

        with open(filename, 'w') as f:
            json.dump(messages, f, indent=2)

        await interaction.followup.send(f"Successfully scraped {len(messages)} messages to {filename}")
    except Exception as e:
        await interaction.followup.send(f"Error scraping channel: {str(e)}")

@bot.slash_command(name="scrape_channel_for_images", description="Scrape all messages from a channel and save images to a directory")
async def scrape_channel_for_images(
    interaction: discord.Interaction,
    channel: discord.Option(discord.TextChannel, description="The channel to scrape"),
    directory: discord.Option(str, description="The directory to save images to"),
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "scrape_channel_for_images", {
        "channel": channel.name,
        "directory": directory
    })
    
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

async def get_verification_log_channel(guild):
    try:
        # Get log channel from Supabase configuration
        config = await supabase.table('verification_config').select('log_channel_id').single().execute()
        if config and config.data and config.data.get('log_channel_id'):
            return guild.get_channel(int(config.data['log_channel_id']))
    except Exception as e:
        print(f"Error getting verification log channel: {str(e)}")
        print(traceback.format_exc())
    return None

async def log_to_channel(guild, message):
    try:
        if os.getenv("LOCAL_TEST", "false").lower() == "true":
            log_channel_id = 1283513132546920650
        else:
            # Get log channel from Supabase configuration
            config = supabase.table('bot_configuration').select('log_channel_id').single().execute()
            if config and config.data and config.data.get('log_channel_id'):
                log_channel_id = config.data['log_channel_id']

        log_channel = guild.get_channel(int(log_channel_id))
        if log_channel:
            await log_channel.send(message)
    except Exception as e:
        print(f"Error logging to channel: {str(e)}")
        print(traceback.format_exc())


# ================= Options Strategy Functions =================

@bot.slash_command(name="os", description="Open a new options strategy trade")
async def os_trade(
    interaction: discord.Interaction,
    strategy_name: discord.Option(str, description="The name of the strategy (e.g., 'Iron Condor', 'Call Spread')"),
    size: discord.Option(str, description="The size of the strategy"),
    net_cost: discord.Option(float, description="The net cost of the strategy"),
    legs: discord.Option(str, description="The legs of the strategy in format: 'SPY240119C510,SPY240119P500,...'"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    """Open a new options strategy trade."""
    await kill_interaction(interaction)
    try:
        # Parse legs
        leg_list = []
        for leg in legs.split(','):
            parsed = parse_option_symbol(leg.strip())
            leg_list.append({
                'symbol': parsed['symbol'],
                'strike': parsed['strike'],
                'expiration_date': parsed['expiration_date'],
                'option_type': parsed['option_type'],
                'size': size,  # Each leg has the same size
                'net_cost': net_cost  # Total net cost of the strategy
            })

        # Determine trade group based on the first leg's expiration
        trade_group = await determine_trade_group(
            leg_list[0]['expiration_date'].strftime("%m/%d/%y"),
            "BTO",  # Default to BTO for options strategies
            underlying_symbol
        )

        # Get configuration for trade group
        config = await get_configuration(trade_group)
        if not config:
            await interaction.followup.send(f"No configuration found for trade group {trade_group}", ephemeral=True)
            return None

        # Create trade using Supabase edge function
        trade_data = await create_os_trade(
            strategy_name=strategy_name,
            underlying_symbol=underlying_symbol,
            net_cost=net_cost,
            size=size,
            legs=leg_list,
            configuration_id=config['id'],
            is_day_trade=(trade_group == TradeGroupEnum.DAY_TRADER),
            note=note
        )

        if trade_data:
            # Create and send embed
            embed = discord.Embed(title="New Options Strategy Created", color=discord.Color.green())
            embed.add_field(name="Trade ID", value=trade_data["trade_id"], inline=False)
            embed.add_field(name="Strategy", value=strategy_name, inline=True)
            embed.add_field(name="Symbol", value=underlying_symbol, inline=True)
            embed.add_field(name="Net Cost", value=f"${net_cost:,.2f}", inline=True)
            embed.add_field(name="Size", value=size, inline=True)
            
            # Add leg details
            for i, leg in enumerate(leg_list, 1):
                leg_str = (
                    f"{leg['symbol']} ${leg['strike']:,.2f} "
                    f"{leg['expiration_date'].strftime('%m/%d/%y')} {leg['option_type']}"
                )
                embed.add_field(name=f"Leg {i}", value=leg_str, inline=False)

            if note:
                embed.add_field(name="Note", value=note, inline=False)

            await interaction.followup.send(embed=embed)
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS command: Options strategy has been opened successfully.")

    except ValueError as e:
        await interaction.followup.send(f"Error parsing option symbols: {str(e)}", ephemeral=True)
        await log_to_channel(interaction.guild, f"Error in OS command by {interaction.user.name}: {str(e)}")
    except Exception as e:
        logger.error(f"Error in os_trade command: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.followup.send(f"Error creating options strategy: {str(e)}", ephemeral=True)
        await log_to_channel(interaction.guild, f"Error in OS command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="os_add", description="Add to an existing options strategy trade")
async def os_add(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the options strategy trade to add to", autocomplete=get_open_os_trade_ids),
    net_cost: discord.Option(float, description="The net cost of the addition"),
    size: discord.Option(str, description="The size to add"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    try:
        # Add to trade using Supabase function
        updated_trade = await add_to_os_trade(trade_id, net_cost, size, note)
        if not updated_trade:
            await interaction.followup.send(f"Trade {trade_id} not found.", ephemeral=True)
            return

        # Create embed
        embed = discord.Embed(title="Added to Options Strategy", color=discord.Color.blue())
        embed.add_field(name="Net Cost", value=f"${net_cost:.2f}", inline=True)
        embed.add_field(name="Added Size", value=format_size(size), inline=True)
        embed.add_field(name="New Size", value=format_size(updated_trade['current_size']), inline=True)
        embed.add_field(name="New Avg Cost", value=f"${float(updated_trade['average_net_cost']):.2f}", inline=True)
        if note:
            embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=f"Strategy ID: {trade_id}")

        # Send message to appropriate channel
        channel = interaction.guild.get_channel(int(updated_trade['channel_id']))
        role = interaction.guild.get_role(int(updated_trade['role_id']))
        await channel.send(content=f"{role.mention if role else ''}", embed=embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS_ADD command: Added to options strategy {trade_id} successfully.")

    except Exception as e:
        logger.error(f"Error adding to options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in OS_ADD command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="os_trim", description="Trim an existing options strategy trade")
async def os_trim(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the options strategy trade to trim", autocomplete=get_open_os_trade_ids),
    net_cost: discord.Option(float, description="The net cost of the trim"),
    size: discord.Option(str, description="The size to trim"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    try:
        # Trim trade using Supabase function
        updated_trade = await trim_os_trade(trade_id, net_cost, size, note)
        if not updated_trade:
            await interaction.followup.send(f"Trade {trade_id} not found.", ephemeral=True)
            return

        # Create embed
        embed = discord.Embed(title="Trimmed Options Strategy", color=discord.Color.yellow())
        embed.add_field(name="Net Cost", value=f"${net_cost:.2f}", inline=True)
        embed.add_field(name="Trimmed Size", value=format_size(size), inline=True)
        embed.add_field(name="New Size", value=format_size(updated_trade['current_size']), inline=True)
        embed.add_field(name="Avg Cost", value=f"${float(updated_trade['average_net_cost']):.2f}", inline=True)
        if note:
            embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=f"Strategy ID: {trade_id}")

        # Send message to appropriate channel
        channel = interaction.guild.get_channel(int(updated_trade['channel_id']))
        role = interaction.guild.get_role(int(updated_trade['role_id']))
        await channel.send(content=f"{role.mention if role else ''}", embed=embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS_TRIM command: Trimmed options strategy {trade_id} successfully.")

    except Exception as e:
        logger.error(f"Error trimming options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in OS_TRIM command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="os_exit", description="Exit an existing options strategy trade")
async def os_exit(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the options strategy trade to exit", autocomplete=get_open_os_trade_ids),
    net_cost: discord.Option(float, description="The net cost of the exit"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    try:
        # Exit trade using Supabase function
        updated_trade = await exit_os_trade(trade_id, net_cost, note)
        if not updated_trade:
            await interaction.followup.send(f"Trade {trade_id} not found.", ephemeral=True)
            return

        # Calculate P/L
        avg_entry_cost = float(updated_trade['average_net_cost'])
        avg_exit_cost = net_cost
        pl_per_contract = avg_exit_cost - avg_entry_cost

        # Create embed
        embed = discord.Embed(title="Exited Options Strategy", color=discord.Color.red())
        embed.add_field(name="Net Cost", value=f"${net_cost:.2f}", inline=True)
        embed.add_field(name="Exited Size", value=format_size(updated_trade['current_size']), inline=True)
        embed.add_field(name="Avg Entry Cost", value=f"${avg_entry_cost:.2f}", inline=True)
        embed.add_field(name="Avg Exit Cost", value=f"${avg_exit_cost:.2f}", inline=True)
        embed.add_field(name="P/L per Contract", value=f"${pl_per_contract:.2f}", inline=True)
        if note:
            embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=f"Strategy ID: {trade_id}")

        # Send message to appropriate channel
        channel = interaction.guild.get_channel(int(updated_trade['channel_id']))
        role = interaction.guild.get_role(int(updated_trade['role_id']))
        await channel.send(content=f"{role.mention if role else ''}", embed=embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS_EXIT command: Exited options strategy {trade_id} successfully.")

    except Exception as e:
        logger.error(f"Error exiting options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in OS_EXIT command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="os_note", description="Add a note to a trade")
async def add_os_note(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The trade to add the note to", autocomplete=get_open_os_trade_ids),
    note: discord.Option(str, description="The note to add")
):
    await kill_interaction(interaction)
    try:
        # Add note using Supabase function
        updated_trade = await add_note_to_os_trade(trade_id, note)
        if not updated_trade:
            await interaction.followup.send(f"Trade {trade_id} not found.", ephemeral=True)
            return

        # Create embed
        embed = discord.Embed(title="Trade Note", color=discord.Color.blue())
        embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=f"Posted by {interaction.user.name}")

        # Send message to appropriate channel
        channel = interaction.guild.get_channel(int(updated_trade['channel_id']))
        await channel.send(embed=embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_NOTE command: Note added to trade {trade_id}.")

    except Exception as e:
        logger.error(f"Error adding note to options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in ADD_NOTE command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="admin_reopen_trade", description="Reopen a trade")
async def admin_reopen_trade(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The trade to reopen")
):
    await kill_interaction(interaction)
    try:
        # Reopen trade using Supabase function
        updated_trade = await reopen_trade(trade_id)
        if not updated_trade:
            await interaction.followup.send(f"Trade {trade_id} not found.", ephemeral=True)
            return

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADMIN_REOPEN_TRADE command: Trade reopened.")

    except Exception as e:
        logger.error(f"Error reopening trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in ADMIN_REOPEN_TRADE command by {interaction.user.name}: {str(e)}")

# TODO: Add trade group rules to Supabase
async def determine_trade_group(expiration_date: str, trade_type: str, symbol: str) -> str:
    """Determine the trade group based on trade parameters."""
    if os.getenv("LOCAL_TEST", "false").lower() == "true":
        return TradeGroupEnum.DAY_TRADER
    
    try:
        # Get trade group configuration from Supabase
        config = await supabase.table('trade_group_rules').select('*').execute()
        if not config.data:
            return TradeGroupEnum.DAY_TRADER  # Default to day trader if no rules found

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

        return TradeGroupEnum.DAY_TRADER  # Default to day trader if no rules match

    except Exception as e:
        logger.error(f"Error determining trade group: {str(e)}")
        return TradeGroupEnum.DAY_TRADER  # Default to day trader on error

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

@bot.slash_command(name="help", description="List all available commands and their purposes")
async def help_command(interaction: discord.Interaction):
    """Display all available commands and their purposes."""
    await interaction.response.defer()

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
        
        await interaction.followup.send(embed=embed)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed HELP command.")

    except Exception as e:
        logger.error(f"Error in help command: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.followup.send("Error displaying help message. Please try again later.", ephemeral=True)
        await log_to_channel(interaction.guild, f"Error in HELP command by {interaction.user.name}: {str(e)}")




# ==================== DEPRECATED COMMANDS ====================
'''
@bot.slash_command(name="bto", description="Buy to open a new trade")
async def bto(
    interaction: discord.Interaction,
    symbol: discord.Option(str, description="The symbol of the security"),
    entry_price: discord.Option(float, description="The price at which the trade was opened"),
    size: discord.Option(str, description="The size of the trade"),
    expiration_date: discord.Option(str, description="The expiration date of the trade (MM/DD/YY)") = None,
    strike: discord.Option(float, description="The strike price of the trade") = None,
    option_type: discord.Option(str, description="The option type of the trade (C or P)") = None,
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await log_command_usage(interaction, "bto", {
        "symbol": symbol,
        "entry_price": entry_price,
        "size": size,
        "expiration_date": expiration_date,
        "strike": strike,
        "option_type": option_type,
        "note": note
    })
    await kill_interaction(interaction)
    try:
        response = await create_trade(
            interaction=interaction, 
            symbol=symbol, 
            entry_price=entry_price, 
            size=size, 
            trade_type="BTO", 
            expiration_date=expiration_date, 
            strike=strike, 
            option_type=option_type, 
            note=note
        )
        trade_data = response['trade']
        if trade_data:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed BTO command: Trade has been opened successfully.")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in BTO command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="sto", description="Open a new stock trade")
async def sto(
    interaction: discord.Interaction,
    symbol: str,
    entry_price: float,
    size: float,
    note: str = None,
):
    """Open a new stock trade"""
    await interaction.response.defer()

    try:
        # Create trade using Supabase edge function
        response = await create_trade(
            symbol=symbol, 
            trade_type="stock",
            entry_price=entry_price, 
            size=size, 
            note=note,
            config_name="day_trader"
        )
        trade_data = response['trade']
        # Create and send embed
        embed = discord.Embed(
            title=f"New Stock Trade Opened: {symbol}",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Entry Price", value=f"${entry_price:,.2f}", inline=True)
        embed.add_field(name="Size", value=f"{size:,.0f}", inline=True)
        if note:
            embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=f"Trade ID: {trade_data['trade_id']}")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logging.error(f"Error in sto command: {str(e)}")
        await interaction.followup.send('''

@bot.slash_command(name="add_role_to_users", description="Add a role to all users who have a specific role")
async def add_role_to_users(
    interaction: discord.Interaction,
    role_to_add: discord.Option(discord.Role, description="The role to add to users"),
    required_role: discord.Option(discord.Role, description="The role that users must have")
):
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild = interaction.guild
        members = guild.fetch_members(limit=None)
        
        added_count = 0
        already_had_count = 0
        total_processed = 0
        
        async for member in members:
            if required_role in member.roles:
                if role_to_add not in member.roles:
                    await member.add_roles(role_to_add)
                    added_count += 1
                else:
                    already_had_count += 1
            total_processed += 1
            if total_processed % 20 == 0:
                print(f"Processed {total_processed} members")
        total_affected = added_count + already_had_count
        
        await interaction.followup.send(
            f"Role addition complete:\n"
            f"- {added_count} users were given the {role_to_add.name} role\n"
            f"- {already_had_count} users already had the role\n"
            f"- {total_affected} total users with the {required_role.name} role",
            ephemeral=True
        )
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_ROLE_TO_USERS command: Role addition complete.")
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to add roles to users.", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_ROLE_TO_USERS command: I don't have permission to add roles to users.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in ADD_ROLE_TO_USERS command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)

@bot.slash_command(name="send_embed", description="Send an embed with optional file attachment")
async def send_embed(
    interaction: discord.Interaction,
    title: discord.Option(str, description="The title of the embed"),
    description: discord.Option(str, description="The description/content of the embed (use \\n for new lines)"),
    channel: discord.Option(discord.TextChannel, description="The channel to send the embed to"),
    file: discord.Option(discord.Attachment, description="File to attach to the embed", required=False) = None
):
    await kill_interaction(interaction)
    
    try:
        # Replace '\\n' with actual new lines
        formatted_description = description.replace('\\n', '\n')
        embed = discord.Embed(title=title, description=formatted_description, color=discord.Color.blue())
        
        if file:
            file_data = await file.read()
            discord_file = discord.File(io.BytesIO(file_data), filename=file.filename)
            embed.set_image(url=f"attachment://{file.filename}")
            await channel.send(embed=embed, file=discord_file)
        else:
            await channel.send(embed=embed)
        
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed SEND_EMBED command: Embed sent successfully!")
    except Exception as e:
        logger.error(f"Error in send_embed: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in SEND_EMBED command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)


@bot.slash_command(name="unsync_resync", description="Unsync and resync commands")
async def unsync_resync(ctx, guild_id: int = None):
    if guild_id:
        guild = discord.Object(id=guild_id)
    else:
        guild = ctx.guild

    await ctx.respond("Unsyncing commands...", ephemeral=True)
    await bot.sync_commands(commands=[], guild_ids=[guild.id])
    await ctx.send("Commands unsynced.", ephemeral=True)

    await ctx.send("Resyncing commands...", ephemeral=True)
    synced = await bot.sync_commands(guild=guild)
    await ctx.send(f"Resynced {len(synced)} commands.", ephemeral=True)


@bot.slash_command(name="transaction_send", description="Send a transaction message")
async def transaction_send(interaction: discord.Interaction, transaction_id: discord.Option(str, description="The transaction to send")):
    await kill_interaction(interaction)
    db = next(get_db())
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transaction:
        await interaction.response.send_message("Transaction not found.", ephemeral=True)
        return
    
    trade = db.query(models.Trade).filter(models.Trade.trade_id == transaction.trade_id).first()
    if not trade:
        await interaction.response.send_message("Trade not found.", ephemeral=True)
        return
    
    config = get_configuration(db, trade.configuration.name)
    if not config:
        await interaction.response.send_message("No configuration found for this trade group.", ephemeral=True)
        return
    
    if transaction.transaction_type == "open":  
        await post_update(interaction, trade.trade_group, f"Open {transaction.transaction_id}")
    elif transaction.transaction_type == "close":
        await post_update(interaction, trade.trade_group, f"Close {transaction.transaction_id}")
    elif transaction.transaction_type == TransactionTypeEnum.CLOSE:
        # Create an embed with the closed trade information
        embed = discord.Embed(title="Trade Closed", color=discord.Color.gold())

        unit_type = "contract" if trade.is_contract else "share"

        profit_loss_per_unit = trade.average_price - transaction.amount
        
        # Add the one-liner at the top of the embed
        embed.description = create_trade_oneliner(trade)
        
        embed.add_field(name="Exit Price", value=f"${transaction.amount:.2f}", inline=True)
        embed.add_field(name="Exit Size", value=format_size(transaction.size), inline=True)
        embed.add_field(name=f"Trade P/L per {unit_type}", value=f"${profit_loss_per_unit:.2f}", inline=True)
        embed.add_field(name="Avg Entry Price", value=f"${trade.average_price:.2f}", inline=True)
        if trade.average_exit_price:
            embed.add_field(name="Avg Exit Price", value=f"${trade.average_exit_price:.2f}", inline=True)
        else:
            embed.add_field(name="Avg Exit Price", value=f"${transaction.amount:.2f}", inline=True)
        embed.add_field(name="Result", value=trade.win_loss.value.capitalize(), inline=True)

        # Set the footer to include the trade ID
        embed.set_footer(text=f"Trade ID: {trade.trade_id}")

        channel = interaction.guild.get_channel(int(config.channel_id))
        await channel.send(embed=embed)


@bot.slash_command(name="note", description="Add a note to a trade")
async def add_note(interaction: discord.Interaction, trade_id: discord.Option(str, description="The trade to add the note to", autocomplete=discord.utils.basic_autocomplete(get_open_trade_ids)), note: discord.Option(str, description="The note to add")):
    await kill_interaction(interaction)
    db = next(get_db())
    trade = db.query(models.Trade).filter(models.Trade.trade_id == trade_id).first()
    if not trade:
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_NOTE command: Trade not found.")
        return
    
    config = get_configuration(db, trade.configuration.name)
    if not config:
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_NOTE command: No configuration found for trade group: {trade.configuration.name}")
        return
    
    channel = interaction.guild.get_channel(int(config.channel_id))
    embed = discord.Embed(title="Trade Note", description=note, color=discord.Color.blue())
    embed.description = create_trade_oneliner(trade)
    embed.add_field(name="Note", value=note, inline=False)
    embed.set_footer(text=f"Posted by {interaction.user.name}")
    await channel.send(embed=embed)

    await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_NOTE command: Note added to trade {trade_id}.")

@bot.slash_command(name="os_note", description="Add a note to a trade")
async def add_os_note(interaction: discord.Interaction, trade_id: discord.Option(str, description="The trade to add the note to", autocomplete=discord.utils.basic_autocomplete(get_open_os_trade_ids)), note: discord.Option(str, description="The note to add")):
    await kill_interaction(interaction)
    db = next(get_db())
    trade = db.query(models.OptionsStrategyTrade).filter(models.OptionsStrategyTrade.trade_id == trade_id).first()
    if not trade:
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_NOTE command: Trade not found.")
        return
    
    config = get_configuration(db, trade.configuration.name)
    if not config:
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_NOTE command: No configuration found for trade group: {trade.configuration.name}")
        return
    
    channel = interaction.guild.get_channel(int(config.channel_id))
    embed = discord.Embed(title="Trade Note", description=note, color=discord.Color.blue())
    embed.description = create_trade_oneliner_os(trade)
    embed.add_field(name="Note", value=note, inline=False)
    embed.set_footer(text=f"Posted by {interaction.user.name}")
    await channel.send(embed=embed)

    await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD_NOTE command: Note added to trade {trade_id}.")

@bot.slash_command(name="admin_reopen_trade", description="Reopen a trade")
async def admin_reopen_trade(interaction: discord.Interaction, trade_id: discord.Option(str, description="The trade to reopen")):
    await kill_interaction(interaction)
    db = next(get_db())
    trade = db.query(models.Trade).filter(models.Trade.trade_id == trade_id).first()
    if not trade:
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADMIN_REOPEN_TRADE command: Trade not found.")
        return
    
    trade.status = "open"
    db.commit()

    await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADMIN_REOPEN_TRADE command: Trade reopened.")


ACCESS_ROLES = ['Full Access', 'Day Trader', 'Swing Trader', 'Long Term Trader']
LOST_ACCESS = ['@everyone', 'BD-Verified']
JOINED_ROLES = ['@everyone', 'Full Access', 'Day Trader', 'Swing Trader', 'Long Term Trader'] 

# if after roles are ['@everyone', 'BD-Verified']
@bot.event
async def on_member_update(before, after):
    print(f"Member updated: {after.name} (ID: {after.id})")
    logger.info(f"Member updated: {after.name} (ID: {after.id})")
    if before.roles != after.roles:
        print(f"Roles changed for {after.name}")
        print(f"Before: {[role.name for role in before.roles]}")
        print(f"After: {[role.name for role in after.roles]}")
    
    if after.roles == LOST_ACCESS:
        try:    
            await after.remove_roles(after.guild.get_role(1283500210127110267))
        except Exception as e:
            print(f"Error removing BD-Verified role from {after.name}: {e}")

    if after.roles == JOINED_ROLES:
        try:
            await after.add_roles(after.guild.get_role(1283500418013593762))
        except Exception as e:
            print(f"Error adding BD-Verified role to {after.name}: {e}")
    
    # if roles are ['@everyone', 'BD-Verified'] then remove BD-Verified
    # Can also do the if no verification role and one of the access roles, then add unverified role here



