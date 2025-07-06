#!/usr/bin/env python3
"""
Financial News Monitor and Summarizer

This script uses Telethon to:
1. Monitor a financial news channel
2. Summarize the news using OpenAI
3. Send summaries to a list of users

It doesn't use python-telegram-bot to avoid compatibility issues.
"""

import asyncio
import os
import json
import logging
from openai import OpenAI
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import events
from telethon.tl.types import User, InputPeerUser
from subscriber_db_sqlite import SubscriberDB

# Add timezone support
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    SGT = ZoneInfo("Asia/Singapore")
except ImportError:
    import pytz
    SGT = pytz.timezone("Asia/Singapore")

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_STRING = os.getenv('TELETHON_SESSION_STRING')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', 'marketfeed')

# Configure OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

class FinancialNewsMonitor:
    """Monitors financial news and sends summaries to subscribers."""
    
    def __init__(self):
        """Initialize the monitor."""
        if not all([API_ID, API_HASH, SESSION_STRING, BOT_TOKEN]):
            raise ValueError("Missing required credentials for both user and bot clients.")
        
        if not OPENAI_API_KEY:
            raise ValueError("Missing OpenAI API key")
        
        self.user_client = None  # For monitoring the channel
        self.bot_client = None   # For interacting with users
        self.target_channel = TARGET_CHANNEL
        self.last_processed_time = datetime.now(SGT)
        self.subscriber_db = SubscriberDB()
        self.db_ready = False
    
    async def connect(self):
        """Connect both the user and bot clients to Telegram."""
        logger.info("Connecting user client for channel monitoring...")
        self.user_client = TelegramClient(
            StringSession(SESSION_STRING), int(API_ID), API_HASH
        )
        await self.user_client.connect()
        if not await self.user_client.is_user_authorized():
            raise ConnectionError("User client authentication failed. Check session string.")
        logger.info("User client connected successfully.")

        logger.info("Connecting bot client for user interaction...")
        # Using a file session for the bot to persist its state
        self.bot_client = TelegramClient(
            'bot_session.session', int(API_ID), API_HASH
        )
        await self.bot_client.start(bot_token=BOT_TOKEN)
        logger.info("Bot client connected successfully.")

        if not self.db_ready:
            logger.info("Connecting to SQLite for subscriber management...")
            await self.subscriber_db.connect()
            self.db_ready = True
            logger.info("SQLite subscriber DB ready.")
    
    async def fetch_recent_messages(self, hours=4):
        """Fetch recent messages from the target channel using the user client."""
        if not self.user_client:
            await self.connect()
        
        # Check if user client is connected, reconnect if needed
        if not self.user_client.is_connected():
            logger.warning("User client disconnected, attempting to reconnect...")
            try:
                await self.user_client.connect()
                if not await self.user_client.is_user_authorized():
                    logger.error("User client authentication failed after reconnection")
                    return []
                logger.info("User client reconnected successfully")
            except Exception as e:
                logger.error(f"Failed to reconnect user client: {e}")
                return []
        
        try:
            # Try to get the channel
            try:
                entity = await self.user_client.get_entity(self.target_channel)
            except ValueError:
                try:
                    # Try with @ prefix
                    entity = await self.user_client.get_entity(f"@{self.target_channel}")
                except ValueError:
                    logger.error(f"Channel '{self.target_channel}' not found")
                    return []
            
            # Calculate time limit
            time_limit = datetime.now(SGT) - timedelta(hours=hours)
            logger.info(f"Fetching messages from {self.target_channel} since {time_limit.strftime('%Y-%m-%d %H:%M:%S')} (last {hours} hours)")
            
            # Fetch messages - increased limit for better analysis with longer intervals
            messages = []
            message_limit = 500 if hours >= 3 else 50  # More messages for longer intervals
            
            async for message in self.user_client.iter_messages(
                entity=entity,
                limit=message_limit,  # Increased from 50 to 500 for 3+ hour intervals
                offset_date=time_limit
            ):
                if not message.text:
                    continue
                messages.append({
                    "id": message.id,
                    "date": message.date,
                    "text": message.text
                })
            
            logger.info(f"Fetched {len(messages)} messages from {self.target_channel} (limit: {message_limit}, time window: {hours} hours)")
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching messages with user client: {e}")
            # If we get a connection error, try to reconnect for next time
            if "disconnected" in str(e).lower() or "connection" in str(e).lower():
                logger.warning("Connection error detected, will try to reconnect on next attempt")
                try:
                    await self.user_client.disconnect()
                except:
                    pass
            return []
    
    def summarize(self, messages):
        """Summarize messages using OpenAI."""
        if not messages:
            logger.warning("No messages to summarize")
            return None
        
        # Compile message texts
        message_texts = [msg["text"] for msg in messages]
        combined_text = "\n\n---\n\n".join(message_texts)
        
        # Truncate combined text if it's too long
        if len(combined_text) > 15000:
            combined_text = combined_text[:15000] + "...(truncated)"
            logger.warning("Message text truncated to fit OpenAI token limits")
        
        prompt = """
You are an expert financial analyst specializing in market impact analysis. Your task is to analyze financial news updates and provide detailed insights on potentially impacted stocks and market sectors.

For each news item, you should:
1. Identify specific stock tickers that will be directly impacted
2. Explain WHY each stock will be impacted (positive or negative)
3. Assess the confidence level of your prediction
4. Identify broader market sectors that may be affected
5. Provide actionable insights for investors

When analyzing stocks, consider:
- Direct mentions of companies in the news
- Companies in related industries or supply chains
- Competitors that might benefit or suffer
- Regulatory impacts on specific sectors
- Market sentiment shifts that could affect similar companies

Format your response as a valid JSON object with the following structure exactly:
{
    "summary": "Comprehensive 3-4 sentence summary of key market developments and their implications",
    "potentially_impacted_stocks": [
        {
            "ticker": "TICKER1",
            "company_name": "Full Company Name",
            "impact_type": "positive/negative/neutral",
            "impact_reason": "Detailed explanation of why this stock will be impacted",
            "confidence_level": "high/medium/low",
            "expected_magnitude": "significant/moderate/minimal"
        }
    ],
    "market_sectors": [
        {
            "sector_name": "Sector Name",
            "impact_type": "positive/negative/neutral",
            "impact_reason": "Explanation of sector-wide impact",
            "key_companies": ["TICKER1", "TICKER2"]
        }
    ],
    "sentiment": "bullish/bearish/neutral",
    "key_points": [
        "Point 1 with specific details",
        "Point 2 with specific details", 
        "Point 3 with specific details"
    ],
    "market_implications": "2-3 sentences on broader market implications and potential trading opportunities"
}

Make sure your response can be parsed as valid JSON. Be specific and detailed in your analysis.
"""
        
        try:
            # Using new OpenAI API format
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Changed to gpt-4o-mini
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"News updates to analyze:\n{combined_text}"}
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            result = response.choices[0].message.content
            
            try:
                # Log the raw response for debugging
                logger.debug(f"Raw OpenAI response: {result}")
                parsed = json.loads(result)
                logger.info("Successfully parsed OpenAI response as JSON")
                return parsed
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from OpenAI response: {e}")
                # Fallback structured data
                return {
                    "summary": "Summary could not be generated in the correct format. Here's the raw output: " + result[:500] + "...",
                    "potentially_impacted_stocks": [],
                    "market_sectors": [],
                    "sentiment": "neutral",
                    "key_points": ["Error: Unable to parse structured data"],
                    "market_implications": ""
                }
        except Exception as e:
            logger.error(f"Error during summarization: {str(e)}")
            return {
                "summary": "Error generating summary",
                "potentially_impacted_stocks": [],
                "market_sectors": [],
                "sentiment": "neutral",
                "key_points": ["Failed to analyze news due to an error"],
                "market_implications": ""
            }
    
    async def send_summary_to_subscribers(self, summary):
        """Send a summary to all subscribers."""
        if not summary:
            logger.warning("No summary to send")
            return
        
        subscribers = await self.subscriber_db.get_active_subscribers()
        
        if not subscribers:
            logger.info("No subscribers to send summary to")
            return
        
        # Format the message
        message = f"""
📊 **Financial News Summary**

{summary['summary']}

**Key Points:**
"""
        for point in summary['key_points'][:3]:
            message += f"- {point}\n"
        
        message += f"\n**Market Sentiment:** {summary['sentiment']}\n"
        
        if summary['potentially_impacted_stocks']:
            message += "\n**📈 Potentially Impacted Stocks:**\n"
            for stock in summary['potentially_impacted_stocks']:
                impact_emoji = "🟢" if stock['impact_type'] == 'positive' else "🔴" if stock['impact_type'] == 'negative' else "🟡"
                confidence_emoji = "🟢" if stock['confidence_level'] == 'high' else "🟡" if stock['confidence_level'] == 'medium' else "🔴"
                message += f"{impact_emoji} **{stock['ticker']}** ({stock['company_name']})\n"
                message += f"   • Impact: {stock['impact_type'].title()} ({stock['expected_magnitude']})\n"
                message += f"   • Reason: {stock['impact_reason']}\n"
                message += f"   • Confidence: {confidence_emoji} {stock['confidence_level'].title()}\n\n"
            
        if summary['market_sectors']:
            message += "\n**🏭 Affected Sectors:**\n"
            for sector in summary['market_sectors']:
                impact_emoji = "🟢" if sector['impact_type'] == 'positive' else "🔴" if sector['impact_type'] == 'negative' else "🟡"
                message += f"{impact_emoji} **{sector['sector_name']}** ({sector['impact_type'].title()})\n"
                message += f"   • Impact: {sector['impact_reason']}\n"
                if sector['key_companies']:
                    message += f"   • Key Companies: {', '.join(sector['key_companies'])}\n"
                message += "\n"
        
        if summary.get('market_implications'):
            message += f"\n**💡 Market Implications:**\n{summary['market_implications']}\n"
        
        message += f"\nGenerated at {datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Send to all subscribers
        logger.info(f"Sending summary to {len(subscribers)} subscribers: {subscribers}")
        for user_id in subscribers:
            try:
                # Use bot_client to send messages (not user_client!)
                logger.info(f"Sending formatted message as bot to user {user_id}")
                result = await self.bot_client.send_message(int(user_id), message, parse_mode='md')
                logger.info(f"Sent summary to user {user_id}, message ID: {getattr(result, 'id', 'unknown')}")
                
                # Sleep to avoid hitting rate limits
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                # Remove this user from active subscribers to prevent future errors
                try:
                    await self.subscriber_db.remove_subscriber(user_id)
                    logger.info(f"Removed unreachable user {user_id} from active subscribers")
                except Exception as db_error:
                    logger.error(f"Failed to remove user {user_id} from database: {str(db_error)}")
                continue
    
    async def monitor_and_summarize(self, interval_minutes=180, test_mode=False):
        """Continuously monitor the channel and send summaries."""
        logger.info(f"Starting to monitor channel: {self.target_channel}")
        logger.info(f"Summary interval: {interval_minutes} minutes")
        
        if test_mode:
            logger.info("Running in TEST MODE with shorter intervals")
        
        last_message_id = None
        
        while True:
            try:
                # Fetch only messages from the last interval_minutes window
                messages = await self.fetch_recent_messages(hours=interval_minutes / 60)
                
                if messages and (last_message_id is None or messages[0]["id"] != last_message_id):
                    if messages:
                        last_message_id = messages[0]["id"]
                    summary = self.summarize(messages)
                    if summary:
                        await self.send_summary_to_subscribers(summary)
                        self.last_processed_time = datetime.now(SGT)
                        logger.info("Successfully sent summary to subscribers")
                else:
                    logger.info("No new messages to summarize or same as last batch")
                    
                logger.info(f"Sleeping for {interval_minutes} minutes until next check")
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                # Check if it's a connection issue
                if "disconnected" in str(e).lower() or "connection" in str(e).lower():
                    logger.warning("Connection issue detected, will attempt reconnection on next cycle")
                    # Try to reconnect the user client
                    try:
                        if self.user_client:
                            await self.user_client.disconnect()
                        await asyncio.sleep(5)  # Wait before reconnecting
                        await self.connect()
                        logger.info("Successfully reconnected after connection error")
                    except Exception as reconnect_error:
                        logger.error(f"Failed to reconnect: {str(reconnect_error)}")
                
                # Sleep shorter time on errors to retry sooner
                logger.info("Sleeping 60 seconds before retry due to error")
                await asyncio.sleep(60)
    
    async def setup_handlers(self):
        """Set up event handlers on the bot client."""
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_command(event):
            """Handle /start command."""
            sender = await event.get_sender()
            user_id = int(sender.id)
            username = sender.username
            first_name = sender.first_name
            
            logger.info(f"Start command received from user ID: {user_id}, username: {username}")
            
            # Add as subscriber
            await self.subscriber_db.add_subscriber(user_id, username, first_name)
            
            # Send welcome message
            welcome_message = f"""
👋 Welcome {first_name}! You're now subscribed to financial news summaries.

The bot will send you regular summaries of financial news with:
- Comprehensive market analysis and key developments
- Detailed stock impact analysis with reasoning
- Market sentiment and sector analysis
- Confidence levels and expected impact magnitude
- Actionable market implications

Available commands:
/test - Generate a test summary now
/status - Check bot status
/help - Show all commands
/stop - Unsubscribe
/force_update - Force an immediate update to all subscribers

You will receive summaries automatically every 3 hours with detailed analysis of potentially impacted stocks and market sectors.
"""
            
            # Send welcome message
            logger.info(f"Sending welcome message to user {user_id}")
            await event.respond(welcome_message, parse_mode='md')
            
            # Send a test message to verify communication
            logger.info(f"Sending test message to verify communication with {user_id}")
            test_message = "This is a test message to verify I can send you direct messages. If you see this, communication is working correctly!"
            await self.bot_client.send_message(sender, test_message, parse_mode='md')
        
        @self.bot_client.on(events.NewMessage(pattern='/stop'))
        async def stop_command(event):
            """Handle /stop command."""
            sender = await event.get_sender()
            user_id = int(sender.id)
            await self.subscriber_db.remove_subscriber(user_id)
            await event.respond("You've been unsubscribed from financial news summaries. Use /start to subscribe again.", parse_mode='md')
        
        @self.bot_client.on(events.NewMessage(pattern='/help'))
        async def help_command(event):
            """Handle /help command."""
            help_text = """
📈 **Financial News Bot - Commands**:

/start - Subscribe to financial news summaries
/stop - Unsubscribe from updates
/help - Show this help message
/status - Show bot status and subscriber count
/test - Send a test summary (for testing purposes)
/subscribe_me - Special command to subscribe yourself
/force_update - Force an immediate update to all subscribers

This bot monitors financial news channels and provides detailed summaries every 3 hours, including:
• Comprehensive market analysis
• Detailed stock impact analysis with reasoning
• Confidence levels and expected impact magnitude
• Sector-wide implications
• Actionable market insights
"""
            await event.respond(help_text, parse_mode='md')
        
        @self.bot_client.on(events.NewMessage(pattern='/status'))
        async def status_command(event):
            """Handle /status command."""
            count = await self.subscriber_db.get_subscriber_count()
            status_text = f"""
🤖 **Bot Status**:
- Active: ✅
- Subscribers: {count}
- Last check: {self.last_processed_time.strftime('%Y-%m-%d %H:%M:%S')}
- Target channel: {self.target_channel}
"""
            await event.respond(status_text, parse_mode='md')
        
        @self.bot_client.on(events.NewMessage(pattern='/force_update'))
        async def force_update_command(event):
            """Force an immediate update to all subscribers."""
            sender = await event.get_sender()
            await event.respond("Forcing an immediate update to all subscribers...", parse_mode='md')
            messages = await self.fetch_recent_messages(hours=2)
            if messages:
                summary = self.summarize(messages)
                if summary:
                    await self.send_summary_to_subscribers(summary)
                    await event.respond("✅ Force update sent successfully to subscribers!", parse_mode='md')
                else:
                    await event.respond("Error generating summary.", parse_mode='md')
            else:
                await event.respond("No messages found to summarize.", parse_mode='md')
        
        @self.bot_client.on(events.NewMessage(pattern='/test'))
        async def test_command(event):
            """Handle /test command - admin only for testing."""
            sender = await event.get_sender()
            user_id = int(sender.id)
            username = sender.username
            first_name = sender.first_name
            
            logger.info(f"Test command received from user ID: {user_id}, username: {username}")
            
            # Add yourself as a subscriber to test
            await self.subscriber_db.add_subscriber(user_id, username, first_name)
            
            await event.respond("Fetching latest news and generating a test summary...", parse_mode='md')
            
            # Fetch and summarize
            messages = await self.fetch_recent_messages(hours=2)
            if messages:
                summary = self.summarize(messages)
                if summary:
                    # Format the message directly here instead of using send_summary_to_subscribers
                    message = f"""
📊 **Financial News Summary**

{summary['summary']}

**Key Points:**
"""
                    for point in summary['key_points'][:3]:
                        message += f"- {point}\n"
                    
                    message += f"\n**Market Sentiment:** {summary['sentiment']}\n"
                    
                    if summary['potentially_impacted_stocks']:
                        message += "\n**📈 Potentially Impacted Stocks:**\n"
                        for stock in summary['potentially_impacted_stocks']:
                            impact_emoji = "🟢" if stock['impact_type'] == 'positive' else "🔴" if stock['impact_type'] == 'negative' else "🟡"
                            confidence_emoji = "🟢" if stock['confidence_level'] == 'high' else "🟡" if stock['confidence_level'] == 'medium' else "🔴"
                            message += f"{impact_emoji} **{stock['ticker']}** ({stock['company_name']})\n"
                            message += f"   • Impact: {stock['impact_type'].title()} ({stock['expected_magnitude']})\n"
                            message += f"   • Reason: {stock['impact_reason']}\n"
                            message += f"   • Confidence: {confidence_emoji} {stock['confidence_level'].title()}\n\n"
                    
                    if summary['market_sectors']:
                        message += "\n**🏭 Affected Sectors:**\n"
                        for sector in summary['market_sectors']:
                            impact_emoji = "🟢" if sector['impact_type'] == 'positive' else "🔴" if sector['impact_type'] == 'negative' else "🟡"
                            message += f"{impact_emoji} **{sector['sector_name']}** ({sector['impact_type'].title()})\n"
                            message += f"   • Impact: {sector['impact_reason']}\n"
                            if sector['key_companies']:
                                message += f"   • Key Companies: {', '.join(sector['key_companies'])}\n"
                            message += "\n"
                    
                    if summary.get('market_implications'):
                        message += f"\n**💡 Market Implications:**\n{summary['market_implications']}\n"
                    
                    message += f"\nGenerated at {datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # Send the actual summary in the chat
                    logger.info(f"Sending test summary response directly to the chat")
                    await event.respond(message, parse_mode='md')
                    
                    # Now also demonstrate the new fallback method
                    logger.info(f"Testing the new summary delivery fallback method")
                    await event.respond("Now testing automatic delivery method, check for another message...", parse_mode='md')
                    await self.send_summary_to_subscribers(summary)
                    
                    await event.respond("✅ Automatic delivery test successful! You should have received another copy.", parse_mode='md')
                else:
                    await event.respond("Error generating summary.", parse_mode='md')
            else:
                await event.respond("No messages found to summarize.", parse_mode='md')
        
        @self.bot_client.on(events.NewMessage(pattern='/subscribe_me'))
        async def subscribe_me_command(event):
            """Special command to subscribe the sender."""
            sender = await event.get_sender()
            user_id = int(sender.id)
            username = sender.username
            first_name = sender.first_name
            await self.subscriber_db.add_subscriber(user_id, username, first_name)
            
            await event.respond(f"👋 Welcome {first_name}! You're now subscribed to financial news summaries.", parse_mode='md')
    
    async def run(self, interval_minutes=180, test_mode=False):
        """Run the monitor, with the bot client taking the lead."""
        if not self.user_client or not self.bot_client:
            await self.connect()
        
        await self.setup_handlers()
        
        logger.info("Bot is running! Listening for commands. Press Ctrl+C to stop.")
        logger.info("Starting periodic monitoring with %d minute intervals", interval_minutes)
        
        # Run both bot handlers and periodic monitoring concurrently
        await asyncio.gather(
            self.bot_client.run_until_disconnected(),
            self.monitor_and_summarize(interval_minutes=interval_minutes, test_mode=test_mode)
        )
    
    async def disconnect(self):
        """Disconnect both clients."""
        if self.user_client and self.user_client.is_connected():
            await self.user_client.disconnect()
            logger.info("User client disconnected.")
        if self.bot_client and self.bot_client.is_connected():
            await self.bot_client.disconnect()
            logger.info("Bot client disconnected.")

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Financial News Monitor')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--test', action='store_true', help='Run in test mode with 5-minute intervals')
    parser.add_argument('--admin_id', type=str, help='Admin Telegram user ID to receive summaries (optional)')
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    interval = 5 if args.test else 180  # 5 minutes for testing, 180 for production
    
    monitor = FinancialNewsMonitor()
    
    if args.admin_id:
        try:
            admin_id = str(args.admin_id)
            logger.info(f"Adding admin (ID: {admin_id}) as a subscriber")
            await monitor.subscriber_db.add_subscriber(admin_id, "admin", "Admin")
            logger.info(f"Admin added as subscriber successfully")
        except Exception as e:
            logger.error(f"Failed to add admin as subscriber: {str(e)}")
    
    try:
        await monitor.run(interval_minutes=interval, test_mode=args.test)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        await monitor.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 