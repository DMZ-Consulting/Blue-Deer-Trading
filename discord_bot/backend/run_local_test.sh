#!/bin/bash

export LOCAL_TEST=true
export DISCORD_TOKEN=MTA3OTg5NzQzNjYzMTM1MTMyNg.GlUV3x.TqAgx4zkYzFAlCph0CVOuqPbjQjqe2s0SAJUZk
export TEST_TOKEN=MTA3OTg5NzQzNjYzMTM1MTMyNg.GlUV3x.TqAgx4zkYzFAlCph0CVOuqPbjQjqe2s0SAJUZk

# Change to the directory containing the app
cd "$(dirname "$0")"

# Run the Discord bot
python3 run_bot.py