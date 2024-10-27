#!/bin/bash

# Set the path to your project directory
#PROJECT_DIR="/root/BlueDeerTradingBot/prototype"

# Navigate to the project directory
#cd "$PROJECT_DIR"

# Check if virtual environment exists, if not create one
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install or upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r backend/app/requirements.txt

# Check if PM2 is installed, if not install it
if ! command -v pm2 &> /dev/null; then
    echo "PM2 is not installed. Installing PM2..."
    npm install pm2@latest -g
fi

# Start the bot using PM2
echo "Starting the bot with PM2..."
pm2 start backend/run.sh --name "BlueDeerTradingBot" --interpreter bash

echo "Bot started successfully!"