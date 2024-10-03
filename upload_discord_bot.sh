#!/bin/bash

# Set the project directory (parent of discord_bot)
PROJECT_DIR="/Users/dylanzeller/Documents/dev/Blue Deer Trading"

# Change to the project directory
cd "$PROJECT_DIR"

# Set the source directory (discord_bot)
SOURCE_DIR="discord_bot"

# Set the output zip file name
OUTPUT_ZIP="discord_bot_backup.zip"

# Set VPS details
VPS_USER="root"
VPS_IP="66.135.5.217"
VPS_DESTINATION="/root/BlueDeerTradingBot"

# Ensure start_bot.sh is in the discord_bot directory
if [ ! -f "$SOURCE_DIR/start_bot.sh" ]; then
    echo "Moving start_bot.sh to discord_bot directory..."
    mv start_bot.sh "$SOURCE_DIR/"
fi

# Create the zip file
zip -r "$OUTPUT_ZIP" "$SOURCE_DIR" \
    -x "*/venv/*" \
    -x "*.db" \
    -x "*/images/*" \
    -x "*/__pycache__/*"

echo "Zip file created: $OUTPUT_ZIP"

# SCP the zip file to VPS
echo "Copying zip file to VPS..."
scp "$OUTPUT_ZIP" "$VPS_USER@$VPS_IP:$VPS_DESTINATION"

if [ $? -eq 0 ]; then
    echo "Zip file successfully copied to VPS"
else
    echo "Failed to copy zip file to VPS"
fi

# Optionally, remove the local zip file after successful transfer
# rm "$OUTPUT_ZIP"