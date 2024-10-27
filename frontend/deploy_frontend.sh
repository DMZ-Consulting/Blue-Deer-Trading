#!/bin/bash

set -x  # Enable debug mode to see all commands being executed

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to the frontend directory
cd "$SCRIPT_DIR"

# Clean the existing .next directory
echo "Cleaning .next directory..."
rm -rf .next

# Install dependencies
echo "Installing dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies"
    exit 1
fi

# Build the frontend with debug output
echo "Building the frontend..."
NODE_ENV=production npm run build -- --debug
if [ $? -ne 0 ]; then
    echo "Failed to build the frontend"
    exit 1
fi

# List contents of .next directory
echo "Contents of .next directory:"
ls -la .next/

# Verify the build exists and has required files
if [ ! -d ".next/static" ] || [ ! -f ".next/build-manifest.json" ]; then
    echo "Build appears incomplete. Missing required files."
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
NODE_ENV=production pm2 start npm --name "BlueDeerTradingFrontend" -- start

# Verify the process started
if ! pm2 list | grep -q "BlueDeerTradingFrontend"; then
    echo "Failed to start the frontend process"
    exit 1
fi

echo "Frontend deployed and started successfully!"