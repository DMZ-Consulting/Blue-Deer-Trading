#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to the screenshotter directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists, if not create one
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check if PM2 is installed, if not install it
if ! command -v pm2 &> /dev/null; then
    echo "PM2 is not installed. Installing PM2..."
    npm install pm2@latest -g
fi

# Start or restart the screenshotter using PM2
if pm2 list | grep -q "BlueDeerScreenshotter"; then
    echo "Restarting the screenshotter with PM2..."
    pm2 restart BlueDeerScreenshotter
else
    echo "Starting the screenshotter with PM2..."
    pm2 start screenshotter.py --name "BlueDeerScreenshotter" --interpreter python
fi

echo "Screenshotter started/restarted successfully!"
