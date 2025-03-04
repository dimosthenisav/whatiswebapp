import os
import json
import hmac
import hashlib
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize the Slack client with the bot token
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

def verify_slack_request(request_data, timestamp, signature):
    """
    Verify that the request is coming from Slack.
    
    Args:
        request_data (bytes): The raw request body
        timestamp (str): The X-Slack-Request-Timestamp header
        signature (str): The X-Slack-Signature header
        
    Returns:
        bool: True if the request is valid, False otherwise
    """
    # Check if the timestamp is too old (more than 5 minutes)
    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False
    
    # Get the signing secret from environment variables
    slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    if not slack_signing_secret:
        print("Warning: SLACK_SIGNING_SECRET not set")
        return False
    
    # Create the signature base string
    sig_basestring = f"v0:{timestamp}:{request_data.decode('utf-8')}"
    
    # Create the signature to compare with the one from Slack
    my_signature = 'v0=' + hmac.new(
        slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures using a constant-time comparison to prevent timing attacks
    return hmac.compare_digest(my_signature, signature)

def send_slack_response(response_url, message, response_type="ephemeral"):
    """
    Send a response to Slack using the response_url.
    
    Args:
        response_url (str): The URL to send the response to
        message (str): The message to send
        response_type (str): "ephemeral" (only visible to the user) or "in_channel" (visible to everyone)
    """
    import requests
    
    payload = {
        "text": message,
        "response_type": response_type
    }
    
    response = requests.post(
        response_url,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"Error sending Slack response: {response.status_code} {response.text}")

def format_term_response(term_data, similar_terms=None):
    """
    Format a term definition for display in Slack.
    
    Args:
        term_data (dict): The term data from the database
        similar_terms (list, optional): List of similar terms if the exact term wasn't found
        
    Returns:
        str: Formatted message for Slack
    """
    if term_data:
        # Format the response for a found term
        return f"*{term_data['term']}*: {term_data['definition']}"
    
    if similar_terms and len(similar_terms) > 0:
        # Format the response for similar terms
        message = "Sorry, I don't have a definition for that exact term. Did you mean:\n\n"
        
        # Add up to 3 similar terms
        for i, term in enumerate(similar_terms[:3]):
            message += f"• *{term['term']}*: {term['definition']}\n\n"
            
        return message
    
    # No term found and no similar terms
    return "Sorry, I don't have a definition for that term."

def is_direct_message(channel_id):
    """
    Check if a channel ID represents a direct message.
    
    Args:
        channel_id (str): The Slack channel ID
        
    Returns:
        bool: True if it's a direct message, False otherwise
    """
    # Direct message channel IDs typically start with 'D'
    return channel_id.startswith('D')

def get_channel_type(channel_id):
    """
    Determine the type of channel (public, private, or DM).
    
    Args:
        channel_id (str): The Slack channel ID
        
    Returns:
        str: "public_channel", "private_channel", or "direct_message"
    """
    if channel_id.startswith('C'):
        return "public_channel"
    elif channel_id.startswith('G'):
        return "private_channel"
    elif channel_id.startswith('D'):
        return "direct_message"
    else:
        return "unknown" 