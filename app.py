import os
import sys
from flask import Flask, request, jsonify, render_template, redirect, url_for
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import database as db
import slack_utils
import traceback
from werkzeug.urls import quote as url_quote
import json
import logging
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Initialize database
try:
    db.init_db()
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    logger.error(traceback.format_exc())

# Initialize Slack client
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# Print debug information
logger.debug(f"Python version: {sys.version}")
logger.debug(f"Current working directory: {os.getcwd()}")
logger.debug(f"Directory contents: {os.listdir('.')}")
logger.debug(f"Environment variables: REDIS_TLS_URL={'REDIS_TLS_URL' in os.environ}")

@app.errorhandler(500)
def handle_500(error):
    """Handle internal server errors with detailed logging."""
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "env_vars_present": {
            "REDIS_TLS_URL": "REDIS_TLS_URL" in os.environ,
            "REDIS_URL": "REDIS_URL" in os.environ,
            "FLASK_DEBUG": "FLASK_DEBUG" in os.environ
        }
    }
    
    logger.error("500 error occurred!")
    logger.error(f"Error type: {error_info['error_type']}")
    logger.error(f"Error message: {error_info['error_message']}")
    logger.error(f"Traceback:\n{error_info['traceback']}")
    
    return jsonify(error_info), 500

@app.route('/')
def index():
    """Health check endpoint with Redis connection test."""
    try:
        if db.redis_client is None:
            raise Exception("Redis client is not initialized")
            
        # Test Redis connection
        db.redis_client.ping()
        return jsonify({
            "status": "healthy",
            "redis_connection": "connected",
            "python_version": sys.version,
            "current_directory": os.getcwd()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "python_version": sys.version,
            "current_directory": os.getcwd()
        }), 500

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard with enhanced error handling."""
    try:
        if db.redis_client is None:
            raise Exception("Redis client is not initialized")
            
        logger.debug("Attempting to get all terms")
        terms = db.get_all_terms()
        logger.debug(f"Successfully retrieved {len(terms)} terms")
        return render_template('admin.html', terms=terms)
    except Exception as e:
        logger.error("Error in admin_dashboard!")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "redis_client_status": "not initialized" if db.redis_client is None else "initialized"
        }), 500

@app.route('/slack/command', methods=['POST'])
def handle_command():
    # Verify request is from Slack
    if not request.form:
        return jsonify({'error': 'Invalid request'}), 400
    
    # Get command text
    text = request.form.get('text', '').strip()
    user_id = request.form.get('user_id', '')
    
    if not text:
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'Please provide a term to look up. Usage: /whatis <term>'
        })
    
    # Look up the term
    term_info = db.get_term(text)
    
    if term_info:
        # Log successful query
        db.log_query(user_id, text, True)
        
        response = {
            'response_type': 'in_channel',
            'blocks': [
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f'*{term_info["term"]}*\n{term_info["definition"]}'
                    }
                }
            ]
        }
    else:
        # Log failed query
        db.log_query(user_id, text, False)
        
        # Find similar terms
        similar_terms = db.find_similar_terms(text)
        
        if similar_terms:
            suggestions = '\n'.join([f'• {term["term"]}' for term in similar_terms[:3]])
            response = {
                'response_type': 'ephemeral',
                'blocks': [
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': f'Term not found. Did you mean:\n{suggestions}'
                        }
                    }
                ]
            }
        else:
            response = {
                'response_type': 'ephemeral',
                'text': 'Term not found. Please check your spelling or add it to the glossary.'
            }
    
    return jsonify(response)

@app.route('/admin/add', methods=['POST'])
def add_term():
    term = request.form.get('term')
    definition = request.form.get('definition')
    
    if not term or not definition:
        return jsonify({'error': 'Both term and definition are required'}), 400
    
    success = db.add_term(term, definition)
    
    if success:
        return redirect(url_for('admin_dashboard'))
    else:
        return jsonify({'error': 'Term already exists'}), 400

@app.route('/admin/update', methods=['POST'])
def update_term():
    term = request.form.get('term')
    definition = request.form.get('definition')
    
    if not term or not definition:
        return jsonify({'error': 'Both term and definition are required'}), 400
    
    success = db.update_term(term, definition)
    
    if success:
        return redirect(url_for('admin_dashboard'))
    else:
        return jsonify({'error': 'Term not found'}), 404

@app.route('/admin/delete', methods=['POST'])
def delete_term():
    term = request.form.get('term')
    
    if not term:
        return jsonify({'error': 'Term is required'}), 400
    
    success = db.delete_term(term)
    
    if success:
        return redirect(url_for('admin_dashboard'))
    else:
        return jsonify({'error': 'Term not found'}), 404

@app.route('/admin/analytics', methods=['GET'])
def get_analytics():
    """
    Admin endpoint to get usage analytics.
    In a production environment, you would want to add authentication.
    """
    # For demonstration purposes only - in a real app, add proper authentication
    
    # Connect to the database
    import sqlite3
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get the top 10 most queried terms
    cursor.execute("""
    SELECT term, COUNT(*) as count
    FROM logs
    GROUP BY term
    ORDER BY count DESC
    LIMIT 10
    """)
    top_terms = [dict(row) for row in cursor.fetchall()]
    
    # Get the number of queries per day for the last 7 days
    cursor.execute("""
    SELECT date(timestamp) as date, COUNT(*) as count
    FROM logs
    WHERE timestamp >= date('now', '-7 days')
    GROUP BY date
    ORDER BY date
    """)
    daily_queries = [dict(row) for row in cursor.fetchall()]
    
    # Get the total number of queries
    cursor.execute("SELECT COUNT(*) as total FROM logs")
    total_queries = cursor.fetchone()['total']
    
    # Get the number of unique users
    cursor.execute("SELECT COUNT(DISTINCT user_id) as unique_users FROM logs")
    unique_users = cursor.fetchone()['unique_users']
    
    # Get the success rate (percentage of queries that found a term)
    cursor.execute("""
    SELECT 
        SUM(CASE WHEN found = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
    FROM logs
    """)
    success_rate = cursor.fetchone()['success_rate']
    
    conn.close()
    
    return jsonify({
        "top_terms": top_terms,
        "daily_queries": daily_queries,
        "total_queries": total_queries,
        "unique_users": unique_users,
        "success_rate": success_rate
    })

@app.route('/seed', methods=['GET'])
def seed_database():
    """
    Seed the database with some example terms.
    This is for demonstration purposes only.
    """
    # Add some example terms
    example_terms = [
        # Technical Terms
        ("API", "Application Programming Interface - a set of rules that allows different software applications to communicate with each other."),
        ("HTML", "HyperText Markup Language - the standard markup language for documents designed to be displayed in a web browser."),
        ("CSS", "Cascading Style Sheets - a style sheet language used for describing the presentation of a document written in HTML."),
        ("JavaScript", "A programming language that enables interactive web pages and is an essential part of web applications."),
        ("Python", "A high-level, interpreted programming language known for its readability and versatility."),
        ("SQL", "Structured Query Language - a domain-specific language used for managing and manipulating relational databases."),
        ("REST", "Representational State Transfer - an architectural style for designing networked applications."),
        ("JSON", "JavaScript Object Notation - a lightweight data-interchange format that is easy for humans to read and write."),
        ("Git", "A distributed version control system for tracking changes in source code during software development."),
        ("Docker", "A platform that uses OS-level virtualization to deliver software in packages called containers."),
        # Business Communication Terms
        ("FYI", "For Your Information - A commonly used abbreviation in business communication to indicate that information is being passed along for awareness, without requiring any specific action."),
        ("ASAP", "As Soon As Possible - Used to indicate urgency in completing a task or providing information."),
        ("EOD", "End of Day - Refers to the end of the business day, commonly used as a deadline indicator."),
        ("COB", "Close of Business - Similar to EOD, indicates the end of the working day."),
        ("TL;DR", "Too Long; Didn't Read - Used to provide a brief summary of a longer text."),
        ("ETA", "Estimated Time of Arrival - Used to indicate when something is expected to be completed or delivered."),
        ("OOO", "Out of Office - Indicates that someone is not available at work, usually used in email automatic replies."),
        ("WFH", "Work From Home - Indicates that an employee is working remotely from their home."),
        ("EOW", "End of Week - Refers to the end of the work week, commonly used as a deadline indicator."),
        ("IMO", "In My Opinion - Used to express a personal view or judgment on a matter.")
    ]
    
    # Add each term to the database
    for term, definition in example_terms:
        db.add_term(term, definition)
    
    return jsonify({"message": "Database seeded with example terms"})

@app.route('/debug')
def debug():
    """Debug endpoint to check configuration."""
    try:
        debug_info = {
            "python_version": sys.version,
            "current_directory": os.getcwd(),
            "directory_contents": os.listdir('.'),
            "redis_url_exists": 'REDIS_TLS_URL' in os.environ,
            "redis_connection": None,
            "redis_ping": None,
            "environment_variables": {
                key: '[HIDDEN]' if 'SECRET' in key or 'URL' in key else value
                for key, value in os.environ.items()
            }
        }
        
        try:
            # Test Redis connection
            db.redis_client.ping()
            debug_info["redis_connection"] = "Success"
            debug_info["redis_ping"] = "Success"
        except Exception as e:
            debug_info["redis_connection"] = f"Error: {str(e)}"
            debug_info["redis_ping"] = f"Error: {str(e)}"
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# Remove any if __name__ == '__main__' block or application = app line
# The WSGI entry point is now in wsgi.py 