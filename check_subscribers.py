#!/usr/bin/env python3
"""
Check subscribers from SQLite database
"""

import os
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subscribers.db")

def check_subscribers():
    """Check subscribers from SQLite database."""
    
    print("="*60)
    print("SUBSCRIBER STATUS CHECK")
    print("="*60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if subscribers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subscribers'")
        if not cursor.fetchone():
            print("❌ No subscribers table found in the database")
            return
            
        # Get all subscribers
        cursor.execute("SELECT user_id, username, first_name, subscribed_at, active FROM subscribers")
        subscribers = cursor.fetchall()
        
        if not subscribers:
            print("❌ No subscribers found in the database")
            return
            
        active_subscribers = [s for s in subscribers if s[4]]  # active is the 5th column
        print(f"✅ SQLite Database: {len(active_subscribers)} active subscribers out of {len(subscribers)} total")
        
        print("\n{:<15} {:<20} {:<20} {:<25} {:<10}".format(
            "USER ID", "USERNAME", "FIRST NAME", "SUBSCRIPTION DATE", "STATUS"
        ))
        print("-" * 80)
        
        for user_id, username, first_name, subscribed_at, active in subscribers:
            status = "✅ Active" if active else "❌ Inactive"
            print("{:<15} {:<20} {:<20} {:<25} {:<10}".format(
                user_id, 
                username or "N/A", 
                first_name or "N/A", 
                subscribed_at or "N/A", 
                status
            ))
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    
    print("="*60)

if __name__ == "__main__":
    check_subscribers() 