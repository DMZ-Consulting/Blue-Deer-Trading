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
from discord import AutocompleteContext, ButtonStyle, OptionChoice
from discord.errors import HTTPException
from discord.ext import commands, tasks
from discord.ui import Button, View
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from . import crud, models, schemas
from .database import SessionLocal, get_db, engine
from .models import create_tables  # Add this import
from .models import TransactionTypeEnum

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

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
        # Run the update_expiration_dates function before starting the bot
        # update_expiration_dates()

        await bot.start(token)
    except Exception as e:
        logger.error(f"Failed to start the bot: {str(e)}")
        raise

@bot.event
async def on_ready():
    global last_sync_time
    print(f'{bot.user} has connected to Discord!')
    create_tables(engine)
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

async def sync_commands_with_backoff(guild, max_retries=5, base_delay=1):
    for attempt in range(max_retries):
        try:
            synced = await bot.sync_commands(guild_ids=[guild.id])
            if synced:
                print(f"Synced {len(synced)} command(s) to the guild with ID {guild.id}.")
            else:
                print(f"No commands were synced to the guild with ID {guild.id}.")
            return
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limit error
                delay = base_delay * (2 ** attempt)
                print(f"Rate limited. Retrying in {delay} seconds.")
                await asyncio.sleep(delay)
            else:
                raise
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

class TradePaginator(View):
    def __init__(self, trades, interaction):
        super().__init__(timeout=180)
        self.trades = trades
        self.interaction = interaction
        self.current_page = 0
        self.items_per_page = 10  # Changed to 1 to show one trade per page with its transactions

        self.prev_button = Button(label="Previous", style=discord.ButtonStyle.primary)
        self.next_button = Button(label="Next", style=discord.ButtonStyle.primary)
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def send_page(self):
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        trades_page = self.trades[start:end]

        embed = discord.Embed(title="Open Trades", color=discord.Color.blue())
        for trade in trades_page:
            entry_price = f"${trade.entry_price:,.2f}" if trade.entry_price >= 0 else f"(${abs(trade.entry_price):,.2f})"
            embed.add_field(
                name=f"Trade ID: {trade.trade_id}",
                value=f"Symbol: {trade.symbol}\nType: {trade.trade_type}\nEntry Price: {entry_price}\nCurrent Size: {format_size(trade.current_size)}",
                inline=False
            )
            
            # Add transactions for this trade
            transactions = crud.get_transactions_for_trade(next(get_db()), trade.trade_id)
            if transactions:
                transaction_text = "\n".join([f"{t.transaction_type.value}: {format_size(t.size)} @ ${t.amount:,.2f}" if t.amount >= 0 else f"{t.transaction_type.value}: {format_size(t.size)} @ (${abs(t.amount):,.2f}) at {t.created_at.strftime('%Y-%m-%d %H:%M:%S')}" for t in transactions])
                embed.add_field(name="Transactions", value=transaction_text, inline=False)
            else:
                embed.add_field(name="Transactions", value="No transactions", inline=False)

        if self.current_page == 0:
            self.prev_button.disabled = True
        else:
            self.prev_button.disabled = False

        if end >= len(self.trades):
            self.next_button.disabled = True
        else:
            self.next_button.disabled = False

        if hasattr(self, 'last_message'):
            await self.last_message.delete()

        self.last_message = await self.interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def prev_page(self, interaction):
        self.current_page -= 1
        await self.send_page()

    async def next_page(self, interaction):
        self.current_page += 1
        await self.send_page()

@tasks.loop(minutes=2)
async def check_and_update_roles():
    """
    This function checks the roles of all members in the guild and updates them based on the role requirements and conditional role grants.
    It also logs the actions taken in the specified log channel.
    """
    for guild in bot.guilds:
        if guild.id != 1055255055474905139: # Blue Deer Server, only do this here. 
            continue
            
            db = next(get_db())
            try:
                # Check role requirements
                role_requirements = db.query(models.RoleRequirement).filter_by(guild_id=str(guild.id)).all()
                for requirement in role_requirements:
                    required_role_ids = [role.role_id for role in requirement.required_roles]
                    members = guild.fetch_members(limit=None)
                    async for member in members:
                        if not any(role.id in required_role_ids for role in member.roles):
                            await member.remove_roles(*member.roles, reason="Does not meet role requirements")
                            await log_action(guild, f"Removed roles from {member.name} (ID: {member.id}) due to not meeting role requirements")

                # Check conditional role grants
                conditional_grants = db.query(models.ConditionalRoleGrant).filter_by(guild_id=str(guild.id)).all()
                for grant in conditional_grants:
                    condition_role_ids = [role.role_id for role in grant.condition_roles]
                    grant_role = guild.get_role(int(grant.grant_role_id))
                    exclude_role = guild.get_role(int(grant.exclude_role_id)) if grant.exclude_role_id else None
                    
                    members = guild.fetch_members(limit=None)
                    async for member in members:
                        if any(role.id in condition_role_ids for role in member.roles) and (not exclude_role or exclude_role not in member.roles):
                            await member.add_roles(grant_role, reason="Meets conditional role grant requirements")
                            await log_action(guild, f"Added role {grant_role.name} to {member.name} (ID: {member.id}) due to meeting conditional role grant requirements")
            finally:
                db.close()

async def log_action(guild, message):
    db = next(get_db())
    try:
        verification_config = db.query(models.VerificationConfig).filter_by(guild_id=str(guild.id)).first()
        if verification_config and verification_config.log_channel_id:
            log_channel = guild.get_channel(int(verification_config.log_channel_id))
            if log_channel:
                await log_channel.send(message)
    finally:
        db.close()

@tasks.loop(time=time(hour=23, minute=45))
async def check_and_exit_expired_trades():
    db = next(get_db())
    try:
        today = date.today()
        open_trades = crud.get_trades(db, status=models.TradeStatusEnum.OPEN)
        
        for trade in open_trades:
            if trade.expiration_date and trade.expiration_date.date() <= today:
                await exit_expired_trade(trade)
        
    except Exception as e:
        logger.error(f"Error in check_and_exit_expired_trades: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        db.close()


# TODO: This is a mess. Need to refactor. the trade is changed to closed but not being committed for some reason.
async def exit_expired_trade(trade):
    db = next(get_db())
    try:
        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.id == trade.configuration_id).first()
        if not config:
            logger.error(f"Configuration for trade {trade.trade_id} not found.")
            return

        # Set exit price to max loss
        exit_price = 0 if trade.trade_type.lower() in ["long", "buy to open"] else trade.strike * 2

        trade.status = models.TradeStatusEnum.CLOSED
        trade.exit_price = exit_price
        trade.closed_at = datetime.now()
        
        current_size = Decimal(trade.current_size)
        
        new_transaction = models.Transaction(
            trade_id=trade.trade_id,
            transaction_type=models.TransactionTypeEnum.CLOSE,
            amount=exit_price,
            size=str(current_size),
            created_at=datetime.now()
        )
        db.add(new_transaction)

        # Calculate profit/loss
        open_transactions = crud.get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
        trim_transactions = crud.get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.TRIM])
        
        total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
        total_open_size = sum(Decimal(t.size) for t in open_transactions)
        
        average_cost = total_cost / total_open_size if total_open_size > 0 else 0
        
        trim_profit_loss = 0
        if trim_transactions:
            trim_profit_loss = sum((Decimal(t.amount) - average_cost) * Decimal(t.size) for t in trim_transactions)
        exit_profit_loss = (Decimal(exit_price) - average_cost) * current_size
        
        total_profit_loss = trim_profit_loss + exit_profit_loss
        trade.profit_loss = float(total_profit_loss)

        # Determine win/loss
        trade.win_loss = models.WinLossEnum.LOSS

        db.commit()

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

@bot.slash_command(name="setup_verification", description="Set up a verification message with terms and conditions")
async def setup_verification(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    terms: str,
    role_to_remove: discord.Role,
    role_to_add: discord.Role,
    log_channel: discord.TextChannel,
):
    await log_command_usage(interaction, "setup_verification", {
        "channel": channel.name,
        "terms": terms,
        "role_to_remove": role_to_remove.name,
        "role_to_add": role_to_add.name,
        "log_channel": log_channel.name
    })
    print("setup_verification called")
    # Kill the response immediately
    await interaction.response.defer(ephemeral=True)
    
    db = next(get_db())
    try:
        embed = discord.Embed(title="Verification", description=terms, color=discord.Color.blue())
        button = discord.ui.Button(style=ButtonStyle.green, label="Accept Terms", custom_id="verify")
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
    print("on_interaction called")
    try:
        if interaction.type == discord.InteractionType.component:
            print("interaction.type == discord.InteractionType.component", interaction.data)
            if interaction.data["custom_id"] == "verify":
                await handle_verification(interaction)
                return
        # Add this else block to allow other interactions to be processed normally
        
        await bot.process_application_commands(interaction)
    except Exception as e:
        logger.error(f"Error in on_interaction: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)

async def handle_verification(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    db = next(get_db())
    try:
        config = db.query(models.VerificationConfig).filter_by(message_id=str(interaction.message.id)).first()
        if not config:
            await interaction.followup.send("Verification configuration not found.", ephemeral=True)
            return

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
        await log_channel.send(embed=log_embed)

        new_verification = models.Verification(
            user_id=str(interaction.user.id),
            username=str(interaction.user.name),
            timestamp=datetime.utcnow(),
            configuration_id=config.id
        )
        db.add(new_verification)
        db.commit()

        await interaction.followup.send("You have been verified!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in handle_verification: {str(e)}")
        logger.error(traceback.format_exc())
        await interaction.followup.send(f"An error occurred during verification: {str(e)}", ephemeral=True)
    finally:
        db.close()

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
                display = f"{symbol} COMMON OPENED: {trade.created_at.strftime('%m/%d/%y')}"
                sort_key = (symbol, datetime.max, 0)  # Put non-option trades at the bottom of their symbol group
            
            trade_info.append((trade.trade_id, display, sort_key))
        
        # Sort the trades
        sorted_trades = sorted(trade_info, key=lambda x: x[2])
        
        # Create OptionChoice objects
        return [discord.OptionChoice(name=f"{display} (ID: {trade_id})", value=trade_id) for trade_id, display, _ in sorted_trades]
    finally:
        db.close()

async def get_open_os_trade_ids(ctx: discord.AutocompleteContext):
    db = next(get_db())
    try:
        open_trades = crud.get_os_trades(db, status=models.OptionsStrategyStatusEnum.OPEN)
        
        # Format trade information
        trade_info = []
        for trade in open_trades:
            symbol = trade.underlying_symbol
            name = trade.name

            display = f"{symbol} - {name}"
            sort_key = (symbol, name)
            
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

def determine_trade_group(expiration_date: str, trade_type: str) -> str:
    print("determine_trade_group called")
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
    else:
        print(f"Returning SWING_TRADER for {expiration_date}")
        return TradeGroupEnum.SWING_TRADER

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

def create_trade_oneliner(trade):
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

    size = trade.current_size if trade.current_size else trade.size
    entry_price = f"${trade.entry_price:.2f}"
    
    if trade.is_contract:
        expiration = convert_to_two_digit_year(trade.expiration_date.strftime('%m/%d/%y')) if trade.expiration_date else "No Exp"
        strike = f"${trade.strike:.2f}"
        return f"### {expiration} {trade.symbol} {strike} {option_type}"# @ {entry_price} {size} size"
    else:
        return f"### {trade.symbol} @ {entry_price} {size} risk"
    
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
        return f"### {type} {trade.symbol} @ {trade.entry_price:.2f} {size} {risk_identifier}"
    
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

@bot.slash_command(name="os", description="Create an options strategy trade")
async def options_strategy(
    interaction: discord.Interaction,
    strategy_name: discord.Option(str, description="The name of the options strategy"),
    size: discord.Option(str, description="The size of the trade"),
    net_cost: discord.Option(float, description="The net cost of the strategy"),
    legs: discord.Option(str, description="Format: [+/-].SYMBOL[W]YYMMDDX0000,PRICE,SIZE;[+/-].SYMBOL[W]YYMMDDX0000,PRICE,SIZE;..."),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await log_command_usage(interaction, "os", {
        "strategy_name": strategy_name,
        "size": size,
        "net_cost": net_cost,
        "legs": legs,
        "note": note
    })
    await kill_interaction(interaction)

    db = next(get_db())
    try:
        parsed_legs = []
        underlying_symbol = None

        leg_symbols = re.findall(r'[+-]?\.?[A-Z]+\d+[CP]\d+', legs)
        for symbol in leg_symbols:
            parsed = parse_option_symbol(symbol)
            parsed['size'] = size
            parsed_legs.append(parsed)

            if not underlying_symbol:
                underlying_symbol = parsed['symbol']
            elif parsed['symbol'] != underlying_symbol:
                raise ValueError("All legs must have the same underlying symbol")

        trade_group = determine_trade_group(parsed_legs[0]['expiration_date'].strftime('%m/%d/%y'), "os")
        config = get_configuration(db, trade_group)

        if not config:
            await log_to_channel(interaction.guild, f"No configuration found for trade group: {trade_group}")
            return

        new_strategy = models.OptionsStrategyTrade(
            name=strategy_name,
            underlying_symbol=underlying_symbol,
            status=models.OptionsStrategyStatusEnum.OPEN,
            configuration_id=config.id,
            trade_group=trade_group,
            legs=serialize_legs(parsed_legs),  # Use the new serialize_legs function
            net_cost=net_cost,
            average_net_cost=net_cost,
            size=size,
            current_size=size
        )

        db.add(new_strategy)
        db.commit()
        db.refresh(new_strategy)

        # Add the initial open transaction
        open_transaction = models.OptionsStrategyTransaction(
            strategy_id=new_strategy.id,
            transaction_type=models.TransactionTypeEnum.OPEN,
            net_cost=net_cost,
            size=size
        )
        db.add(open_transaction)
        db.commit()

        # Create an embed with the strategy trade information
        embed = discord.Embed(title=f"New Options Strategy: {strategy_name}", color=discord.Color.blue())
        embed.add_field(name="Underlying Symbol", value=underlying_symbol, inline=True)
        embed.add_field(name="Net Cost", value=f"${net_cost:.2f}", inline=True)
        embed.add_field(name="Size", value=size, inline=True)

        for i, leg in enumerate(parsed_legs, 1):
            leg_info = f"{leg['trade_type']} {leg['size']} {leg['symbol']} {leg['strike']} {leg['option_type']} {leg['expiration_date'].strftime('%m/%d/%y')}"
            embed.add_field(name=f"Leg {i}", value=leg_info, inline=False)

        if note:
            embed.add_field(name="Note", value=note, inline=False)

        embed.set_footer(text=f"Strategy ID: {new_strategy.trade_id}")

        print(f"Sending message to channel {config.channel_id}")
        print(f"config {config}")
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS command: Options strategy {strategy_name} created successfully.")

    except Exception as e:
        logger.error(f"Error creating options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in OS command by {interaction.user.name}: {str(e)}")
    finally:
        db.close()

"""def create_trade_oneliner_os(os_trade):
    add_date = True
    trade_oneliner = f"{os_trade.underlying_symbol} - {os_trade.name} "
    for leg in os_trade.legs:
        leg_parsed = parse_option_symbol(leg)

        if add_date:
            trade_oneliner += f" ({leg_parsed['expiration_date']})"
            add_date = False
        else:
            if leg_parsed['option_type'] == "C":
                trade_oneliner += "+"
            else:
                trade_oneliner += "-"
        
        trade_oneliner += f"{leg_parsed['strike']}{leg_parsed['option_type']}"

    return trade_oneliner
"""

async def create_trade(
    interaction: discord.Interaction,
    symbol: str,
    entry_price: float,
    size: str,
    trade_type: str,
    expiration_date: str = None,
    strike: float = None,
    option_type: str = None,
    trade_group: str = None,
    note: str = None,
    suppress_embed: bool = False
):
    db = next(get_db())
    try:
        if expiration_date:
            expiration_date = convert_to_two_digit_year(expiration_date)
        
        if not trade_group:
            trade_group = determine_trade_group(expiration_date, trade_type.lower())
        
        config = get_configuration(db, trade_group)
        if not config:
            await log_to_channel(interaction.guild, f"No configuration found for trade group: {trade_group}")
            return

        is_contract = expiration_date is not None
        is_day_trade = False
        if is_contract:
            try:
                exp_date = datetime.strptime(expiration_date, "%m/%d/%y")
                is_day_trade = (exp_date - datetime.now()).days < 7
            except ValueError:
                await log_to_channel(interaction.guild, "Invalid expiration date format. Please use MM/DD/YY.")
                return

        new_trade = models.Trade(
            symbol=symbol.upper(),
            trade_type=trade_type,
            status=models.TradeStatusEnum.OPEN,
            entry_price=entry_price,
            average_price=entry_price,
            size=size,
            current_size=size,
            created_at=datetime.utcnow(),
            closed_at=None,
            exit_price=None,
            average_exit_price=None,
            profit_loss=None,
            risk_reward_ratio=None,
            win_loss=None,
            configuration_id=config.id,
            is_contract=is_contract,
            is_day_trade=is_day_trade,
            strike=strike,
            expiration_date=datetime.strptime(expiration_date, "%m/%d/%y") if expiration_date else None,
            option_type=option_type.upper() if option_type else None
        )
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)

        open_transaction = models.Transaction(
            trade_id=new_trade.trade_id,
            transaction_type=models.TransactionTypeEnum.OPEN,
            amount=entry_price,
            size=size,
            created_at=datetime.now()
        )
        db.add(open_transaction)
        db.commit()

        if not suppress_embed:
            embed_color = discord.Color.green() if trade_type == "BTO" else discord.Color.red()
            embed = discord.Embed(title="New Trade Opened", color=embed_color)
            embed.description = create_trade_oneliner(new_trade)
            
            embed.add_field(name="Symbol", value=symbol, inline=True)
            embed.add_field(name="Trade Type", value=trade_type, inline=True)
            entry_price_display = f"${entry_price:.2f}" if entry_price >= 0 else f"(${abs(entry_price):,.2f})"
            embed.add_field(name="Entry Price", value=entry_price_display, inline=True)
            embed.add_field(name="Risk Level (1-6)", value=size, inline=True)
            if expiration_date:
                embed.add_field(name="Exp. Date", value=expiration_date, inline=True)
            if strike:
                strike_display = f"${strike:.2f}" if strike >= 0 else f"(${abs(strike):,.2f})"
                embed.add_field(name="Strike Price", value=strike_display, inline=True)
            if option_type:
                embed.add_field(name="Option Type", value=option_type, inline=True)
            embed.set_footer(text=f"Trade ID: {new_trade.trade_id}")

            channel = interaction.guild.get_channel(int(config.channel_id))
            role = interaction.guild.get_role(int(config.role_id))
            await channel.send(content=f"{role.mention}", embed=embed)

            if note:
                note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey())
                await channel.send(embed=note_embed)

        return new_trade
    finally:
        db.close()

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
        new_trade = await create_trade(
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
        if new_trade:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed BTO command: Trade has been opened successfully.")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in BTO command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="sto", description="Sell to open a new trade")
async def sto(
    interaction: discord.Interaction,
    symbol: discord.Option(str, description="The symbol of the security"),
    entry_price: discord.Option(float, description="The price at which the trade was opened"),
    size: discord.Option(str, description="The size of the trade"),
    expiration_date: discord.Option(str, description="The expiration date of the trade (MM/DD/YY)") = None,
    strike: discord.Option(float, description="The strike price of the trade") = None,
    option_type: discord.Option(str, description="The option type of the trade (C or P)") = None,
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "sto", {
        "symbol": symbol,
        "entry_price": entry_price,
        "size": size,
        "expiration_date": expiration_date,
        "strike": strike,
        "option_type": option_type,
        "note": note
    })
    try:
        new_trade = await create_trade(
            interaction=interaction, 
            symbol=symbol, 
            entry_price=entry_price, 
            size=size, 
            trade_type="STO", 
            expiration_date=expiration_date, 
            strike=strike, 
            option_type=option_type, 
            note=note
        )
        if new_trade:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed STO command: Trade has been opened successfully.")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in STO command by {interaction.user.name}: {str(e)}")

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
async def long_term_trade(
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
    filename: discord.Option(str, description="The filename to save the scraped data (e.g., 'output.txt')")
):
    await log_command_usage(interaction, "scrape_channel", {
        "channel": channel.name,
        "filename": filename
    })
    await interaction.response.defer(ephemeral=True)
    
    try:
        message_count = 0
        async with aiofiles.open(filename, mode='w', encoding='utf-8') as file:
            async for message in channel.history(limit=None):
                content = message.content.strip()
                
                # Handle embeds
                for embed in message.embeds:
                    if embed.description:
                        content += f" {embed.description.strip()}"
                    for field in embed.fields:
                        content += f" {field.name}: {field.value}"
                
                if content:
                    # Format the date and time
                    date_time = message.created_at.strftime("%m/%d/%y %H:%M:%S")
                    author = message.author.name
                    
                    # Write the formatted message
                    await file.write(f"{date_time} - {author} - {content}\n")
                    message_count += 1
                
                if message_count % 1000 == 0:
                    await interaction.followup.send(f"Processed {message_count} messages...", ephemeral=True)
        
        await interaction.followup.send(f"Scraping complete. {message_count} messages saved to {filename}", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed SCRAPE_CHANNEL command: {message_count} messages scraped from {channel.name} and saved to {filename}")
    
    except HTTPException as e:
        error_message = f"Discord API error: {str(e)}"
        await interaction.followup.send(error_message, ephemeral=True)
        await log_to_channel(interaction.guild, f"Error in SCRAPE_CHANNEL command by {interaction.user.name}: {error_message}")
    
    except Exception as e:
        error_message = f"An error occurred while scraping the channel: {str(e)}"
        await interaction.followup.send(error_message, ephemeral=True)
        await log_to_channel(interaction.guild, f"Error in SCRAPE_CHANNEL command by {interaction.user.name}: {error_message}")
        logger.error(f"Error in scrape_channel: {str(e)}")
        logger.error(traceback.format_exc())


async def get_verification_log_channel(guild):
    db = next(get_db())
    try:
        verification_config = db.query(models.VerificationConfig).first()
        if verification_config and verification_config.log_channel_id:
            return guild.get_channel(int(verification_config.log_channel_id))
    finally:
        db.close()
    return None

async def log_to_channel(guild, message):
    log_channel = await get_verification_log_channel(guild)
    if log_channel:
        await log_channel.send(message)
    else:
        print(f"Warning: Verification log channel not found. Message: {message}")


# ================= Options Strategy Functions =================

@bot.slash_command(name="os_add", description="Add to an existing options strategy trade")
async def os_add(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the options strategy trade to add to", autocomplete=discord.utils.basic_autocomplete(get_open_os_trade_ids)),
    net_cost: discord.Option(float, description="The net cost of the addition"),
    size: discord.Option(str, description="The size to add"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "os_add", {
        "trade_id": trade_id,
        "net_cost": net_cost,
        "size": size,
        "note": note
    })

    db = next(get_db())
    try:
        strategy = db.query(models.OptionsStrategyTrade).filter_by(trade_id=trade_id).first()
        if not strategy:
            await log_to_channel(interaction.guild, f"Options strategy trade {trade_id} not found.")
            return

        new_transaction = models.OptionsStrategyTransaction(
            strategy_id=strategy.id,
            transaction_type=models.TransactionTypeEnum.ADD,
            net_cost=net_cost,
            size=size
        )
        db.add(new_transaction)

        strategy.current_size = str(float(strategy.current_size) + float(size))
        strategy.average_net_cost = ((float(strategy.average_net_cost) * float(strategy.current_size)) + (float(net_cost) * float(size))) / (float(strategy.current_size) + float(size))
        db.commit()

        embed = discord.Embed(title=f"Added to Options Strategy: {strategy.name}", color=discord.Color.green())
        embed.description = create_trade_oneliner_os(strategy)
        embed.add_field(name="Net Cost", value=f"${net_cost:.2f}", inline=True)
        embed.add_field(name="Added Size", value=size, inline=True)
        embed.add_field(name="New Total Size", value=strategy.current_size, inline=True)
        embed.add_field(name="Average Net Cost", value=f"${strategy.average_net_cost:.2f}", inline=True)
        if note:
            embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=f"Strategy ID: {strategy.trade_id}")

        config = db.query(models.TradeConfiguration).filter_by(id=strategy.configuration_id).first()
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS_ADD command: Added to options strategy {trade_id} successfully.")

    except Exception as e:
        logger.error(f"Error adding to options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in OS_ADD command by {interaction.user.name}: {str(e)}")
    finally:
        db.close()

@bot.slash_command(name="os_trim", description="Trim an existing options strategy trade")
async def os_trim(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the options strategy trade to add to", autocomplete=discord.utils.basic_autocomplete(get_open_os_trade_ids)),
    net_cost: discord.Option(float, description="The net cost of the trim"),
    size: discord.Option(str, description="The size to trim"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "os_trim", {
        "trade_id": trade_id,
        "net_cost": net_cost,
        "size": size,
        "note": note
    })

    db = next(get_db())
    try:
        strategy = db.query(models.OptionsStrategyTrade).filter_by(trade_id=trade_id).first()
        if not strategy:
            await log_to_channel(interaction.guild, f"Options strategy trade {trade_id} not found.")
            return

        if float(size) > float(strategy.current_size):
            await log_to_channel(interaction.guild, f"Trim size ({size}) is greater than current strategy size ({strategy.current_size}).")
            return

        new_transaction = models.OptionsStrategyTransaction(
            strategy_id=strategy.id,
            transaction_type=models.TransactionTypeEnum.TRIM,
            net_cost=net_cost,
            size=size
        )
        db.add(new_transaction)

        strategy.current_size = str(float(strategy.current_size) - float(size))
        db.commit()

        embed = discord.Embed(title=f"Trimmed Options Strategy: {strategy.name}", color=discord.Color.orange())
        embed.description = create_trade_oneliner_os(strategy)
        embed.add_field(name="Net Cost", value=f"${net_cost:.2f}", inline=True)
        embed.add_field(name="Trimmed Size", value=size, inline=True)
        embed.add_field(name="Remaining Size", value=strategy.current_size, inline=True)
        if note:
            embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=f"Strategy ID: {strategy.trade_id}")

        config = db.query(models.TradeConfiguration).filter_by(id=strategy.configuration_id).first()
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS_TRIM command: Trimmed options strategy {trade_id} successfully.")

    except Exception as e:
        logger.error(f"Error trimming options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in OS_TRIM command by {interaction.user.name}: {str(e)}")
    finally:
        db.close()

@bot.slash_command(name="os_exit", description="Exit an existing options strategy trade")
async def os_exit(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the options strategy trade to exit", autocomplete=discord.utils.basic_autocomplete(get_open_os_trade_ids)),
    net_cost: discord.Option(float, description="The net cost of the exit"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "os_exit", {
        "trade_id": trade_id,
        "net_cost": net_cost,
        "note": note
    })

    db = next(get_db())
    try:
        strategy = db.query(models.OptionsStrategyTrade).filter_by(trade_id=trade_id).first()
        if not strategy:
            await log_to_channel(interaction.guild, f"Options strategy trade {trade_id} not found.")
            return

        # Get all transactions for this strategy
        transactions = db.query(models.OptionsStrategyTransaction).filter_by(strategy_id=strategy.id).all()

        # Calculate average entry cost
        open_transactions = [t for t in transactions if t.transaction_type in [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD]]
        total_cost = sum(t.net_cost * float(t.size) for t in open_transactions)
        total_size = sum(float(t.size) for t in open_transactions)
        avg_entry_cost = total_cost / total_size if total_size > 0 else 0

        # Calculate average exit cost, including the current exit
        exit_transactions = [t for t in transactions if t.transaction_type in [models.TransactionTypeEnum.TRIM]]#, models.TransactionTypeEnum.CLOSE]]
        total_exit_cost = sum(t.net_cost * float(t.size) for t in exit_transactions) + (net_cost * float(strategy.current_size))
        total_exit_size = sum(float(t.size) for t in exit_transactions) + float(strategy.current_size)
        avg_exit_cost = total_exit_cost / total_exit_size if total_exit_size > 0 else 0

        # Calculate P/L per contract
        pl_per_contract = avg_exit_cost - avg_entry_cost

        new_transaction = models.OptionsStrategyTransaction(
            strategy_id=strategy.id,
            transaction_type=models.TransactionTypeEnum.CLOSE,
            net_cost=net_cost,
            size=strategy.current_size
        )
        db.add(new_transaction)

        strategy.status = models.OptionsStrategyStatusEnum.CLOSED
        strategy.closed_at = datetime.now()
        db.commit()

        embed = discord.Embed(title=f"Exited Options Strategy: {strategy.name}", color=discord.Color.red())
        embed.description = create_trade_oneliner_os(strategy)
        embed.add_field(name="Net Cost", value=f"${net_cost:.2f}", inline=True)
        embed.add_field(name="Exited Size", value=format_size(strategy.current_size), inline=True)
        embed.add_field(name="Avg Entry Cost", value=f"${avg_entry_cost:.2f}", inline=True)
        embed.add_field(name="Avg Exit Cost", value=f"${avg_exit_cost:.2f}", inline=True)
        embed.add_field(name="P/L per Contract", value=f"${pl_per_contract:.2f}", inline=True)
        if note:
            embed.add_field(name="Note", value=note, inline=False)
        embed.set_footer(text=f"Strategy ID: {strategy.trade_id}")

        config = db.query(models.TradeConfiguration).filter_by(id=strategy.configuration_id).first()
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS_EXIT command: Exited options strategy {trade_id} successfully.")

    except Exception as e:
        logger.error(f"Error exiting options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in OS_EXIT command by {interaction.user.name}: {str(e)}")
    finally:
        db.close()

# ============== Open Trades Functions =================
"""
@bot.slash_command(name="paste", description="Open a trade from the clipboard")
async def paste_trade(
    interaction: discord.Interaction,
    trade_string: discord.Option(str, description="The trade string to parse"),
    price: discord.Option(float, description="The price of the trade"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)

    try:
        parsed = parse_option_symbol(trade_string)
        new_trade = await create_trade(
            interaction=interaction,
            symbol=parsed['symbol'],
            entry_price=price,
            size=size,
            trade_type=parsed['trade_type'],
            expiration_date=parsed['expiration_date'].strftime("%m/%d/%y"),
            strike=parsed['strike'],
            option_type=parsed['option_type'],
            note=note
        )
        if new_trade:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed PASTE command: Trade has been opened successfully.")
    except ValueError as e:
        await log_to_channel(interaction.guild, f"Error in PASTE command by {interaction.user.name}: {str(e)}")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in PASTE command by {interaction.user.name}: {str(e)}")
"""
@bot.slash_command(name="open", description="Open a trade from the clipboard")
async def open_trade(
    interaction: discord.Interaction,
    trade_string: discord.Option(str, description="The trade string to parse"),
    price: discord.Option(float, description="The price of the trade"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    await kill_interaction(interaction)
    await log_command_usage(interaction, "open", {
        "trade_string": trade_string,
        "price": price,
        "size": size,
        "note": note
    })

    try:
        parsed = parse_option_symbol(trade_string)
        new_trade = await create_trade(
            interaction=interaction,
            symbol=parsed['symbol'],
            entry_price=price,
            size=size,
            trade_type=parsed['trade_type'],
            expiration_date=parsed['expiration_date'].strftime("%m/%d/%y"),
            strike=parsed['strike'],
            option_type=parsed['option_type'],
            note=note
        )
        if new_trade:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed PASTE command: Trade has been opened successfully.")
    except ValueError as e:
        await log_to_channel(interaction.guild, f"Error in PASTE command by {interaction.user.name}: {str(e)}")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in PASTE command by {interaction.user.name}: {str(e)}")

def parse_option_symbol(option_string):
    """
    Parse an option symbol string in the format ".SPXW241010P5755" or "-.SPXW241010P5755".
    
    Args:
    option_string (str): The option symbol string to parse.
    
    Returns:
    dict: A dictionary containing the parsed components:
        - symbol: The underlying symbol (e.g., 'SPX' for '.SPXW')
        - expiration_date: The expiration date as a datetime object
        - option_type: 'PUT' or 'CALL'
        - strike: The strike price as a float
        - trade_type: 'STO' if the string starts with '-', otherwise 'BTO'
    
    Raises:
    ValueError: If the string format is invalid or can't be parsed.
    """
    try:
        # Determine trade type and remove leading '-' if present
        if option_string.startswith('-'):
            trade_type = 'STO'
            option_string = option_string[1:]
        else:
            if option_string.startswith('+'):
                option_string = option_string[1:]
            trade_type = 'BTO'

        # Remove leading dot if present
        if option_string.startswith('.'):
            option_string = option_string[1:]
        
        # Handle SPXW special case
        if option_string.startswith('SPXW'):
            symbol = 'SPX'
            rest = option_string[4:]
        else:
            # Find the first digit to separate symbol from the rest
            digit_index = next(i for i, c in enumerate(option_string) if c.isdigit())
            symbol = option_string[:digit_index]
            rest = option_string[digit_index:]
        
        # Parse expiration date
        exp_date = datetime.strptime(rest[:6], '%y%m%d')
        
        # Determine option type
        option_type = 'PUT' if rest[6] == 'P' else 'CALL'
        
        # Parse strike price
        strike = round(float(rest[7:]), 2)  # Round to two decimal places
        
        return {
            'symbol': symbol,
            'expiration_date': exp_date,
            'option_type': option_type,
            'strike': strike,
            'trade_type': trade_type
        }
    except Exception as e:
        raise ValueError(f"Invalid option string format: {option_string}. Error: {str(e)}")

# Example usage:
# try:
#     parsed = parse_option_symbol(".SPXW241010P5755")
#     print(parsed)
#     parsed_sto = parse_option_symbol("-.SPXW241010P5755")
#     print(parsed_sto)
# except ValueError as e:
#     print(f"Error: {e}")

# ============== Open Trades Functions =================

@bot.slash_command(name="list", description="List open trades")
async def list_trades(interaction: discord.Interaction):
    await log_command_usage(interaction, "list", {})

    db = next(get_db())
    try:
        open_trades = crud.get_trades(db, status=models.TradeStatusEnum.OPEN)
        if not open_trades:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed LIST command: No open trades found.")
            await kill_interaction(interaction)
            return

        paginator = TradePaginator(open_trades, interaction)
        await interaction.response.defer()
        await paginator.send_page()
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed LIST command: Trades list generated.")

    except Exception as e:
        logger.error(f"Error listing trades: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in LIST command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)
    finally:
        db.close()

@bot.slash_command(name="exit", description="Exit an open trade")
async def exit_trade(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the trade to close", autocomplete=discord.utils.basic_autocomplete(get_open_trade_ids)),
    exit_price: discord.Option(float, description="The price at which the trade was closed"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    db = next(get_db())
    try:
        trade = crud.get_trade(db, trade_id)
        if not trade:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed EXIT command: Trade {trade_id} not found.")
            await kill_interaction(interaction)
            return

        # If the trade has a 4-digit year expiration, update it to 2-digit year
        if trade.expiration_date:
            trade.expiration_date = datetime.strptime(convert_to_two_digit_year(trade.expiration_date.strftime('%m/%d/%Y')), "%m/%d/%y")

        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.id == trade.configuration_id).first()
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed EXIT command: Configuration for trade {trade_id} not found.")
            await kill_interaction(interaction)
            return

        trade.status = models.TradeStatusEnum.CLOSED
        trade.exit_price = exit_price
        trade.closed_at = datetime.now()
        
        current_size = Decimal(trade.current_size)
        
        new_transaction = models.Transaction(
            trade_id=trade.trade_id,
            transaction_type=models.TransactionTypeEnum.CLOSE,
            amount=exit_price,
            size=str(current_size),
            created_at=datetime.now()
        )
        db.add(new_transaction)
        db.commit()

        # Calculate profit/loss considering all transactions
        open_transactions = crud.get_transactions_for_trade(db, trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
        trim_transactions = crud.get_transactions_for_trade(db, trade_id, [models.TransactionTypeEnum.TRIM])
        
        total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
        total_open_size = sum(Decimal(t.size) for t in open_transactions)
        total_trimmed_size = sum(Decimal(t.size) for t in trim_transactions)
        
        average_cost = total_cost / total_open_size if total_open_size > 0 else Decimal('0')
        
        # Calculate profit/loss from trims
        trim_profit_loss = sum((Decimal(t.amount) - average_cost) * Decimal(t.size) for t in trim_transactions)
        
        # Calculate profit/loss from final exit
        exit_profit_loss = (Decimal(exit_price) - average_cost) * current_size
        
        # Total profit/loss
        total_profit_loss = trim_profit_loss + exit_profit_loss
        trade.profit_loss = float(total_profit_loss)

        # Calculate profit/loss per share or per contract
        if trade.is_contract:
            profit_loss_per_unit = (total_profit_loss / total_open_size) * 100 # Assuming 100 shares per contract
            unit_type = "contract"
        else:
            profit_loss_per_unit = total_profit_loss / total_open_size
            unit_type = "share"

        # Determine win/loss
        if total_profit_loss > 0:
            trade.win_loss = models.WinLossEnum.WIN
        elif total_profit_loss < 0:
            trade.win_loss = models.WinLossEnum.LOSS
        else:
            trade.win_loss = models.WinLossEnum.BREAKEVEN

        if trade.average_exit_price:
            trade.average_exit_price = (trade.average_exit_price * total_trim_size + Decimal(exit_price) * current_size) / (total_trim_size + current_size)
        else:
            trade.average_exit_price = exit_price

        db.commit()

        # Create an embed with the closed trade information
        embed = discord.Embed(title="Trade Closed", color=discord.Color.gold())
        
        # Add the one-liner at the top of the embed
        embed.description = create_trade_oneliner(trade)
        
        embed.add_field(name="Exit Price", value=f"${exit_price:.2f}", inline=True)
        embed.add_field(name="Exit Size", value=format_size(current_size), inline=True)
        embed.add_field(name=f"Trade P/L per {unit_type}", value=f"${profit_loss_per_unit:.2f}", inline=True)
        embed.add_field(name="Avg Entry Price", value=f"${trade.average_price:.2f}", inline=True)
        if trade.average_exit_price:
            embed.add_field(name="Avg Exit Price", value=f"${trade.average_exit_price:.2f}", inline=True)
        else:
            embed.add_field(name="Avg Exit Price", value=f"${exit_price:.2f}", inline=True)
        embed.add_field(name="Result", value=trade.win_loss.value.capitalize(), inline=True)

        # Set the footer to include the trade ID
        embed.set_footer(text=f"Trade ID: {trade_id}")

        # Send an ephemeral reply to the user
        await kill_interaction(interaction)

        # Send the embed to the configured channel with role ping
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        # Send an additional embed with the note if provided
        if note:
            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey())
            await channel.send(embed=note_embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed EXIT command: Trade {trade_id} closed successfully.")

    except Exception as e:
        logger.error(f"Error closing trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in EXIT command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)
    finally:
        db.close()

@bot.slash_command(name="add", description="Add to an existing trade")
async def add_to_trade(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the trade to add to", autocomplete=discord.utils.basic_autocomplete(get_open_trade_ids)),
    add_price: discord.Option(float, description="The price at which the trade was added"),
    add_size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    db = next(get_db())
    try:
        trade = crud.get_trade(db, trade_id)
        if not trade:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD command: Trade {trade_id} not found.")
            await kill_interaction(interaction)
            return

        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.id == trade.configuration_id).first()
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD command: Configuration for trade {trade_id} not found.")
            await kill_interaction(interaction)
            return

        new_transaction = models.Transaction(
            trade_id=trade.trade_id,
            transaction_type=models.TransactionTypeEnum.ADD,
            amount=add_price,
            size=add_size,
            created_at=datetime.utcnow()
        )
        db.add(new_transaction)

        # Update the current size of the trade
        current_size = Decimal(trade.current_size)
        add_size_decimal = Decimal(add_size)
        new_size = current_size + add_size_decimal
        trade.current_size = str(new_size)
        trade.average_price = (Decimal(trade.average_price) * current_size + Decimal(add_price) * add_size_decimal) / new_size

        db.commit()

        # Create an embed with the transaction information
        embed = discord.Embed(title="Added to Trade", color=discord.Color.teal())
        embed.description = create_transaction_oneliner(trade, "ADD", add_size, add_price)
        embed.add_field(name="Symbol", value=trade.symbol, inline=True)
        if trade.expiration_date:
            embed.add_field(name="Exp. Date", value=trade.expiration_date.strftime('%m/%d/%y'), inline=True)
        embed.add_field(name="Trade Type", value=trade.trade_type, inline=True)
        if trade.strike:
            embed.add_field(name="Strike", value=f"${trade.strike:.2f}", inline=True)
        embed.add_field(name="Add Price", value=f"${add_price:.2f}", inline=True)
        embed.add_field(name="Add Size", value=format_size(add_size), inline=True)
        embed.add_field(name="Total Size", value=format_size(new_size), inline=True)
        embed.add_field(name="Avg Price", value=f"${trade.average_price:.2f}", inline=True)

        embed.set_footer(text=f"Trade ID: {trade.trade_id}")

        # Send an ephemeral reply to the user
        await kill_interaction(interaction)

        # Send the embed to the configured channel with role ping
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        # Send an additional embed with the note if provided
        if note:
            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey())
            await channel.send(embed=note_embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD command: Transaction added to trade {trade_id} successfully.")

    except Exception as e:
        logger.error(f"Error adding to trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in ADD command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)
    finally:
        db.close()

@bot.slash_command(name="trim", description="Sell a partial amount of an existing trade")
async def trim_trade(
    interaction: discord.Interaction,
    trade_id: discord.Option(str, description="The ID of the trade to trim", autocomplete=discord.utils.basic_autocomplete(get_open_trade_ids)),
    trim_price: discord.Option(float, description="The price at which to trim the trade"),
    trim_size: discord.Option(str, description="The size to trim from the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    db = next(get_db())
    try:
        trade = crud.get_trade(db, trade_id)
        if not trade:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TRIM command: Trade {trade_id} not found.")
            await kill_interaction(interaction)
            return

        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.id == trade.configuration_id).first()
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TRIM command: Configuration for trade {trade_id} not found.")
            await kill_interaction(interaction)
            return


        current_size = Decimal(trade.current_size)
        trim_size = Decimal(trim_size)

        trim_transactions = crud.get_transactions_for_trade(db, trade_id, [models.TransactionTypeEnum.TRIM])
        total_trim_size = sum(Decimal(t.size) for t in trim_transactions)

        if trim_size > current_size:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TRIM command: Trim size ({trim_size}) is greater than current trade size ({current_size}).")
            await kill_interaction(interaction)
            return

        new_transaction = models.Transaction(
            trade_id=trade.trade_id,
            transaction_type=models.TransactionTypeEnum.TRIM,
            amount=trim_price,
            size=str(trim_size),
            created_at=datetime.utcnow()
        )
        db.add(new_transaction)

        # Update the current size of the trade
        new_size = current_size - trim_size
        trade.current_size = str(new_size)
        if trade.average_exit_price:
            trade.average_exit_price = (Decimal(trade.average_exit_price) * total_trim_size + Decimal(trim_price) * trim_size) / (total_trim_size + trim_size)
        else:
            trade.average_exit_price = trim_price

        db.commit()

        # Calculate profit/loss for this trim
        open_transactions = crud.get_transactions_for_trade(db, trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
        total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
        total_size = sum(Decimal(t.size) for t in open_transactions)
        average_cost = total_cost / total_size if total_size > 0 else Decimal('0')
        
        trim_profit_loss = (Decimal(trim_price) - average_cost)

        if trade.is_contract:
            trim_profit_loss = trim_profit_loss * 100
            unit = "contract"
        else:
            unit = "share"

        # Create an embed with the transaction information
        embed = discord.Embed(title="Trimmed Trade", color=discord.Color.orange())
        embed.description = create_transaction_oneliner(trade, "TRIM", trim_size, trim_price)
        embed.add_field(name="Symbol", value=trade.symbol, inline=True)
        embed.add_field(name="Trade Type", value=trade.trade_type, inline=True)
        if trade.expiration_date:
            embed.add_field(name="Exp. Date", value=trade.expiration_date.strftime('%m/%d/%y'), inline=True)
        if trade.strike:
            embed.add_field(name="Strike", value=f"${trade.strike:.2f}", inline=True)
        embed.add_field(name="Trim Price", value=f"${trim_price:.2f}", inline=True)
        embed.add_field(name="Trim Size", value=format_size(trim_size), inline=True)
        embed.add_field(name="Remaining Size", value=format_size(new_size), inline=True)
        embed.add_field(name="Avg Exit Price", value=f"${trade.average_exit_price:.2f}", inline=True)
        embed.add_field(name=f"P/L per {unit}", value=f"${trim_profit_loss:.2f}", inline=True)

        embed.set_footer(text=f"Trade ID: {trade.trade_id}")

        # Send an ephemeral reply to the user
        await kill_interaction(interaction)

        # Send the embed to the configured channel with role ping
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        # Send an additional embed with the note if provided
        if note:
            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey())
            await channel.send(embed=note_embed)

        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TRIM command: Trade {trade_id} trimmed successfully.")

    except Exception as e:
        logger.error(f"Error trimming trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in TRIM command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)
    finally:
        db.close()




# ============== Configuration Functions =================

@bot.slash_command(name="setup_conditional_role_grant", description="Set up a conditional role grant configuration")
async def setup_conditional_role_grant(
    interaction: discord.Interaction,
    condition_roles: discord.Option(str, description="Comma-separated list of role IDs that users must have at least one of"),
    grant_role: discord.Option(discord.Role, description="The role to grant if conditions are met"),
    exclude_role: discord.Option(discord.Role, description="The role that, if present, prevents granting the new role") = None
):
    db = next(get_db())
    try:
        role_ids = [role.strip() for role in condition_roles.split(',')]
        new_grant = models.ConditionalRoleGrant(
            guild_id=str(interaction.guild_id),
            grant_role_id=str(grant_role.id),
            exclude_role_id=str(exclude_role.id) if exclude_role else None
        )
        db.add(new_grant)
        db.flush()

        for role_id in role_ids:
            role = models.Role(role_id=role_id, guild_id=str(interaction.guild_id))
            db.add(role)
            new_grant.condition_roles.append(role)

        db.commit()
        await interaction.response.send_message("Conditional role grant configuration set up successfully.", ephemeral=True)
    except Exception as e:
        db.rollback()
        await interaction.response.send_message(f"Error setting up conditional role grant: {str(e)}", ephemeral=True)
    finally:
        db.close()

@bot.slash_command(name="setup_trade_config", description="Set up a trade configuration with channels and role")
async def setup_trade_config(
    interaction: discord.Interaction,
    name: discord.Option(str, description="A name for this trade configuration"),
    channel: discord.Option(discord.TextChannel, description="The main channel to send notifications to"),
    role: discord.Option(discord.Role, description="The role to ping"),
    roadmap_channel: discord.Option(discord.TextChannel, description="The channel for roadmap posts"),
    update_channel: discord.Option(discord.TextChannel, description="The channel for update posts"),
    portfolio_channel: discord.Option(discord.TextChannel, description="The channel for portfolio updates"),
    log_channel: discord.Option(discord.TextChannel, description="The channel for logging verifications"),
):
    db = next(get_db())
    try:
        existing_config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.name == name).first()
        if existing_config:
            await interaction.response.send_message(f"A trade configuration with the name '{name}' already exists. Please choose a different name.", ephemeral=True)
            return

        new_config = models.TradeConfiguration(
            name=name,
            channel_id=str(channel.id),
            role_id=str(role.id),
            roadmap_channel_id=str(roadmap_channel.id),
            update_channel_id=str(update_channel.id),
            portfolio_channel_id=str(portfolio_channel.id),
            log_channel_id=str(log_channel.id),
        )
        db.add(new_config)
        db.commit()

        await interaction.response.send_message(
            f"Trade configuration '{name}' created successfully:\n"
            f"Main Channel: {channel.name}\n"
            f"Role: {role.name}\n"
            f"Roadmap Channel: {roadmap_channel.name}\n"
            f"Update Channel: {update_channel.name}\n"
            f"Portfolio Channel: {portfolio_channel.name}\n"
            f"Log Channel: {log_channel.name}",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"Error setting up trade configuration: {str(e)}", ephemeral=True)
    finally:
        db.close()

@bot.slash_command(name="list_trade_configs", description="List all trade configurations")
async def list_trade_configs(interaction: discord.Interaction):
    db = next(get_db())
    try:
        configs = db.query(models.TradeConfiguration).all()
        if not configs:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed LIST_TRADE_CONFIGS command: No trade configurations found.")
            await kill_interaction(interaction)
            return

        embed = discord.Embed(title="Trade Configurations", color=discord.Color.purple())
        for config in configs:
            channel = interaction.guild.get_channel(int(config.channel_id))
            role = interaction.guild.get_role(int(config.role_id))
            channel_name = channel.name if channel else "Unknown Channel"
            role_name = role.name if role else "Unknown Role"
            embed.add_field(
                name=config.name,
                value=f"Channel: {channel_name}\n"
                      f"Role: {role_name}\n"
                      f"Trade Group: {config.name}",  # Use config.name instead of config.trade_group
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed LIST_TRADE_CONFIGS command: Trade configurations list generated.")
    except Exception as e:
        logger.error(f"Error listing trade configurations: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in LIST_TRADE_CONFIGS command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)
    finally:
        db.close()

@bot.slash_command(name="remove_trade_config", description="Remove a trade configuration")
async def remove_trade_config(
    interaction: discord.Interaction,
    name: discord.Option(str, description="The name of the trade configuration to remove")
):
    db = next(get_db())
    try:
        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.name == name).first()
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed REMOVE_TRADE_CONFIG command: Trade configuration '{name}' not found.")
            await kill_interaction(interaction)
            return

        db.delete(config)
        db.commit()

        await interaction.response.send_message(f"Trade configuration '{name}' removed successfully.", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed REMOVE_TRADE_CONFIG command: Trade configuration '{name}' removed successfully.")
    except Exception as e:
        logger.error(f"Error removing trade configuration: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in REMOVE_TRADE_CONFIG command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)
    finally:
        db.close()

@bot.slash_command(name="wl", description="Send a watchlist update")
async def watchlist_update(
    interaction: discord.Interaction,
    message: discord.Option(str, description="The watchlist update message")
):
    await kill_interaction(interaction)
    db = next(get_db())
    try:
        config = db.query(models.BotConfiguration).first()
        if not config or not config.watchlist_channel_id:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed WL command: Watchlist channel not configured. Use /set_watchlist_channel first.")
            return
        channel = interaction.guild.get_channel(int(config.watchlist_channel_id))
        if not channel:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed WL command: Configured watchlist channel not found.")
            return
        try:
            parsed_message = parse_option_symbol(message)
            message = f"{parsed_message['expiration_date'].strftime('%m/%d/%y')} {parsed_message['symbol']} {parsed_message['strike']} {parsed_message['option_type']}"
        except Exception as e:
            await log_to_channel(interaction.guild, f"Error parsing option symbols: {str(e)} posting regular message instead.")

        embed = discord.Embed(title="Watchlist Update", description=message, color=discord.Color.blue())
        embed.set_footer(text=f"Posted by {interaction.user.name}")
        await channel.send(embed=embed)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed WL command: Watchlist update sent successfully.")
    except Exception as e:
        logger.error(f"Error sending watchlist update: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in WL command by {interaction.user.name}: {str(e)}")
    finally:
        db.close()

@bot.slash_command(name="set_configuration_wl_ta", description="Set the watchlist and technical analysis channels")
async def set_configuration_wl_ta(
    interaction: discord.Interaction,
    watchlist_channel: discord.Option(discord.TextChannel, description="The watchlist channel"),
    technical_analysis_channel: discord.Option(discord.TextChannel, description="The technical analysis channel")
):
    await kill_interaction(interaction)
    db = next(get_db())
    config = db.query(models.BotConfiguration).first()
    if not config:
        config = models.BotConfiguration()
        config.watchlist_channel_id = str(watchlist_channel.id)
        config.ta_channel_id = str(technical_analysis_channel.id) 
        db.add(config)
    else:
        config.watchlist_channel_id = str(watchlist_channel.id)
        config.ta_channel_id = str(technical_analysis_channel.id)
    
    db.commit()
    await interaction.response.send_message("Configuration updated successfully.", ephemeral=True)

@bot.slash_command(name="ta", description="Send a technical analysis update")
async def ta_update(
    interaction: discord.Interaction,
    message: discord.Option(str, description="The technical analysis update message")
):
    await kill_interaction(interaction)
    db = next(get_db())
    try:
        config = db.query(models.BotConfiguration).first()
        if not config or not config.ta_channel_id:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TA command: Technical analysis channel not configured. Use /set_ta_channel first.")
            return
        channel = interaction.guild.get_channel(int(config.ta_channel_id))
        if not channel:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TA command: Configured technical analysis channel not found.")
            return
        embed = discord.Embed(title="Technical Analysis Update", description=message, color=discord.Color.green())
        embed.set_footer(text=f"Posted by {interaction.user.name}")
        await channel.send(embed=embed)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TA command: Technical analysis update sent successfully.")
    except Exception as e:
        logger.error(f"Error sending technical analysis update: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in TA command by {interaction.user.name}: {str(e)}")
        await interaction.response.defer(ephemeral=True)
    finally:
        db.close()

@bot.slash_command(name="r", description="Post a roadmap message")
async def post_roadmap(
    interaction: discord.Interaction,
    trade_group: discord.Option(str, description="The trade group for this roadmap post", autocomplete=discord.utils.basic_autocomplete(get_trade_groups)),
    message: discord.Option(str, description="The roadmap message to post")
):
    db = next(get_db())
    try:
        config = get_configuration(db, trade_group)
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed R command: No configuration found for trade group: {trade_group}")
            await kill_interaction(interaction)
            return

        if not config.roadmap_channel_id:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed R command: No roadmap channel configured for trade group: {trade_group}")
            await kill_interaction(interaction)
            return

        embed = discord.Embed(title="Roadmap Update", description=message, color=discord.Color.blue())
        embed.set_footer(text=f"Posted by {interaction.user.name}")

        channel = interaction.guild.get_channel(int(config.roadmap_channel_id))
        await channel.send(embed=embed)

        await interaction.response.send_message("Roadmap message posted successfully.", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed R command: Roadmap message posted successfully.")
    except Exception as e:
        logger.error(f"Error posting roadmap message: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in R command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)
    finally:
        db.close()

@bot.slash_command(name="u", description="Post an update message")
async def post_update(
    interaction: discord.Interaction,
    trade_group: discord.Option(str, description="The trade group for this update post", autocomplete=discord.utils.basic_autocomplete(get_trade_groups)),
    message: discord.Option(str, description="The update message to post")
):
    db = next(get_db())
    try:
        config = get_configuration(db, trade_group)
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed U command: No configuration found for trade group: {trade_group}")
            await kill_interaction(interaction)
            return

        if not config.update_channel_id:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed U command: No update channel configured for trade group: {trade_group}")
            await kill_interaction(interaction)
            return

        embed = discord.Embed(title="Trade Update", description=message, color=discord.Color.green())
        embed.set_footer(text=f"Posted by {interaction.user.name}")

        channel = interaction.guild.get_channel(int(config.update_channel_id))
        await channel.send(embed=embed)

        #await interaction.response.send_message("Update message posted successfully.", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed U command: Update message posted successfully.")
    except Exception as e:
        logger.error(f"Error posting update message: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in U command by {interaction.user.name}: {str(e)}")
        await kill_interaction(interaction)
    finally:
        db.close()

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

        channel = interaction.guild.get_channel(int(config.update_channel_id))
        await channel.send(embed=embed)
