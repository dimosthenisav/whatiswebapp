#!/usr/bin/env python
"""
Development script to run the WhatIs Slack bot locally.
This script initializes the database, seeds it with example data,
and starts the Flask server.
"""

import os
import webbrowser
import time
import requests
from dotenv import load_dotenv
import database as db

# Load environment variables
load_dotenv()

def check_env_vars():
    """Check if required environment variables are set."""
    required_vars = ['SLACK_BOT_TOKEN', 'SLACK_SIGNING_SECRET']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease create a .env file with these variables or set them in your environment.")
        return False
    return True

def init_database():
    """Initialize the database and seed it with example data."""
    print("🗃️  Initializing database...")
    db.init_db()
    
    # Check if there are any terms in the database
    terms = db.get_all_terms()
    if not terms:
        print("🌱  Seeding database with example terms...")
        try:
            requests.get('http://localhost:5000/seed')
            print("✅  Database seeded successfully!")
        except requests.exceptions.ConnectionError:
            print("⚠️  Could not seed database. Server not running yet.")
            # We'll seed it when the server starts

def start_server():
    """Start the Flask server."""
    print("🚀  Starting server...")
    print("📝  The WhatIs Slack bot is running at http://localhost:5000")
    print("🔧  Admin dashboard available at http://localhost:5000/admin")
    print("\n⚠️  Note: To receive Slack commands, you need to expose your local server to the internet.")
    print("   You can use a tool like ngrok: 'ngrok http 5000'")
    print("\n📋  Press Ctrl+C to stop the server")
    
    # Open the admin dashboard in the default browser
    time.sleep(1)  # Give the server a moment to start
    webbrowser.open('http://localhost:5000/admin')
    
    # Import and run the Flask app
    from app import app
    app.run(debug=True)

if __name__ == '__main__':
    print("🤖  WhatIs Slack Bot - Development Server")
    print("----------------------------------------")
    
    if check_env_vars():
        init_database()
        start_server()
    else:
        print("\n❌  Setup incomplete. Please fix the issues above and try again.") 