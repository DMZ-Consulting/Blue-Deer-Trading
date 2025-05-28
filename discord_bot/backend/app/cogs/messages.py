import discord
from discord.ext import commands
import logging
from datetime import datetime, date
import re
import traceback
import os
import openai

from ..supabase_client import supabase

logger = logging.getLogger(__name__)

class MessagesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="get_message_details", description="Get the details of a message")
    async def get_message_details(self, 
                                  ctx: discord.ApplicationContext, 
                                  message_id: discord.Option(str, description="The ID of the message to get the details of")):
        message = await ctx.channel.fetch_message(message_id)
        await ctx.send(f"Message ID: {message_id}\nMessage Content: {message.content}\nMessage Attachments: {message.attachments}\nMessage Embeds: {message.embeds}\nMessage Flags: {message.flags}")

    @commands.slash_command(name="transcribe_message", description="Transcribe a message")
    async def transcribe_message(self, ctx: discord.ApplicationContext, message_id: str):
        message = await ctx.channel.fetch_message(message_id)
        if message.attachments and message.attachments[0].filename.endswith(".mp3") or message.attachments[0].filename.endswith(".ogg"):
            await ctx.respond("This is a voice message", ephemeral=True)
            await self.transcribe_voice_message(ctx, message.attachments[0])

        else:
            await ctx.respond("This is a not a voice message", ephemeral=True)

    async def transcribe_voice_message(self, ctx: discord.ApplicationContext, attachment: discord.Attachment):
        filename = f"voice_message_{attachment.id}.{attachment.filename.split('.')[-1]}"
        with open(filename, "wb") as f:
            await attachment.save(f)

        if attachment.filename.endswith(".ogg"):
            import subprocess
            mp3_filename = filename.replace(".ogg", ".mp3")
            subprocess.run(["ffmpeg", "-i", filename, mp3_filename])
            os.remove(filename)  # Remove the original .ogg file
            filename = mp3_filename  # Update filename to use the .mp3 version

        client = openai.OpenAI()
        audio_file= open(filename, "rb")

        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe", 
            file=audio_file
        )

        # remove the file
        os.remove(filename)
        
        await ctx.respond(transcription.text, ephemeral=True)

def setup(bot):
    bot.add_cog(MessagesCog(bot)) 