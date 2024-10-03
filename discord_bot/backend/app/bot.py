import os
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .database import SessionLocal
from discord import AutocompleteContext, OptionChoice, ButtonStyle
from decimal import Decimal
from typing import List, Tuple
from operator import attrgetter
import traceback
import logging
import asyncio
import io
from .models import create_tables  # Add this import
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .database import SQLALCHEMY_DATABASE_URL

load_dotenv()

TEST_MODE = os.getenv('TEST_MODE')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    create_tables()  # Add this line to create tables
    #check_and_update_roles.start()
    
    # Sync commands for specific servers
    guild_ids = [os.getenv('PROD_GUILD_ID'), os.getenv('TEST_GUILD_ID')]
    
    for guild_id in guild_ids:
        if guild_id:
            try:
                guild = discord.Object(id=int(guild_id))
                synced = await bot.sync_commands(guild_ids=[guild.id])
                if synced:
                    print(f"Synced {len(synced)} command(s) to the guild with ID {guild_id}.")
                else:
                    print(f"No commands were synced to the guild with ID {guild_id}. This might be because there are no commands to sync or the bot doesn't have the necessary permissions.")
            except Exception as e:
                print(f"Failed to sync commands to the guild with ID {guild_id}: {e}")
        else:
            print(f"Guild ID not set. Skipping command sync.")

    print("Bot is ready!")

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

def update_expiration_dates():
    """
    Update all trade expiration dates in the database to use 2-digit years.
    """
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        trades = db.query(models.Trade).all()
        for trade in trades:
            if trade.expiration_date:
                trade.expiration_date = datetime.strptime(convert_to_two_digit_year(trade.expiration_date.strftime('%m/%d/%Y')), "%m/%d/%y")
        db.commit()
        print("All trade expiration dates updated to 2-digit year format.")
    except Exception as e:
        print(f"Error updating expiration dates: {str(e)}")
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

def determine_trade_group(expiration_date: str) -> str:
    if not expiration_date:
        return "long_term_trader"
    
    try:
        # Try parsing with 2-digit year first
        exp_date = datetime.strptime(expiration_date, "%m/%d/%y").date()
    except ValueError:
        try:
            # If that fails, try with 4-digit year
            exp_date = datetime.strptime(expiration_date, "%m/%d/%Y").date()
        except ValueError:
            # If both fail, return default
            return "long_term_trader"
    
    days_to_expiration = (exp_date - datetime.now().date()).days
    
    if days_to_expiration < 7:
        return "day_trader"
    elif 8 <= days_to_expiration <= 90:
        return "swing_trader"
    else:
        return "long_term_trader"

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
    db = next(get_db())
    try:
        # Convert expiration_date to 2-digit year format if it's not already
        if expiration_date:
            expiration_date = convert_to_two_digit_year(expiration_date)
        
        # Determine trade group based on expiration date
        trade_group = determine_trade_group(expiration_date)
        
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
            trade_type="Buy to Open",
            status=models.TradeStatusEnum.OPEN,
            entry_price=entry_price,
            current_size=size,
            created_at=datetime.utcnow(),
            closed_at=None,
            exit_price=None,
            profit_loss=None,
            risk_reward_ratio=None,
            win_loss=None,
            configuration_id=config.id,
            is_contract=is_contract,
            is_day_trade=is_day_trade,
            strike=strike,
            expiration_date=exp_date if expiration_date else None,
        )
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)

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
        #if is_contract:
        #    embed.add_field(name="Contract Trade", value="Yes", inline=True)
        #if is_day_trade:
        #    embed.add_field(name="Day Trade", value="Yes", inline=True)
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
        # Log the error instead of sending an ephemeral message
        await log_to_channel(interaction.guild, f"Error in BTO command by {interaction.user.name}: {str(e)}")
    finally:
        db.close()

    # Instead of sending a generic response to the user, we'll defer the response and then do nothing
    await interaction.response.defer(ephemeral=True)

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
    db = next(get_db())
    try:
        # Convert expiration_date to 2-digit year format if it's not already
        if expiration_date:
            expiration_date = convert_to_two_digit_year(expiration_date)
        
        # Determine trade group based on expiration date
        trade_group = determine_trade_group(expiration_date)
        
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
            current_size=size,
            created_at=datetime.utcnow(),
            closed_at=None,
            exit_price=None,
            profit_loss=None,
            risk_reward_ratio=None,
            win_loss=None,
            configuration_id=config.id,
            is_contract=is_contract,
            is_day_trade=is_day_trade,
            strike=strike,
            expiration_date=exp_date if expiration_date else None,
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
        #embed.add_field(name="Trade Group", value=trade_group, inline=True)
        if expiration_date:
            embed.add_field(name="Exp. Date", value=expiration_date, inline=True)
        if strike:
            strike_display = f"${strike:,.2f}" if strike >= 0 else f"(${abs(strike):,.2f})"
            embed.add_field(name="Strike Price", value=strike_display, inline=True)
        #if is_contract:
        #    embed.add_field(name="Contract Trade", value="Yes", inline=True)
        #if is_day_trade:
        #    embed.add_field(name="Day Trade", value="Yes", inline=True)
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

    # Instead of sending a generic response to the user, we'll defer the response and then do nothing
    await interaction.response.defer(ephemeral=True)

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
            await interaction.response.defer(ephemeral=True)
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
        await interaction.response.defer(ephemeral=True)
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
            await interaction.response.defer(ephemeral=True)
            return

        db.delete(config)
        db.commit()

        await interaction.response.send_message(f"Trade configuration '{name}' removed successfully.", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed REMOVE_TRADE_CONFIG command: Trade configuration '{name}' removed successfully.")
    except Exception as e:
        logger.error(f"Error removing trade configuration: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in REMOVE_TRADE_CONFIG command by {interaction.user.name}: {str(e)}")
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
            await interaction.response.defer(ephemeral=True)
            return

        if not config.roadmap_channel_id:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed R command: No roadmap channel configured for trade group: {trade_group}")
            await interaction.response.defer(ephemeral=True)
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
        await interaction.response.defer(ephemeral=True)
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
            await interaction.response.defer(ephemeral=True)
            return

        if not config.update_channel_id:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed U command: No update channel configured for trade group: {trade_group}")
            await interaction.response.defer(ephemeral=True)
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
        await interaction.response.defer(ephemeral=True)
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
        await interaction.response.defer(ephemeral=True)

@bot.slash_command(name="send_embed", description="Send an embed with optional file attachment")
async def send_embed(
    interaction: discord.Interaction,
    title: discord.Option(str, description="The title of the embed"),
    description: discord.Option(str, description="The description/content of the embed (use \\n for new lines)"),
    channel: discord.Option(discord.TextChannel, description="The channel to send the embed to"),
    file: discord.Option(discord.Attachment, description="File to attach to the embed", required=False) = None
):
    await interaction.response.defer(ephemeral=True)
    
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
        
        await interaction.followup.send("Embed sent successfully!", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed SEND_EMBED command: Embed sent successfully!")
    except Exception as e:
        logger.error(f"Error in send_embed: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in SEND_EMBED command by {interaction.user.name}: {str(e)}")
        await interaction.response.defer(ephemeral=True)

# Add these functions near your other configuration functions

@bot.slash_command(name="set_watchlist_channel", description="Set the channel for watchlist updates")
async def set_watchlist_channel(
    interaction: discord.Interaction,
    channel: discord.Option(discord.TextChannel, description="The channel for watchlist updates")
):
    db = next(get_db())
    try:
        config = db.query(models.BotConfiguration).first()
        if not config:
            config = models.BotConfiguration(watchlist_channel_id=str(channel.id))
            db.add(config)
        else:
            config.watchlist_channel_id = str(channel.id)
        db.commit()
        await interaction.response.send_message(f"Watchlist channel set to {channel.mention}", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed SET_WATCHLIST_CHANNEL command: Watchlist channel set to {channel.mention}")
    except Exception as e:
        logger.error(f"Error setting watchlist channel: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in SET_WATCHLIST_CHANNEL command by {interaction.user.name}: {str(e)}")
        await interaction.response.defer(ephemeral=True)
    finally:
        db.close()

@bot.slash_command(name="set_ta_channel", description="Set the channel for technical analysis updates")
async def set_ta_channel(
    interaction: discord.Interaction,
    channel: discord.Option(discord.TextChannel, description="The channel for technical analysis updates")
):
    db = next(get_db())
    try:
        config = db.query(models.BotConfiguration).first()
        if not config:
            config = models.BotConfiguration(ta_channel_id=str(channel.id))
            db.add(config)
        else:
            config.ta_channel_id = str(channel.id)
        db.commit()
        await interaction.response.send_message(f"Technical analysis channel set to {channel.mention}", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed SET_TA_CHANNEL command: Technical analysis channel set to {channel.mention}")
    except Exception as e:
        logger.error(f"Error setting technical analysis channel: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in SET_TA_CHANNEL command by {interaction.user.name}: {str(e)}")
        await interaction.response.defer(ephemeral=True)
    finally:
        db.close()

@bot.slash_command(name="wl", description="Send a watchlist update")
async def watchlist_update(
    interaction: discord.Interaction,
    message: discord.Option(str, description="The watchlist update message")
):
    db = next(get_db())
    try:
        config = db.query(models.BotConfiguration).first()
        if not config or not config.watchlist_channel_id:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed WL command: Watchlist channel not configured. Use /set_watchlist_channel first.")
            await interaction.response.defer(ephemeral=True)
            return

        channel = interaction.guild.get_channel(int(config.watchlist_channel_id))
        if not channel:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed WL command: Configured watchlist channel not found.")
            await interaction.response.defer(ephemeral=True)
            return

        embed = discord.Embed(title="Watchlist Update", description=message, color=discord.Color.blue())
        embed.set_footer(text=f"Posted by {interaction.user.name}")
        await channel.send(embed=embed)
        await interaction.response.send_message("Watchlist update sent successfully.", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed WL command: Watchlist update sent successfully.")
    except Exception as e:
        logger.error(f"Error sending watchlist update: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in WL command by {interaction.user.name}: {str(e)}")
        await interaction.response.defer(ephemeral=True)
    finally:
        db.close()

@bot.slash_command(name="ta", description="Send a technical analysis update")
async def ta_update(
    interaction: discord.Interaction,
    message: discord.Option(str, description="The technical analysis update message")
):
    db = next(get_db())
    try:
        config = db.query(models.BotConfiguration).first()
        if not config or not config.ta_channel_id:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TA command: Technical analysis channel not configured. Use /set_ta_channel first.")
            await interaction.response.defer(ephemeral=True)
            return

        channel = interaction.guild.get_channel(int(config.ta_channel_id))
        if not channel:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TA command: Configured technical analysis channel not found.")
            await interaction.response.defer(ephemeral=True)
            return

        embed = discord.Embed(title="Technical Analysis Update", description=message, color=discord.Color.green())
        embed.set_footer(text=f"Posted by {interaction.user.name}")
        await channel.send(embed=embed)
        await interaction.response.send_message("Technical analysis update sent successfully.", ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TA command: Technical analysis update sent successfully.")
    except Exception as e:
        logger.error(f"Error sending technical analysis update: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in TA command by {interaction.user.name}: {str(e)}")
        await interaction.response.defer(ephemeral=True)
    finally:
        db.close()

# Add this at the end of your bot.py file
@bot.event
async def on_application_command_error(ctx, error):
    logger.error(f"An error occurred: {str(error)}")
    logger.error(traceback.format_exc())
    await log_to_channel(ctx.guild, f"Error in command {ctx.command.name} by {ctx.author.name}: {str(error)}")
    await ctx.defer(ephemeral=True)

@bot.slash_command(name="list", description="List open trades")
async def list_trades(interaction: discord.Interaction):
    db = next(get_db())
    try:
        open_trades = crud.get_trades(db, status=models.TradeStatusEnum.OPEN)
        if not open_trades:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed LIST command: No open trades found.")
            await interaction.response.defer(ephemeral=True)
            return

        paginator = TradePaginator(open_trades, interaction)
        await interaction.response.defer()
        await paginator.send_page()
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed LIST command: Trades list generated.")

    except Exception as e:
        logger.error(f"Error listing trades: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in LIST command by {interaction.user.name}: {str(e)}")
        await interaction.response.defer(ephemeral=True)
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
            await interaction.response.defer(ephemeral=True)
            return

        # If the trade has a 4-digit year expiration, update it to 2-digit year
        if trade.expiration_date:
            trade.expiration_date = datetime.strptime(convert_to_two_digit_year(trade.expiration_date.strftime('%m/%d/%Y')), "%m/%d/%y")

        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.id == trade.configuration_id).first()
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed EXIT command: Configuration for trade {trade_id} not found.")
            await interaction.response.defer(ephemeral=True)
            return

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
        db.commit()

        # Calculate profit/loss considering all transactions
        open_transactions = crud.get_transactions_for_trade(db, trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
        trim_transactions = crud.get_transactions_for_trade(db, trade_id, [models.TransactionTypeEnum.TRIM])
        
        total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
        total_open_size = sum(Decimal(t.size) for t in open_transactions)
        total_trimmed_size = sum(Decimal(t.size) for t in trim_transactions)
        
        average_cost = total_cost / total_open_size if total_open_size > 0 else 0
        
        # Calculate profit/loss from trims
        trim_profit_loss = sum((Decimal(t.amount) - average_cost) * Decimal(t.size) for t in trim_transactions)
        
        # Calculate profit/loss from final exit
        exit_profit_loss = (Decimal(exit_price) - average_cost) * current_size
        
        # Total profit/loss
        total_profit_loss = trim_profit_loss + exit_profit_loss
        trade.profit_loss = float(total_profit_loss)

        # Calculate profit/loss per share or per contract
        if trade.is_contract:
            profit_loss_per_unit = total_profit_loss / Decimal('100')  # Assuming 100 shares per contract
            unit_type = "contract"
        else:
            profit_loss_per_unit = total_profit_loss / (current_size + total_trimmed_size)
            unit_type = "share"

        # Determine win/loss
        if total_profit_loss > 0:
            trade.win_loss = models.WinLossEnum.WIN
        elif total_profit_loss < 0:
            trade.win_loss = models.WinLossEnum.LOSS
        else:
            trade.win_loss = models.WinLossEnum.BREAKEVEN

        db.commit()

        # Create an embed with the closed trade information
        embed = discord.Embed(title="Trade Closed", color=discord.Color.gold())
        
        # Add the one-liner at the top of the embed
        embed.description = create_trade_oneliner(trade)
        
        embed.add_field(name="Exit Price", value=f"${exit_price:.2f}", inline=True)
        embed.add_field(name="Final Size", value=current_size, inline=True)
        embed.add_field(name=f"P/L per {unit_type}", value=f"${profit_loss_per_unit:.2f}", inline=True)
        embed.add_field(name="Total Profit/Loss", value=f"${total_profit_loss:.2f}", inline=True)
        embed.add_field(name="Result", value=trade.win_loss.value.capitalize(), inline=True)

        if total_trimmed_size > 0:
            embed.add_field(name="Trimmed Size", value=total_trimmed_size, inline=True)
            embed.add_field(name="Trim Profit/Loss", value=f"${trim_profit_loss:.2f}", inline=True)

        # Set the footer to include the trade ID
        embed.set_footer(text=f"Trade ID: {trade_id}")

        # Send an ephemeral reply to the user
        await interaction.response.defer(ephemeral=True)

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
        await interaction.response.defer(ephemeral=True)
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
            await interaction.response.defer(ephemeral=True)
            return

        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.id == trade.configuration_id).first()
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed ADD command: Configuration for trade {trade_id} not found.")
            await interaction.response.defer(ephemeral=True)
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
        new_size = float(trade.current_size) + float(add_size)
        trade.current_size = str(new_size)

        db.commit()

        # Create an embed with the transaction information
        embed = discord.Embed(title="Added to Trade", color=discord.Color.teal())
        embed.description = create_trade_oneliner(trade)
        embed.add_field(name="Symbol", value=trade.symbol, inline=True)
        embed.add_field(name="Trade Type", value=trade.trade_type, inline=True)
        if trade.strike:
            embed.add_field(name="Strike", value=f"${trade.strike:.2f}", inline=True)
        if trade.expiration_date:
            embed.add_field(name="Exp. Date", value=trade.expiration_date.strftime('%m/%d/%y'), inline=True)
        embed.add_field(name="Add Price", value=f"${add_price:.2f}", inline=True)
        embed.add_field(name="Add Size", value=add_size, inline=True)
        embed.add_field(name="Previous Size", value=trade.current_size, inline=True)
        embed.add_field(name="New Total Size", value=f"{new_size:.2f}", inline=True)
        #if trade.is_contract:
        #    embed.add_field(name="Contract", value="Yes", inline=True)
        #if trade.is_day_trade:
        #    embed.add_field(name="Day Trade", value="Yes", inline=True)

        embed.set_footer(text=f"Trade ID: {trade.trade_id}")

        # Send an ephemeral reply to the user
        await interaction.response.defer(ephemeral=True)

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
        await interaction.response.defer(ephemeral=True)
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
            await interaction.response.defer(ephemeral=True)
            return

        config = db.query(models.TradeConfiguration).filter(models.TradeConfiguration.id == trade.configuration_id).first()
        if not config:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TRIM command: Configuration for trade {trade_id} not found.")
            await interaction.response.defer(ephemeral=True)
            return

        current_size = Decimal(trade.current_size)
        trim_size = Decimal(trim_size)

        if trim_size > current_size:
            await log_to_channel(interaction.guild, f"User {interaction.user.name} executed TRIM command: Trim size ({trim_size}) is greater than current trade size ({current_size}).")
            await interaction.response.defer(ephemeral=True)
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

        db.commit()

        # Calculate profit/loss for this trim
        open_transactions = crud.get_transactions_for_trade(db, trade_id, [models.TransactionTypeEnum.OPEN, models.TransactionTypeEnum.ADD])
        total_cost = sum(Decimal(t.amount) * Decimal(t.size) for t in open_transactions)
        average_cost = total_cost / sum(Decimal(t.size) for t in open_transactions)
        
        trim_profit_loss = (Decimal(trim_price) - average_cost) # DONT MULTIPLY BY TRIM SIZE * trim_size

        # Create an embed with the transaction information
        embed = discord.Embed(title="Trimmed Trade", color=discord.Color.orange())
        embed.description = create_trade_oneliner(trade)
        embed.add_field(name="Symbol", value=trade.symbol, inline=True)
        embed.add_field(name="Trade Type", value=trade.trade_type, inline=True)
        if trade.strike:
            embed.add_field(name="Strike", value=f"${trade.strike:.2f}", inline=True)
        if trade.expiration_date:
            embed.add_field(name="Exp. Date", value=trade.expiration_date.strftime('%m/%d/%y'), inline=True)
        embed.add_field(name="Trim Price", value=f"${trim_price:.2f}", inline=True)
        embed.add_field(name="Trim Size", value=str(trim_size), inline=True)
        embed.add_field(name="Previous Size", value=str(current_size), inline=True)
        embed.add_field(name="Remaining Size", value=f"{new_size:.2f}", inline=True)
        embed.add_field(name="P/L per", value=f"${trim_profit_loss:.2f}", inline=True)
        if trade.is_contract:
            embed.add_field(name="Contract", value="Yes", inline=True)
        if trade.is_day_trade:
            embed.add_field(name="Day Trade", value="Yes", inline=True)

        embed.set_footer(text=f"Trade ID: {trade.trade_id}")

        # Send an ephemeral reply to the user
        await interaction.response.defer(ephemeral=True)

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
        await interaction.response.defer(ephemeral=True)
    finally:
        db.close()

@bot.slash_command(name="os", description="Create an options strategy trade")
async def options_strategy(
    interaction: discord.Interaction,
    strategy_name: discord.Option(str, description="The name of the options strategy"),
    underlying_symbol: discord.Option(str, description="The underlying symbol for the options strategy"),
    leg1: discord.Option(str, description="Format: BTO/STO,STRIKE,MM/DD/YY,OPTION_TYPE,SIZE,PRICE"),
    leg2: discord.Option(str, description="Format: BTO/STO,STRIKE,MM/DD/YY,OPTION_TYPE,SIZE,PRICE"),
    leg3: discord.Option(str, description="Format: BTO/STO,STRIKE,MM/DD/YY,OPTION_TYPE,SIZE,PRICE") = None,
    leg4: discord.Option(str, description="Format: BTO/STO,STRIKE,MM/DD/YY,OPTION_TYPE,SIZE,PRICE") = None,
    note: discord.Option(str, description="Optional note from the trader") = None,
):
    db = next(get_db())
    try:
        # Parse leg1, leg2, leg3, leg4
        legs = [leg1, leg2]
        if leg3:
            legs.append(leg3)
        if leg4:
            legs.append(leg4)

        parsed_legs = []
        for leg in legs:
            try:
                trade_type, strike, expiration, option_type, size, price = leg.split(',')
                strike = float(strike)
                expiration = datetime.strptime(expiration, "%m/%d/%y")
                size = float(size)
                price = float(price)
                parsed_legs.append((trade_type, strike, expiration, option_type, size, price))
            except ValueError:
                await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS command: Invalid leg format: {leg}")
                await interaction.response.defer(ephemeral=True)
                return

        # Determine trade group based on expiration date
        trade_group = determine_trade_group(parsed_legs[0][2].strftime('%m/%d/%y'))
        
        config = get_configuration(db, trade_group)
        if not config:
            await interaction.response.send_message(f"No configuration found for trade group: {trade_group}", ephemeral=True)
            return

        # Create the strategy trade
        strategy_trade = models.StrategyTrade(
            name=strategy_name,
            underlying_symbol=underlying_symbol,
            created_at=datetime.utcnow(),
            note=note
        )
        db.add(strategy_trade)
        db.commit()
        db.refresh(strategy_trade)

        # Create individual trades for each leg
        for trade_type, strike, expiration, option_type, size, price in parsed_legs:
            new_trade = models.Trade(
                symbol=underlying_symbol,
                trade_type=trade_type,
                status=models.TradeStatusEnum.OPEN,
                entry_price=price,
                current_size=size,
                created_at=datetime.utcnow(),
                closed_at=None,
                exit_price=None,
                profit_loss=None,
                risk_reward_ratio=None,
                win_loss=None,
                configuration_id=config.id,
                is_contract=True,
                is_day_trade=False,
                strike=strike,
                expiration_date=expiration,
                strategy_trade_id=strategy_trade.id
            )
            db.add(new_trade)
            db.commit()
            db.refresh(new_trade)

            # Add the initial transaction
            new_transaction = models.Transaction(
                trade_id=new_trade.trade_id,
                transaction_type=models.TransactionTypeEnum.OPEN,
                amount=price,
                size=size,
                created_at=datetime.utcnow()
            )
            db.add(new_transaction)
            db.commit()

        # Create an embed with the strategy trade information
        embed = discord.Embed(title=f"New Options Strategy: {strategy_name}", color=discord.Color.blue())
        embed.add_field(name="Underlying Symbol", value=underlying_symbol, inline=True)
        
        for i, (trade_type, strike, expiration, option_type, size, price) in enumerate(parsed_legs, 1):
            leg_info = f"{trade_type} {size} {underlying_symbol} {strike} {option_type} {expiration.strftime('%m/%d/%y')} @ ${price:.2f}"
            embed.add_field(name=f"Leg {i}", value=leg_info, inline=False)

        if note:
            embed.add_field(name="Note", value=note, inline=False)

        embed.set_footer(text=f"Strategy ID: {strategy_trade.id}")

        # Send the embed to the configured channel with role ping
        channel = interaction.guild.get_channel(int(config.channel_id))
        role = interaction.guild.get_role(int(config.role_id))
        await channel.send(content=f"{role.mention}", embed=embed)

        #await interaction.response.send_message("Options strategy trade created successfully!", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await log_to_channel(interaction.guild, f"User {interaction.user.name} executed OS command: Options strategy {strategy_name} created successfully.")

    except Exception as e:
        logger.error(f"Error creating options strategy trade: {str(e)}")
        logger.error(traceback.format_exc())
        await log_to_channel(interaction.guild, f"Error in OS command by {interaction.user.name}: {str(e)}")
        await interaction.response.send_message("An error occurred while creating the options strategy trade.", ephemeral=True)
    finally:
        db.close()

async def run_bot():
    #if TEST_MODE:
    #    token = os.getenv('TEST_TOKEN')
    #else:   
    token = os.getenv('DISCORD_TOKEN')
    print("token", token)
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set.")
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    try:
        # Run the update_expiration_dates function before starting the bot
        update_expiration_dates()
        
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