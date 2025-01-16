import asyncio
import os
from dotenv import load_dotenv
from app.bot import bot

# Load environment variables
load_dotenv()

# Get the token
token = os.getenv('DISCORD_TOKEN')
if not token:
    raise ValueError("No Discord token found in environment variables")

try:
    bot.run(token)
except KeyboardInterrupt:
    print("Bot shutting down...")
except Exception as e:
    print(f"Error running bot: {str(e)}")
    raise 