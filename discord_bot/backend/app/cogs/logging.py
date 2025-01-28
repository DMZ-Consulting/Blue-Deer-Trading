import discord
from discord.ext import commands
import logging
import os
import traceback

from ..supabase_client import supabase

logger = logging.getLogger(__name__)

class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_command_usage(self, interaction: discord.Interaction, command_name: str, params: dict):
        """Log command usage to the log channel."""
        try:
            # Format parameters, excluding any None values
            param_str = ', '.join(f"{k}={v}" for k, v in params.items() if v is not None)
            log_message = f"Command executed: /{command_name} by {interaction.user.name} ({interaction.user.id})\nParameters: {param_str}"
            await self.log_to_channel(interaction.guild, log_message)
        except Exception as e:
            logger.error(f"Error logging command usage: {str(e)}")
            logger.error(traceback.format_exc())

    async def log_to_channel(self, guild, message):
        """Log a message to the appropriate logging channel."""
        try:
            if os.getenv("LOCAL_TEST", "false").lower() == "true":
                log_channel_id = 1283513132546920650
            else:
                # Get log channel from Supabase configuration
                config = await supabase.table('bot_configurations').select('log_channel_id').single().execute()
                config = config.data if config.data else None
                if config and config.get('log_channel_id', None):
                    log_channel_id = config.get('log_channel_id')
                else:
                    logger.error("No log channel ID found in Supabase configuration")
                    return

            log_channel = guild.get_channel(int(log_channel_id))
            if log_channel:
                await log_channel.send(message)
        except Exception as e:
            logger.error(f"Error logging to channel: {str(e)}")
            logger.error(traceback.format_exc())

def setup(bot):
    bot.add_cog(LoggingCog(bot)) 