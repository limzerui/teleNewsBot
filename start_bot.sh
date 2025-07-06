#!/bin/bash

# Start script for Financial News Bot

# Check if running in test mode
if [ "$1" == "--test" ]; then
    echo "Starting Financial News Bot in TEST MODE (summaries every 5 minutes)"
    python3 simple_solution.py --test
else
    echo "Starting Financial News Bot in NORMAL MODE (summaries every 5 hours)"
    python3 simple_solution.py
fi 