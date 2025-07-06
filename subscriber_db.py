import asyncpg
import os
import logging
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
logger = logging.getLogger(__name__)

class SubscriberDB:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Connect to PostgreSQL database with error handling."""
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        try:
            logger.info("Attempting to connect to PostgreSQL database...")
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("PostgreSQL connection pool created successfully")
            await self.create_table()
            logger.info("Database schema verified/created")
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL: %s", str(e))
            raise

    async def create_table(self):
        """Create the subscribers table if it doesn't exist."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    subscribed_at TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE
                )
            """)

    async def add_subscriber(self, user_id, username, first_name):
        """Add a subscriber to the database."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO subscribers (user_id, username, first_name, subscribed_at, active)
                    VALUES ($1, $2, $3, $4, TRUE)
                    ON CONFLICT (user_id) DO UPDATE SET active=TRUE, username=$2, first_name=$3
                """, int(user_id), username, first_name, datetime.utcnow())
                logger.debug("Added/updated subscriber: %s", user_id)
        except Exception as e:
            logger.error("Error adding subscriber %s: %s", user_id, str(e))
            raise

    async def remove_subscriber(self, user_id):
        """Remove a subscriber from active status."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE subscribers SET active=FALSE WHERE user_id=$1
                """, int(user_id))
                logger.debug("Deactivated subscriber: %s", user_id)
        except Exception as e:
            logger.error("Error removing subscriber %s: %s", user_id, str(e))
            raise

    async def get_active_subscribers(self):
        """Get list of active subscriber IDs."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT user_id FROM subscribers WHERE active=TRUE
                """)
                return [row['user_id'] for row in rows]
        except Exception as e:
            logger.error("Error fetching active subscribers: %s", str(e))
            return []

    async def get_subscriber_count(self):
        """Get count of active subscribers."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) AS count FROM subscribers WHERE active=TRUE")
                return row['count'] if row else 0
        except Exception as e:
            logger.error("Error getting subscriber count: %s", str(e))
            return 0

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")