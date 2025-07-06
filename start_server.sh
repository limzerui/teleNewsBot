#!/bin/bash
#
# Financial News Bot Startup Script
# This script is designed to start the Financial News Bot in a production environment
# with proper error handling and environment setup.
#
# Usage:
#   ./start_server.sh [--test] [--debug] [--admin_id TELEGRAM_ID]

# Exit on error
set -e

# Set working directory to script location
cd "$(dirname "$0")"

# Configuration
VENV_DIR="venv"
PYTHON_CMD="python3"
BOT_SCRIPT="simple_solution.py"
LOG_FILE="logs/bot_$(date +%Y-%m-%d).log"

# Ensure logs directory exists
mkdir -p logs

# Parse arguments
ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            ARGS="$ARGS --test"
            echo "Running in test mode (faster updates)"
            shift
            ;;
        --debug)
            ARGS="$ARGS --debug"
            echo "Debug mode enabled"
            shift
            ;;
        --admin_id)
            ARGS="$ARGS --admin_id $2"
            echo "Adding admin subscriber: $2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Check if virtual environment exists
if [ -d "$VENV_DIR" ]; then
    echo "Activating virtual environment: $VENV_DIR"
    source "$VENV_DIR/bin/activate"
else
    echo "Creating virtual environment: $VENV_DIR"
    $PYTHON_CMD -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    
    echo "Installing requirements..."
    pip install -r requirements.txt
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Please create one based on README instructions."
    exit 1
fi

# Display setup information
echo "----------------------------------------"
echo "Starting Financial News Bot..."
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Log file: $LOG_FILE"
echo "----------------------------------------"

# Start the bot
echo "Running: $PYTHON_CMD $BOT_SCRIPT $ARGS"
$PYTHON_CMD $BOT_SCRIPT $ARGS

# This line will only execute if the bot exits normally
echo "Bot has stopped. Check logs for any errors." 