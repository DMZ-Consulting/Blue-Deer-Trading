#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
set -x  # Enable debug mode to see all commands being executed

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to the frontend directory
cd "$SCRIPT_DIR"

# Check if the build exists
if [ ! -d ".next" ] || [ ! -f ".next/build-manifest.json" ]; then
    echo "Error: Build not found. Please run deploy_frontend.sh first to build the frontend."
    exit 1
fi

# Check if PM2 is installed, if not install it
if ! command -v pm2 &> /dev/null; then
    echo "PM2 is not installed. Installing PM2..."
    npm install pm2@latest -g
fi

# Stop existing process if it exists
if pm2 list | grep -q "BlueDeerTradingFrontend"; then
    echo "Stopping existing frontend process..."
    pm2 stop BlueDeerTradingFrontend
    pm2 delete BlueDeerTradingFrontend
fi

# Start the frontend using PM2
echo "Starting the frontend with PM2..."
NODE_ENV=production pm2 start npm --name "BlueDeerTradingFrontend" -- start

# Verify the process started
if pm2 list | grep -q "BlueDeerTradingFrontend"; then
    echo "Frontend started successfully!"
else
    echo "Failed to start the frontend process"
    exit 1
fi
