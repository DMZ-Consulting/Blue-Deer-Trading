# type: ignore[type-arg]

import discord
from discord.ext import commands
import logging
import traceback
import json
from datetime import datetime

from ..supabase_client import reopen_trade

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_logging_cog(self):
        return self.bot.get_cog('LoggingCog')

    async def get_utility_cog(self):
        return self.bot.get_cog('UtilityCog')

    @commands.slash_command(name="admin_reopen_trade", description="Reopen a trade using a trade ID")
    async def admin_reopen_trade(
        self,
        ctx: discord.ApplicationContext,
        trade_id: discord.Option(str, description="The ID of the trade to reopen"),
    ):
        await ctx.defer()

        try:
            logging_cog = await self.get_logging_cog()
            utility_cog = await self.get_utility_cog()

            # Reopen trade using Supabase function
            reopened_trade = await reopen_trade(trade_id)
            if not reopened_trade:
                await ctx.followup.send(f"Trade {trade_id} not found or could not be reopened.", ephemeral=True)
                return

            # Create embed
            embed = discord.Embed(title="Trade Reopened", color=discord.Color.green())
            embed.add_field(name="Trade ID", value=trade_id, inline=False)
            embed.add_field(name="Symbol", value=reopened_trade['symbol'], inline=True)
            embed.add_field(name="Size", value=utility_cog.format_size(reopened_trade['size']), inline=True)
            embed.add_field(name="Entry Price", value=f"${float(reopened_trade['entry_price']):.2f}", inline=True)
            
            await utility_cog.send_embed_by_configuration_id(ctx, reopened_trade['configuration_id'], embed)
            await logging_cog.log_to_channel(ctx.guild, f"User {ctx.user.name} executed ADMIN_REOPEN_TRADE command: Trade {trade_id} reopened successfully.")

        except Exception as e:
            logger.error(f"Error reopening trade: {str(e)}")
            logger.error(traceback.format_exc())
            await ctx.followup.send(f"Error reopening trade: {str(e)}", ephemeral=True)
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in ADMIN_REOPEN_TRADE command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="add_role_to_users", description="Add a role to all users who have a required role")
    async def add_role_to_users(
        self,
        ctx: discord.ApplicationContext,
        role_to_add: discord.Option(discord.Role, description="The role to add to users"),
        required_role: discord.Option(discord.Role, description="Users must have this role to receive the new role"),
    ):
        await ctx.defer()

        try:
            logging_cog = await self.get_logging_cog()
            
            # Get all members with the required role
            members_with_role = [member for member in ctx.guild.members if required_role in member.roles]
            
            # Add the new role to each member
            success_count = 0
            for member in members_with_role:
                try:
                    await member.add_roles(role_to_add)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to add role to {member.name}: {str(e)}")
                    continue

            # Send response
            await ctx.followup.send(
                f"Added role {role_to_add.name} to {success_count} members who had the role {required_role.name}",
                ephemeral=True
            )
            await logging_cog.log_to_channel(
                ctx.guild,
                f"User {ctx.user.name} executed ADD_ROLE_TO_USERS command: Added {role_to_add.name} to {success_count} members with {required_role.name}"
            )

        except Exception as e:
            logger.error(f"Error in add_role_to_users: {str(e)}")
            logger.error(traceback.format_exc())
            await ctx.followup.send(f"Error adding roles: {str(e)}", ephemeral=True)
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in ADD_ROLE_TO_USERS command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="scrape_channel", description="Scrape messages from a channel and save them to a file")
    async def scrape_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, description="The channel to scrape messages from"),
        limit: discord.Option(int, description="Maximum number of messages to scrape", min_value=1, max_value=10000) = 1000,
    ):
        await ctx.defer()

        try:
            logging_cog = await self.get_logging_cog()
            
            messages = []
            async for message in channel.history(limit=limit):
                messages.append({
                    'id': message.id,
                    'content': message.content,
                    'author': str(message.author),
                    'timestamp': message.created_at.isoformat(),
                    'attachments': [a.url for a in message.attachments],
                    'embeds': [e.to_dict() for e in message.embeds]
                })

            # Save to file
            filename = f"channel_scrape_{channel.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)

            await ctx.followup.send(
                f"Successfully scraped {len(messages)} messages from {channel.mention}. Saved to {filename}",
                ephemeral=True
            )
            await logging_cog.log_to_channel(
                ctx.guild,
                f"User {ctx.user.name} executed SCRAPE_CHANNEL command: Scraped {len(messages)} messages from {channel.name}"
            )

        except Exception as e:
            logger.error(f"Error scraping channel: {str(e)}")
            logger.error(traceback.format_exc())
            await ctx.followup.send(f"Error scraping channel: {str(e)}", ephemeral=True)
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in SCRAPE_CHANNEL command by {ctx.user.name}: {str(e)}")

    @commands.slash_command(name="unsync_resync", description="Unsync and resync commands for a guild")
    async def unsync_resync(
        self,
        ctx: discord.ApplicationContext,
        guild_id: discord.Option(str, description="The ID of the guild to unsync/resync commands for") = None,
    ):
        await ctx.defer()

        try:
            logging_cog = await self.get_logging_cog()
            
            if guild_id:
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    await ctx.followup.send(f"Guild with ID {guild_id} not found.", ephemeral=True)
                    return
            else:
                guild = ctx.guild

            # Unsync commands
            self.bot.tree.clear_commands(guild=guild)
            await self.bot.tree.sync(guild=guild)
            
            # Resync commands
            await self.bot.tree.sync(guild=guild)

            await ctx.followup.send(f"Successfully unsynced and resynced commands for guild {guild.name}", ephemeral=True)
            await logging_cog.log_to_channel(
                ctx.guild,
                f"User {ctx.user.name} executed UNSYNC_RESYNC command: Commands unsynced and resynced for guild {guild.name}"
            )

        except Exception as e:
            logger.error(f"Error in unsync_resync: {str(e)}")
            logger.error(traceback.format_exc())
            await ctx.followup.send(f"Error unsyncing/resyncing commands: {str(e)}", ephemeral=True)
            if logging_cog:
                await logging_cog.log_to_channel(ctx.guild, f"Error in UNSYNC_RESYNC command by {ctx.user.name}: {str(e)}")

def setup(bot):
    bot.add_cog(AdminCog(bot)) 