# type: ignore[type-arg]

import discord
from discord.ext import commands
import logging
import traceback
from datetime import datetime

from ..supabase_client import (
    get_verification_configs,
    add_verification_config,
    add_verification    
)

logger = logging.getLogger(__name__)

class VerificationModal(discord.ui.Modal):
    def __init__(self, bot, terms_link: str, terms_summary: str, role_to_remove: discord.Role, role_to_add: discord.Role):
        super().__init__(title="Verification Form")
        self.bot = bot
        self.terms_link = terms_link
        self.terms_summary = terms_summary
        self.role_to_remove = role_to_remove
        self.role_to_add = role_to_add

        self.agree_to_terms = discord.ui.InputText(
            label="Agree by typing 'I AGREE'.",
            placeholder="Type 'I AGREE' to agree",
            required=True,
            min_length=7,
            max_length=7
        )
        self.add_item(self.agree_to_terms)

        self.full_name = discord.ui.InputText(
            label="Full Name",
            placeholder="Enter your full name",
            required=True,
            min_length=2,
            max_length=100
        )
        self.add_item(self.full_name)

        self.email = discord.ui.InputText(
            label="Email Address",
            placeholder="Enter your email address",
            required=True,
            min_length=5,
            max_length=100
        )
        self.add_item(self.email)

    async def callback(self, interaction: discord.Interaction):
        if self.agree_to_terms.value.upper() != "I AGREE":
            await interaction.response.send_message("You must agree to the terms to proceed.", ephemeral=True)
            return

        try:
            # Remove unverified role
            if self.role_to_remove:
                await interaction.user.remove_roles(self.role_to_remove)

            # Add verified role
            if self.role_to_add:
                await interaction.user.add_roles(self.role_to_add)

            # Log verification
            logging_cog = self.bot.get_cog('LoggingCog')
            if logging_cog:
                embed = discord.Embed(
                    title="User Verification",
                    description=f"User {interaction.user.name} has been verified",
                    color=discord.Color.green()
                )
                embed.add_field(name="Full Name", value=self.full_name.value, inline=False)
                embed.add_field(name="Email", value=self.email.value, inline=False)
                await logging_cog.log_to_channel(interaction.guild, None, embed=embed)

            await interaction.response.send_message(
                "Thank you for verifying! Your roles have been updated.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in verification modal callback: {str(e)}")
            logger.error(traceback.format_exc())
            await interaction.response.send_message(
                "An error occurred during verification. Please try again or contact an administrator.",
                ephemeral=True
            )
            if logging_cog:
                await logging_cog.log_to_channel(
                    interaction.guild,
                    f"Error in verification modal callback for user {interaction.user.name}: {str(e)}"
                )

class VerificationButton(discord.ui.Button):
    def __init__(self):
        # Use a simple, consistent custom_id
        super().__init__(
            label="Start Verification",
            style=discord.ButtonStyle.success,
            custom_id="verification_button"
        )
        
    # Remove the callback method - we'll handle it globally

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerificationButton())

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.verification_configs = {}  # Store configs by message_id for quick lookup
        self.bot.add_listener(self.on_ready, "on_ready")
        self.bot.add_listener(self.on_interaction, "on_interaction")
        
    async def on_ready(self):
        """Called when the bot is ready, load verification configs"""
        await self.load_verification_configs()
        logger.info("Verification configs loaded on bot ready")
        
    async def on_interaction(self, interaction: discord.Interaction):
        """Global interaction handler for verification buttons"""
        if not interaction.data:
            return
            
        custom_id = interaction.data.get('custom_id')
        if custom_id != "verification_button":
            return
            
        # Find the config for this message
        message_id = str(interaction.message.id)
        config = self.verification_configs.get(message_id)
        
        if not config:
            logger.warning(f"No verification config found for message {message_id}")
            await interaction.response.send_message("This verification button is not properly configured. Please contact an administrator.", ephemeral=True)
            return
            
        # Get the roles
        guild = interaction.guild
        role_to_remove = guild.get_role(int(config['role_to_remove_id'])) if config.get('role_to_remove_id') else None
        role_to_add = guild.get_role(int(config['role_to_add_id'])) if config.get('role_to_add_id') else None
        
        # Show the verification modal
        modal = VerificationModal(
            self.bot,
            config.get('terms_link', ''),
            config.get('terms_summary', ''),
            role_to_remove,
            role_to_add
        )
        
        await interaction.response.send_modal(modal)

    async def load_verification_configs(self):
        """Load all verification configurations from database on startup"""
        try:
            # Get all verification configs from database
            configs = await get_verification_configs()
            logger.info(f"Found {len(configs)} verification configs to load")
            
            # Store configs by message_id for quick lookup
            self.verification_configs = {config['message_id']: config for config in configs}
            
            # Register a single persistent view for all verification buttons
            self.bot.add_view(VerificationView())
            
            logger.info(f"Registered global verification view for {len(configs)} messages")
            
        except Exception as e:
            logger.error(f"Error in load_verification_configs: {str(e)}")
            logger.error(traceback.format_exc())

    async def get_logging_cog(self):
        return self.bot.get_cog('LoggingCog')

    @commands.slash_command(name="setup_verification", description="Set up verification message with terms and conditions")
    async def setup_verification(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, description="The channel to send the verification message in"),
        terms_link: discord.Option(str, description="Link to the full terms and conditions"),
        terms_summary: discord.Option(str, description="A brief summary of the terms"),
        role_to_remove: discord.Option(discord.Role, description="Role to remove when verified"),
        role_to_add: discord.Option(discord.Role, description="Role to add when verified"),
        log_channel: discord.Option(discord.TextChannel, description="Channel to log verifications in"),
    ):
        await ctx.defer()

        try:
            logging_cog = await self.get_logging_cog()

            # Create embed for verification message
            embed = discord.Embed(
                title="Verification Required",
                description=(
                    f"Please read our terms and conditions before proceeding:\n\n"
                    f"**Terms Summary:**\n{terms_summary}\n\n"
                    f"**Full Terms:**\n[CLICK HERE]({terms_link})\n\n"
                    f"Click the button below to verify and agree to the terms."
                ),
                color=discord.Color.blue()
            )

            # Create a simple view with the verification button
            view = VerificationView()

            # Send verification message
            verification_message = await channel.send(embed=embed, view=view)
            
            # Create config
            config = {
                'channel_id': str(channel.id),
                'message_id': str(verification_message.id),
                'role_to_remove_id': str(role_to_remove.id),
                'role_to_add_id': str(role_to_add.id),
                'log_channel_id': str(log_channel.id),
            }
            
            # Store in memory
            self.verification_configs[str(verification_message.id)] = config

            # Save verification configuration to database
            await add_verification_config(config)

            await ctx.followup.send(
                f"Verification message has been set up in {channel.mention}. "
                f"Verifications will be logged in {log_channel.mention}.",
                ephemeral=True
            )
            await logging_cog.log_to_channel(
                ctx.guild,
                f"User {ctx.user.name} executed SETUP_VERIFICATION command: Verification system has been set up."
            )

        except Exception as e:
            logger.error(f"Error setting up verification: {str(e)}")
            logger.error(traceback.format_exc())
            await ctx.followup.send(f"Error setting up verification: {str(e)}", ephemeral=True)
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in SETUP_VERIFICATION command by {ctx.user.name}: {str(e)}")

def setup(bot):
    bot.add_cog(VerificationCog(bot)) 