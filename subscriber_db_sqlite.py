import aiosqlite
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SubscriberDB:
    def __init__(self, db_path="subscribers.db"):
        self.db_path = db_path

    async def connect(self):
        """Connect to SQLite database with error handling."""
        try:
            logger.info(f"Connecting to SQLite database: {self.db_path}")
            # Test connection and create table
            await self.create_table()
            logger.info("SQLite database connected and initialized successfully")
        except Exception as e:
            logger.error("Failed to connect to SQLite: %s", str(e))
            raise

    async def create_table(self):
        """Create the subscribers table if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    subscribed_at TIMESTAMP,
                    active INTEGER DEFAULT 1
                )
            """)
            await db.commit()

    async def add_subscriber(self, user_id, username, first_name):
        """Add a subscriber to the database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO subscribers 
                    (user_id, username, first_name, subscribed_at, active)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, username, first_name, datetime.now(), 1))
                await db.commit()
            logger.info(f"Added subscriber: {user_id} ({username})")
            return True
        except Exception as e:
            logger.error(f"Error adding subscriber {user_id}: {str(e)}")
            return False

    async def remove_subscriber(self, user_id):
        """Remove a subscriber from the database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE subscribers SET active = 0 WHERE user_id = ?
                """, (user_id,))
                await db.commit()
            logger.info(f"Removed subscriber: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing subscriber {user_id}: {str(e)}")
            return False

    async def get_active_subscribers(self):
        """Get all active subscribers."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT user_id FROM subscribers WHERE active = 1
                """) as cursor:
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error getting subscribers: {str(e)}")
            return []

    async def get_subscriber_count(self):
        """Get the number of active subscribers."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT COUNT(*) FROM subscribers WHERE active = 1
                """) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error getting subscriber count: {str(e)}")
            return 0

    async def close(self):
        """Close database connection (SQLite doesn't need explicit closing)."""
        logger.info("SQLite database connection closed")
