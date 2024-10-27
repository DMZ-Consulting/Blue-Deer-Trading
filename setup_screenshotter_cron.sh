#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Path to the run_screenshotter.sh script
SCREENSHOTTER_SCRIPT="$SCRIPT_DIR/screenshotter/run_screenshotter.sh"

# Check if the run_screenshotter.sh script exists
if [ ! -f "$SCREENSHOTTER_SCRIPT" ]; then
    echo "Error: $SCREENSHOTTER_SCRIPT does not exist."
    exit 1
fi

# Make sure the script is executable
chmod +x "$SCREENSHOTTER_SCRIPT"

# Create a temporary file for the new crontab
TEMP_CRON=$(mktemp)

# Export the current crontab to the temporary file
crontab -l > "$TEMP_CRON"

# Check if the cron job already exists
if grep -q "$SCREENSHOTTER_SCRIPT" "$TEMP_CRON"; then
    echo "Cron job for screenshotter already exists. No changes made."
else
    # Add the new cron job to run at 5 PM EST (10 PM UTC) daily
    echo "0 22 * * * $SCREENSHOTTER_SCRIPT" >> "$TEMP_CRON"

    # Install the new crontab
    crontab "$TEMP_CRON"

    echo "Cron job for screenshotter has been added successfully."
fi

# Remove the temporary file
rm "$TEMP_CRON"

echo "Screenshotter cron job setup complete."
