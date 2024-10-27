#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

# Navigate to the project directory
cd "$PROJECT_DIR"

# Check if virtual environment exists, if not create one
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source ../venv/bin/activate

# Install or upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r discord_bot/backend/app/requirements.txt

# Check if PM2 is installed, if not install it
if ! command -v pm2 &> /dev/null; then
    echo "PM2 is not installed. Installing PM2..."
    npm install pm2@latest -g
fi

# Start or restart the bot using PM2
if pm2 list | grep -q "BlueDeerTradingBot"; then
    echo "Restarting the bot with PM2..."
    pm2 restart BlueDeerTradingBot
else
    echo "Starting the bot with PM2..."
    pm2 start discord_bot/backend/run.sh --name "BlueDeerTradingBot" --interpreter bash
fi

echo "Bot started/restarted successfully!"
