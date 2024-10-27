#!/bin/bash

# Set the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to the script directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install or upgrade requirements
echo "Installing/upgrading requirements..."
pip install -r requirements.txt

# Run the screenshotter script
echo "Running screenshotter.py..."
python screenshotter.py

# Deactivate the virtual environment
deactivate

echo "Script execution completed."

