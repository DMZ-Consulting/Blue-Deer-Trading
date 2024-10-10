import logging
import os
import traceback
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import aiofiles
import discord
from discord import ButtonStyle
from discord.errors import HTTPException
from discord.ext import commands, tasks
from discord.ui import Button, View
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from . import crud, models
from .database import engine, get_db
from .models import create_tables  # Add this import

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
                value=f"Symbol: {trade.symbol}\nType: {trade.trade_type}\nEntry Price: {entry_price}\nCurrent Size: {trade.current_size}",
                inline=False
            )
            
            # Add transactions for this trade
            transactions = crud.get_transactions_for_trade(next(get_db()), trade.trade_id)
            if transactions:
                transaction_text = "\n".join([f"{t.transaction_type.value}: {t.size} @ ${t.amount:,.2f}" if t.amount >= 0 else f"{t.transaction_type.value}: {t.size} @ (${abs(t.amount):,.2f}) at {t.created_at.strftime('%Y-%m-%d %H:%M:%S')}" for t in transactions])
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
        trade.closed_at = datetime.utcnow()
        
        current_size = Decimal(trade.current_size)
        
        new_transaction = models.Transaction(
            trade_id=trade.trade_id,
            transaction_type=models.TransactionTypeEnum.CLOSE,
            amount=exit_price,
            size=str(current_size),
            created_at=datetime.utcnow()
        )
        db.add(new_transaction)

        # Calculate profit/loss
        open_transactions = crud.get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
        trim_transactions = crud.get_transactions_for_trade(db, trade.trade_id, [models.TransactionTypeEnum.TRIM])
        
        total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
        total_open_size = sum(Decimal(t.size) for t in open_transactions)
        total_trimmed_size = sum(Decimal(t.size) for t in trim_transactions)
        
        average_cost = total_cost / total_open_size if total_open_size > 0 else 0
        
        trim_profit_loss = sum((Decimal(t.amount) - average_cost) * Decimal(t.size) for t in trim_transactions)
        exit_profit_loss = (Decimal(exit_price) - average_cost) * current_size
        
        total_profit_loss = trim_profit_loss + exit_profit_loss
        trade.profit_loss = float(total_profit_loss)

        # Determine win/loss
        trade.win_loss = models.WinLossEnum.LOSS

        db.commit()

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

    except Exception as e:
        logger.error(f"Error exiting expired trade {trade.trade_id}: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        db.close()

@bot.slash_command(name="setup_verification", description="Set up a verification message with terms and conditions")
async def setup_verification(
    interaction: discord.Interaction,
    channel: discord.Option(discord.TextChannel, description="The channel to send the verification message"),
    terms: discord.Option(str, description="The terms and conditions text"),
    role_to_remove: discord.Option(discord.Role, description="The role to remove upon verification"),
    role_to_add: discord.Option(discord.Role, description="The role to add upon verification"),
    log_channel: discord.Option(discord.TextChannel, description="The channel for logging verifications"),
):
    print("setup_verification called")
    # Defer the response immediately
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
    print("handle_verification called")
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
                display = symbol
                sort_key = (symbol, datetime.max, 0)  # Put non-option trades at the bottom of their symbol group
            
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
    
    if days_to_expiration < 7:
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
    direction = "LONG" if trade.trade_type.lower() in ["long", "buy to open"] else "SHORT"
    size = trade.current_size
    entry_price = f"${trade.entry_price:.2f}"
    
    if trade.is_contract:
        expiration = convert_to_two_digit_year(trade.expiration_date.strftime('%m/%d/%y')) if trade.expiration_date else "No Exp"
        strike = f"${trade.strike:.2f}"
        #option_type = "c" if direction == "LONG" else "p"
        option_type = "" #TODO
        return f"{expiration} {trade.symbol} {strike}{option_type} @ {entry_price} {size} size"
    else:
        return f"{trade.symbol} @ {entry_price} {size} size"

@bot.slash_command(name="bto", description="Buy to open a new trade")
async def bto(
    interaction: discord.Interaction,
    symbol: discord.Option(str, description="The symbol of the security"),
    entry_price: discord.Option(float, description="The price at which the trade was opened"),
    size: discord.Option(str, description="The size of the trade"),
    expiration_date: discord.Option(str, description="The expiration date of the trade (MM/DD/YY)") = None,
    strike: discord.Option(float, description="The strike price of the trade") = None,
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    print("bto called")
    await interaction.response.defer(ephemeral=True)
    
    db = next(get_db())
    try:
        print(f"BTO called with expiration_date: {expiration_date}")
        
        if expiration_date:
            expiration_date = convert_to_two_digit_year(expiration_date)
        print(f"Converted expiration_date: {expiration_date}")
        
        try:
            trade_group = determine_trade_group(expiration_date, "bto")
            print(f"Trade group determined: {trade_group}")
        except Exception as e:
            print(f"Error in determine_trade_group: {str(e)}")
            await log_to_channel(interaction.guild, f"Error in BTO command by {interaction.user.name}: {str(e)}")
            return
        
        try:
            config = get_configuration(db, trade_group)
            print(f"Configuration retrieved: {config}")
        except Exception as e:
            print(f"Error in get_configuration: {str(e)}")
            await log_to_channel(interaction.guild, f"Error in BTO command by {interaction.user.name}: {str(e)}")
            return
        
        if not config:
            print(f"No configuration found for trade group: {trade_group}")
            await interaction.followup.send(f"No configuration found for trade group: {trade_group}", ephemeral=True)
            return
        
        print("Checking if it's a contract and day trade")
        is_contract = expiration_date is not None
        is_day_trade = False
        if is_contract:
            try:
                exp_date = datetime.strptime(expiration_date, "%m/%d/%y")
                is_day_trade = (exp_date - datetime.now()).days < 7
            except ValueError as e:
                print(f"Error parsing expiration date: {str(e)}")
                await interaction.followup.send("Invalid expiration date format. Please use MM/DD/YY.", ephemeral=True)
                return
        
        print("Creating new trade")
        new_trade = models.Trade(
            symbol=symbol,
            trade_type="BTO",
            status=models.TradeStatusEnum.OPEN,
            entry_price=entry_price,
            average_price=entry_price,
            size=size,
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
            expiration_date=datetime.strptime(expiration_date, "%m/%d/%y") if expiration_date else None
        )
        print("Adding new trade to database")
        db.add(new_trade)
        print("New trade added to session")
        db.commit()
        print("Database committed")
        db.refresh(new_trade)
        print("New trade refreshed")

        print("new_trade", new_trade)

        # Create an embed with the trade information
        embed = discord.Embed(title="New Trade Opened", color=discord.Color.green())
        
        # Add the one-liner at the top of the embed
        embed.description = create_trade_oneliner(new_trade)
        
        embed.add_field(name="Symbol", value=symbol, inline=True)
        embed.add_field(name="Trade Type", value="Buy to Open", inline=True)
        entry_price_display = f"${entry_price:,.2f}" if entry_price >= 0 else f"(${abs(entry_price):,.2f})"
        embed.add_field(name="Entry Price", value=entry_price_display, inline=True)
        embed.add_field(name="Risk Level (1-6)", value=size, inline=True)
        #embed.add_field(name="Trade Group", value=trade_group, inline=True)
        if expiration_date:
            embed.add_field(name="Exp. Date", value=expiration_date, inline=True)
        if strike:
            strike_display = f"${strike:,.2f}" if strike >= 0 else f"(${abs(strike):,.2f})"
            embed.add_field(name="Strike Price", value=strike_display, inline=True)

        embed.set_footer(text=f"Trade ID: {new_trade.trade_id}")

        # Instead of sending an ephemeral message, log the command
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed BTO command: Trade has been opened successfully.")

        # Send the embed to the configured channel with role ping
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        # Send an additional embed with the note if provided
        if note:
            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey())
            await channel.send(embed=note_embed)

        # Add the initial transaction
        new_transaction = models.Transaction(
            trade_id=new_trade.trade_id,
            transaction_type=models.TransactionTypeEnum.OPEN,
            amount=entry_price,
            size=size,
            created_at=datetime.utcnow()
        )
        db.add(new_transaction)
        db.commit()

    except Exception as e:
        print(f"Unexpected error in BTO command: {str(e)}")
        logger.error(f"Error opening trade: {str(e)}")
        # Log the error instead of sending an ephemeral message
        await log_to_channel(interaction.guild, f"Error in BTO command by {interaction.user.name}: {str(e)}")
    finally:
        db.close()

    

@bot.slash_command(name="sto", description="Sell to open a new trade")
async def sto(
    interaction: discord.Interaction,
    symbol: discord.Option(str, description="The symbol of the security"),
    entry_price: discord.Option(float, description="The price at which the trade was opened"),
    size: discord.Option(str, description="The size of the trade"),
    expiration_date: discord.Option(str, description="The expiration date of the trade (MM/DD/YY)") = None,
    strike: discord.Option(float, description="The strike price of the trade") = None,
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    print("sto called")
    # Instead of sending a generic response to the user, we'll defer the response and then do nothing
    await interaction.response.defer(ephemeral=True)

    db = next(get_db())
    try:
        # Convert expiration_date to 2-digit year format if it's not already
        if expiration_date:
            expiration_date = convert_to_two_digit_year(expiration_date)
        
        # Determine trade group based on expiration date
        trade_group = determine_trade_group(expiration_date, "sto")
        
        config = get_configuration(db, trade_group)
        if not config:
            await interaction.response.send_message(f"No configuration found for trade group: {trade_group}", ephemeral=True)
            return

        is_contract = expiration_date is not None
        is_day_trade = False
        if is_contract:
            try:
                exp_date = datetime.strptime(expiration_date, "%m/%d/%y")
                is_day_trade = (exp_date - datetime.now()).days < 7
            except ValueError:
                await interaction.response.send_message("Invalid expiration date format. Please use MM/DD/YY.", ephemeral=True)
                return

        new_trade = models.Trade(
            symbol=symbol,
            trade_type="Sell to Open",
            status=models.TradeStatusEnum.OPEN,
            entry_price=entry_price,
            average_price=entry_price,
            size=size,
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
            expiration_date=datetime.strptime(expiration_date, "%m/%d/%y") if expiration_date else None
        )
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)

        # Create an embed with the trade information
        embed = discord.Embed(title="New Trade Opened", color=discord.Color.red())
        
        # Add the one-liner at the top of the embed
        embed.description = create_trade_oneliner(new_trade)
        
        embed.add_field(name="Symbol", value=symbol, inline=True)
        embed.add_field(name="Trade Type", value="Sell to Open", inline=True)
        entry_price_display = f"${entry_price:,.2f}" if entry_price >= 0 else f"(${abs(entry_price):,.2f})"
        embed.add_field(name="Entry Price", value=entry_price_display, inline=True)
        embed.add_field(name="Risk Level (1-6)", value=size, inline=True)

        if expiration_date:
            embed.add_field(name="Exp. Date", value=expiration_date, inline=True)
        if strike:
            strike_display = f"${strike:,.2f}" if strike >= 0 else f"(${abs(strike):,.2f})"
            embed.add_field(name="Strike Price", value=strike_display, inline=True)
        embed.set_footer(text=f"Trade ID: {new_trade.trade_id}")

        # Send an ephemeral reply to the user
        await interaction.response.send_message("Trade has been opened successfully.", ephemeral=True)

        # Send the embed to the configured channel with role ping
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        # Send an additional embed with the note if provided
        if note:
            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey())
            await channel.send(embed=note_embed)

        # Add the initial transaction
        new_transaction = models.Transaction(
            trade_id=new_trade.trade_id,
            transaction_type=models.TransactionTypeEnum.OPEN,
            amount=entry_price,
            size=size,
            created_at=datetime.utcnow()
        )
        db.add(new_transaction)
        db.commit()

    except Exception as e:
        await interaction.response.send_message(f"Error opening trade: {e}", ephemeral=True)
    finally:
        db.close()

@bot.slash_command(name="fut", description="Buy to open a new trade")
async def future_trade(
    interaction: discord.Interaction,
    symbol: discord.Option(str, description="The symbol of the security"),
    entry_price: discord.Option(float, description="The price at which the trade was opened"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    trade_group = TradeGroupEnum.DAY_TRADER
    await interaction.response.defer(ephemeral=True)
    try:
        await common_stock_trade(interaction.guild, trade_group, symbol, entry_price, size, note)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed FUT command: Trade has been opened successfully.")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in future trade (FUT) command by {interaction.user.name}: {str(e)}")

@bot.slash_command(name="lt", description="Buy to open a new trade")
async def long_term_trade(
    interaction: discord.Interaction,
    symbol: discord.Option(str, description="The symbol of the security"),
    entry_price: discord.Option(float, description="The price at which the trade was opened"),
    size: discord.Option(str, description="The size of the trade"),
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    trade_group = TradeGroupEnum.LONG_TERM_TRADER
    await interaction.response.defer(ephemeral=True)
    try:
        await common_stock_trade(interaction.guild, trade_group, symbol, entry_price, size, note)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed LT command: Trade has been opened successfully.")
    except Exception as e:
        await log_to_channel(interaction.guild, f"Error in long term trade (LT) command by {interaction.user.name}: {str(e)}")


async def common_stock_trade(
        guild: discord.Guild,
        trade_group: TradeGroupEnum,
        symbol: str,
        entry_price: float,
        size: str,
        note: str = None,
):
    db = next(get_db())
    try:
        print(f"BTO called with expiration_date: {expiration_date}")
        
        if expiration_date:
            expiration_date = convert_to_two_digit_year(expiration_date)
        print(f"Converted expiration_date: {expiration_date}")
        
        try:
            trade_group = determine_trade_group(expiration_date, "bto")
            print(f"Trade group determined: {trade_group}")
        except Exception as e:
            print(f"Error in determine_trade_group: {str(e)}")
            await log_to_channel(guild, f"Error in BTO command: {str(e)}")
            return
        
        try:
            config = get_configuration(db, trade_group)
            print(f"Configuration retrieved: {config}")
        except Exception as e:
            print(f"Error in get_configuration: {str(e)}")
            await log_to_channel(guild, f"Error in BTO command: {str(e)}")
            return
        
        if not config:
            print(f"No configuration found for trade group: {trade_group}")
            return
        
        print("Checking if it's a contract and day trade")
        is_contract = expiration_date is not None
        is_day_trade = False
        if is_contract:
            try:
                exp_date = datetime.strptime(expiration_date, "%m/%d/%y")
                is_day_trade = (exp_date - datetime.now()).days < 7
            except ValueError as e:
                print(f"Error parsing expiration date: {str(e)}")
                return
        
        print("Creating new trade")
        new_trade = models.Trade(
            symbol=symbol,
            trade_type="BTO",
            status=models.TradeStatusEnum.OPEN,
            entry_price=entry_price,
            average_price=entry_price,
            size=size,
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
            expiration_date=datetime.strptime(expiration_date, "%m/%d/%y") if expiration_date else None
        )
        
        print("Adding new trade to database")
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)
        
        embed = discord.Embed(title="New Trade Opened", color=discord.Color.green())
        
        embed.description = create_trade_oneliner(new_trade)
        
        embed.add_field(name="Symbol", value=symbol, inline=True)
        embed.add_field(name="Trade Type", value="Buy to Open", inline=True)
        entry_price_display = f"${entry_price:,.2f}" if entry_price >= 0 else f"(${abs(entry_price):,.2f})"
        embed.add_field(name="Entry Price", value=entry_price_display, inline=True)
        embed.add_field(name="Risk Level (1-6)", value=size, inline=True)

        embed.set_footer(text=f"Trade ID: {new_trade.trade_id}")

        channel = guild.get_channel(int(config.channel_id))
        role = guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        if note:
            note_embed = discord.Embed(title="Trader's Note", description=note, color=discord.Color.light_grey())
            await channel.send(embed=note_embed)

        new_transaction = models.Transaction(
            trade_id=new_trade.trade_id,
            transaction_type=models.TransactionTypeEnum.OPEN,
            amount=entry_price,
            size=size,
            created_at=datetime.utcnow()
        )
        db.add(new_transaction)
        db.commit()

    except Exception as e:
        print(f"Unexpected error in BTO command: {str(e)}")
        logger.error(f"Error opening trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in BTO command by {interaction.user.name}: {str(e)}")
    finally:
        db.close()


@bot.slash_command(name="scrape_channel", description="Scrape all messages from a channel and save to a file")
async def scrape_channel(
    interaction: discord.Interaction,
    channel: discord.Option(discord.TextChannel, description="The channel to scrape"),
    filename: discord.Option(str, description="The filename to save the scraped data (e.g., 'output.txt')")
):
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

async def run_bot():

    if os.getenv("LOCAL_TEST", "false").lower() == "true":
        token = os.getenv('TEST_TOKEN')
    else:   
        token = os.getenv('DISCORD_TOKEN')

    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set.")
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Failed to start the bot: {str(e)}")
        raise

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

