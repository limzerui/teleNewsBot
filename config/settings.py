import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Telethon configuration
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE = os.getenv('TELEGRAM_PHONE')
SESSION_STRING = os.getenv('TELETHON_SESSION_STRING')

# Channel to monitor
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', 'marketfeed')

# AI API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# MongoDB
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/telegrambot')

# Summarization interval in minutes
SUMMARY_INTERVAL = int(os.getenv('SUMMARY_INTERVAL', 300))

# Testing interval in minutes (for development)
TESTING_INTERVAL = int(os.getenv('TESTING_INTERVAL', 5))

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent 