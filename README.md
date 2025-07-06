# Financial News Bot for Raspberry Pi

A self-hosted Telegram bot that monitors financial news channels, summarizes content using AI, and sends periodic summaries to subscribers. This version is optimized for running on a Raspberry Pi.

## Features

- 📰 **Channel Monitoring**: Monitors financial news channels on Telegram (default: "marketfeed")
- 🤖 **AI Summaries**: Generates concise summaries using OpenAI's GPT models
- 📈 **Stock Impact Analysis**: Identifies potentially impacted stocks and market sectors
- 🔍 **Sentiment Analysis**: Determines if the news has bullish, bearish, or neutral sentiment
- ✨ **Markdown Formatting**: Properly formatted messages with bold text and bullet points
- 🧑‍💼 **Subscriber Management**: Users can subscribe/unsubscribe to receive updates
- 🚀 **Auto-start on Boot**: Uses systemd to automatically start when your Raspberry Pi boots
- 💾 **Local SQLite Storage**: Stores subscribers locally in an SQLite database

## System Requirements

- Raspberry Pi (any model) running Raspberry Pi OS
- Python 3.8+
- Internet connection
- Approximately 50MB free space for the application and dependencies

## Prerequisites

- Telegram API credentials (API ID and API Hash) from [my.telegram.org](https://my.telegram.org/apps)
- Telegram Bot Token from [@BotFather](https://t.me/botfather)
- OpenAI API Key from [OpenAI Platform](https://platform.openai.com/account/api-keys)

## Installation

1. Clone the repository:
   ```bash
   cd ~/Documents
   git clone <repository-url>
   cd teleNewsBot
   ```

2. Create a virtual environment and install the required packages:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables:
   ```
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELETHON_SESSION_STRING=your_session_string
   OPENAI_API_KEY=your_openai_key
   TARGET_CHANNEL=channel_name  # default is 'marketfeed'
   SUMMARY_INTERVAL=300
   TESTING_INTERVAL=5
   ```

## Step-by-Step Setup

### 1. Create a Telegram Application

1. Go to [my.telegram.org](https://my.telegram.org/apps) and log in
2. Create a new application to get your API ID and API Hash
3. Add these to your `.env` file as `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`

### 2. Create a Telegram Bot

1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions to create a new bot
3. Copy the provided token to your `.env` file as `TELEGRAM_BOT_TOKEN`

### 3. Generate a Session String

The session string allows the bot to connect to Telegram as a user to monitor channels:

```bash
python3 session_generator.py
```

Follow the prompts to authenticate and generate a session string, then add it to your `.env` file as `TELETHON_SESSION_STRING`.

### 4. Get an OpenAI API Key

1. Create an account or log in at [OpenAI](https://platform.openai.com/)
2. Navigate to the [API Keys section](https://platform.openai.com/account/api-keys)
3. Generate a new key and add it to your `.env` file as `OPENAI_API_KEY`

### 5. Configure Auto-start on Boot

```bash
# Copy systemd service file
sudo cp financial-news-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable financial-news-bot
```

## Usage

### Running the Bot

The bot will start automatically when your Raspberry Pi boots. To manually manage the service:

```bash
# Start the service
sudo systemctl start financial-news-bot

# Check status
sudo systemctl status financial-news-bot --no-pager

# Stop the service
sudo systemctl stop financial-news-bot

# Restart the service
sudo systemctl restart financial-news-bot
```

For testing purposes, you can run the bot directly with shorter intervals (5 minutes):

```bash
cd ~/Documents/teleNewsBot
source venv/bin/activate
python simple_solution.py --test
```

### Managing Subscribers

To check current subscribers:

```bash
cd ~/Documents/teleNewsBot
./check_subscribers.py
```

This will show all active and inactive subscribers in the SQLite database.

### Bot Commands

Once the bot is running, users can interact with it using these commands:

- `/start` - Subscribe to financial news summaries
- `/stop` - Unsubscribe from updates
- `/help` - Show help message and available commands
- `/status` - Show bot status and subscriber count
- `/test` - Generate and send a test summary immediately
- `/subscribe_me` - Alternative command to subscribe

## Maintenance

### Checking Logs

```bash
# View systemd service logs
sudo journalctl -u financial-news-bot -f --no-pager

# View application logs
tail -f ~/Documents/teleNewsBot/logs/bot_$(date +%Y-%m-%d).log
```

### Database Management

The bot uses SQLite to store subscribers. The database file is located at:
```
~/Documents/teleNewsBot/subscribers.db
```

You can view the database schema and contents with SQLite:

```bash
sqlite3 ~/Documents/teleNewsBot/subscribers.db
```

Common SQLite commands:
```sql
-- View all tables
.tables

-- View schema
.schema subscribers

-- List all subscribers
SELECT * FROM subscribers;

-- List only active subscribers
SELECT * FROM subscribers WHERE active = 1;

-- Add a subscriber manually
INSERT INTO subscribers (user_id, username, first_name, subscribed_at, active) 
VALUES (123456789, 'username', 'First Name', datetime('now'), 1);

-- Exit SQLite
.exit
```

## Configuration Options

The bot's behavior can be configured through environment variables in the `.env` file:

- `SUMMARY_INTERVAL`: Minutes between summaries (default: 300)
- `TESTING_INTERVAL`: Minutes between summaries in test mode (default: 5)
- `TARGET_CHANNEL`: The channel to monitor (default: 'marketfeed')

## OLED Bus Display Integration

If you're also running the OLED bus display on your Raspberry Pi, this project includes the necessary service file to manage it alongside the financial news bot.

### Setting Up OLED Display Service

1. Copy the service file to the systemd directory:
```bash
sudo cp ~/Documents/teleNewsBot/oled-bus-display.service /etc/systemd/system/
```

2. Enable and start the service:
```bash
sudo systemctl enable oled-bus-display
sudo systemctl start oled-bus-display
```

### Managing OLED Display Issues

If your OLED display starts behaving erratically or "going crazy," you can stop the service:

```bash
sudo systemctl stop oled-bus-display
```

To check if the service is running:
```bash
sudo systemctl status oled-bus-display
```

If you want to permanently disable the OLED display from starting at boot:
```bash
sudo systemctl disable oled-bus-display
```

## Troubleshooting

### Bot Not Starting

Check the systemd service status:
```bash
sudo systemctl status financial-news-bot --no-pager
```

Verify your environment variables:
```bash
cd ~/Documents/teleNewsBot
cat .env
```

Check for errors in the log files:
```bash
cat ~/Documents/teleNewsBot/logs/systemd-error.log
```

### OLED Display Issues

If the OLED display is showing erratic behavior:
```bash
# Stop the display service
sudo systemctl stop oled-bus-display

# Check if any related processes are still running
ps aux | grep -i oled
```

If you find any lingering processes, you can kill them:
```bash
kill -9 <PID>
```

### Connectivity Issues

Make sure your Raspberry Pi has an active internet connection:
```bash
ping -c 4 google.com
```

### SQLite Database Issues

To check the current subscribers in the database:
```bash
cd ~/Documents/teleNewsBot
python3 check_subscribers.py
```

If you need to back up your subscribers database:
```bash
cp ~/Documents/teleNewsBot/subscribers.db ~/Documents/teleNewsBot/backup/subscribers.db.$(date +%Y%m%d)
```

## License

This project is licensed under the MIT License.
