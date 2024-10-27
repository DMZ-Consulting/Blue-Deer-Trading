#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "Starting/Restarting Blue Deer Trading application..."

# Start or restart the backend (Discord bot)
echo "Starting/restarting the backend (Discord bot)..."
bash "$SCRIPT_DIR/discord_bot/start_bot.sh" restart

# Start or restart the frontend
echo "Starting/restarting the frontend..."
bash "$SCRIPT_DIR/frontend/start_frontend.sh" restart

# Start or restart the screenshotter
#echo "Starting/restarting the screenshotter..."
#bash "$SCRIPT_DIR/screenshotter/run_screenshotter.sh" restart

echo "All components of Blue Deer Trading have been started or restarted!"
