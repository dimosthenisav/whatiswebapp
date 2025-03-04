# WhatIs Slack Bot

A Slack bot that allows users to query a predefined glossary of terms via the command `/whatis [term]`.

## Features

- Query terms using `/whatis [term]` in Slack
- Get definitions from a database
- Fuzzy matching for similar terms
- Works in both public channels and private DMs
- Tracks usage analytics (who requested what term and when)

## Setup Instructions

### Prerequisites

- Python 3.7+
- A Slack workspace with admin permissions
- SQLite (included with Python)

### Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd whatis-slack-bot
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your Slack credentials:
   ```
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_SIGNING_SECRET=your-signing-secret
   ```

### Creating a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click "Create New App"
2. Choose "From scratch" and give your app a name ("WhatIs") and select your workspace
3. Under "Basic Information", note your "Signing Secret" for the `.env` file
4. Go to "OAuth & Permissions" and add the following scopes:
   - `commands` (to create slash commands)
   - `chat:write` (to post messages)
   - `users:read` (to get user information)
5. Install the app to your workspace and copy the "Bot User OAuth Token" for the `.env` file
6. Go to "Slash Commands" and create a new command:
   - Command: `/whatis`
   - Request URL: `https://your-app-url.com/slack/whatis` (you'll update this after deployment)
   - Short Description: "Get the definition of a term"
   - Usage Hint: "[term]"

### Running Locally

1. Start the Flask server:
   ```
   python app.py
   ```

2. Use a tool like ngrok to expose your local server:
   ```
   ngrok http 5000
   ```

3. Update your Slack app's Request URL with the ngrok URL

### Deployment

The app can be deployed to various platforms:
- Vercel
- AWS Lambda
- Heroku
- Any platform that supports Python web applications

## Database Structure

The app uses SQLite with the following tables:
- `terms`: Stores term definitions
- `logs`: Tracks usage analytics

## License

MIT 