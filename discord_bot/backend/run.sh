#!/bin/bash

# Change to the directory containing the app
cd "$(dirname "$0")"

# Check if the database file exists
if [ ! -f local.db ]; then
  # Run the database initialization script
  python3 -m app.init_db
fi

# Start the uvicorn server
uvicorn app.main:app --host 0.0.0.0 --port 8000