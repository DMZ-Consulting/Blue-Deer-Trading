import asyncio
import os
from dotenv import load_dotenv
from app.bot import run_bot
import time
# Load environment variables
load_dotenv()

# Get the token
token = os.getenv('DISCORD_TOKEN')
if not token:
    raise ValueError("No Discord token found in environment variables")

def main():
    try:
        run_bot(token)
    except KeyboardInterrupt:
        print("Bot shutting down...")
    except Exception as e:
        print(f"Error running bot: {str(e)}")
        raise

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error running bot: {str(e)}")
            raise
        time.sleep(1)