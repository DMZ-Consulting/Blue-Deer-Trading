#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to the frontend directory
cd "$SCRIPT_DIR"

# Install dependencies
echo "Installing dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies"
    exit 1
fi

# Build the frontend
echo "Building the frontend..."
npm run build
if [ $? -ne 0 ]; then
    echo "Failed to build the frontend"
    exit 1
fi

# Verify the build exists
if [ ! -d ".next" ]; then
    echo "Build directory .next not found after build"
    exit 1
fi

# Check if PM2 is installed, if not install it
if ! command -v pm2 &> /dev/null; then
    echo "PM2 is not installed. Installing PM2..."
    npm install pm2@latest -g
    if [ $? -ne 0 ]; then
        echo "Failed to install PM2"
        exit 1
    fi
fi

# Stop existing process if it exists
if pm2 list | grep -q "BlueDeerTradingFrontend"; then
    echo "Stopping existing frontend process..."
    pm2 stop BlueDeerTradingFrontend
    pm2 delete BlueDeerTradingFrontend
fi

# Start the frontend using PM2
echo "Starting the frontend with PM2..."
pm2 start npm --name "BlueDeerTradingFrontend" -- start

# Verify the process started
if ! pm2 list | grep -q "BlueDeerTradingFrontend"; then
    echo "Failed to start the frontend process"
    exit 1
fi

echo "Frontend deployed and started successfully!"