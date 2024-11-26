#!/bin/bash

# Get the directory of the current script
#SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to the screenshotter directory
#cd "$SCRIPT_DIR"

#sudo apt-get install -y firefox-geckodriver

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

# Run the screenshotter and log output
echo "Starting the screenshotter..."
python screenshotter.py > screenshotter.log

echo "Screenshotter started successfully! Logs are being written to screenshotter.log."
