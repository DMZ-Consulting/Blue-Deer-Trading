#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to the frontend directory
cd "$SCRIPT_DIR"

# Install dependencies
echo "Installing dependencies..."
npm install

# Build the frontend
echo "Building the frontend..."
npm run build

# Check if PM2 is installed, if not install it
if ! command -v pm2 &> /dev/null; then
    echo "PM2 is not installed. Installing PM2..."
    npm install pm2@latest -g
fi

# Start or restart the frontend using PM2
if pm2 list | grep -q "BlueDeerTradingFrontend"; then
    echo "Restarting the frontend with PM2..."
    pm2 restart BlueDeerTradingFrontend
else
    echo "Starting the frontend with PM2..."
    pm2 start npm --name "BlueDeerTradingFrontend" -- start
fi

echo "Frontend deployed and started/restarted successfully!"
