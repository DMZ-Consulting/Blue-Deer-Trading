# type: ignore[type-arg]

import discord
from discord.ext import commands
import logging
import traceback
from datetime import datetime

from ..supabase_client import (
    get_verification_config,
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
            label="Do you agree to the terms? (Yes/No)",
            placeholder="Type 'Yes' to agree",
            required=True,
            min_length=2,
            max_length=3
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
        if self.agree_to_terms.value.lower() != "yes":
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
                await logging_cog.log_to_channel(
                    interaction.guild,
                    f"User {interaction.user.name} has been verified:\n"
                    f"- Full Name: {self.full_name.value}\n"
                    f"- Email: {self.email.value}"
                )

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
    def __init__(self, bot, terms_link: str, terms_summary: str, role_to_remove: discord.Role, role_to_add: discord.Role):
        super().__init__(
            label="Start Verification",
            style=discord.ButtonStyle.success,
            custom_id="verify_button"
        )
        self.bot = bot
        self.terms_link = terms_link
        self.terms_summary = terms_summary
        self.role_to_remove = role_to_remove
        self.role_to_add = role_to_add

    async def callback(self, interaction: discord.Interaction):
        modal = VerificationModal(
            self.bot,
            self.terms_link,
            self.terms_summary,
            self.role_to_remove,
            self.role_to_add
        )
        await interaction.response.send_modal(modal)

class VerificationView(discord.ui.View):
    def __init__(self, bot, terms_link: str, terms_summary: str, role_to_remove: discord.Role, role_to_add: discord.Role):
        super().__init__(timeout=None)
        self.add_item(VerificationButton(bot, terms_link, terms_summary, role_to_remove, role_to_add))

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
                    f"**Full Terms:**\n{terms_link}\n\n"
                    f"Click the button below to verify and agree to the terms."
                ),
                color=discord.Color.blue()
            )

            # Create view with verification button
            view = VerificationView(
                self.bot,
                terms_link,
                terms_summary,
                role_to_remove,
                role_to_add
            )

            # Send verification message
            verification_message = await channel.send(embed=embed, view=view)

            # Save verification configuration
            await add_verification_config({
                'channel_id': str(channel.id),
                'message_id': str(verification_message.id),
                'role_to_remove_id': str(role_to_remove.id),
                'role_to_add_id': str(role_to_add.id),
                'log_channel_id': str(log_channel.id)
            })

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