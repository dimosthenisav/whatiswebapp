# Setting Up Your Slack App

This guide will walk you through the process of setting up a Slack app for the WhatIs bot.

## Step 1: Create a New Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Enter "WhatIs" as the app name
5. Select your workspace
6. Click "Create App"

## Step 2: Configure Basic Information

1. In the "Basic Information" section, note your "Signing Secret" - you'll need this for your `.env` file
2. Scroll down to "Display Information" and configure:
   - App name: WhatIs
   - Short description: A glossary bot for looking up term definitions
   - App icon: (optional) Upload an icon for your bot
   - Background color: Choose a color (e.g., #3498db)

## Step 3: Set Up OAuth & Permissions

1. In the sidebar, click "OAuth & Permissions"
2. Under "Scopes", add the following Bot Token Scopes:
   - `commands` (to create slash commands)
   - `chat:write` (to post messages)
   - `users:read` (to get user information)

3. Scroll up to "OAuth Tokens for Your Workspace" and click "Install to Workspace"
4. Authorize the app when prompted
5. Copy the "Bot User OAuth Token" (starts with `xoxb-`) - you'll need this for your `.env` file

## Step 4: Create a Slash Command

1. In the sidebar, click "Slash Commands"
2. Click "Create New Command"
3. Fill in the details:
   - Command: `/whatis`
   - Request URL: `https://your-app-url.com/slack/whatis` (you'll update this after deployment)
   - Short Description: Get the definition of a term
   - Usage Hint: `[term]`
4. Click "Save"

## Step 5: Configure Interactivity (Optional)

If you want to add interactive features like buttons or menus:

1. In the sidebar, click "Interactivity & Shortcuts"
2. Toggle "Interactivity" to On
3. Set the Request URL to `https://your-app-url.com/slack/interactive` (you'll update this after deployment)
4. Click "Save Changes"

## Step 6: Update Your Environment Variables

Create a `.env` file in your project with the following variables:

```
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
```

## Step 7: Deploy Your App

1. Deploy your app to your chosen platform (Vercel, AWS, etc.)
2. Update the Request URLs in your Slack app configuration with your deployed URL

## Step 8: Test Your Bot

1. In Slack, type `/whatis help` to see if your bot responds
2. Try looking up a term with `/whatis API`

## Troubleshooting

- **Bot not responding**: Check your logs for errors and make sure your Request URL is correct
- **Invalid request errors**: Verify your signing secret is correct
- **Permission errors**: Make sure you've added all the required scopes

## Local Development with ngrok

For local development, you can use [ngrok](https://ngrok.com/) to expose your local server:

1. Start your Flask app locally
2. In a new terminal, run `ngrok http 5000`
3. Copy the HTTPS URL provided by ngrok (e.g., `https://abc123.ngrok.io`)
4. Update your Slack app's Request URLs with this URL
5. Test your bot in Slack

Note that ngrok URLs change each time you restart ngrok, so you'll need to update your Slack app configuration accordingly. 