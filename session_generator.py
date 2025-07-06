"""
Telethon Session String Generator

This script generates a session string that can be used in non-interactive environments
like Railway. Run this script locally once to generate the string, then set it as an
environment variable in your deployment environment.

Usage:
    python session_generator.py
"""

import os
import getpass
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load environment variables if available
load_dotenv()

def main():
    print("=== Telegram Session String Generator ===")
    
    # Get API credentials
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    
    # If not in .env file, prompt for them
    if not api_id:
        api_id = input("Enter your API ID (from https://my.telegram.org/apps): ")
    if not api_hash:
        api_hash = input("Enter your API hash: ")
    if not phone:
        phone = input("Enter your phone number (with country code, e.g. +1234567890): ")

    # Create client and connect
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        print("\nConnecting to Telegram...")
        client.connect()
        
        # Send code request
        if not client.is_user_authorized():
            client.send_code_request(phone)
            code = input("Enter the code you received: ")
            client.sign_in(phone, code)
            
            # In some cases, 2FA might be enabled
            if client.is_user_authorized():
                print("Successfully logged in!")
            else:
                password = getpass.getpass("Enter your 2FA password: ")
                client.sign_in(password=password)
        
        # Get the session string
        session_string = client.session.save()
        print("\n=== YOUR SESSION STRING ===")
        print(f"\n{session_string}\n")
        print("=== END OF SESSION STRING ===")
        print("\nStore this string as TELETHON_SESSION_STRING in your .env file or in your deployment environment.")
        print("This string allows your application to authenticate with Telegram without interactive login.")
        print("\nNEVER share this string with anyone! It provides full access to your Telegram account.")

if __name__ == "__main__":
    main() 