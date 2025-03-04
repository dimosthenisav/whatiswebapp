import os
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import database as db
import slack_utils

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def index():
    """
    Simple health check endpoint.
    """
    return "WhatIs Slack Bot is running!"

@app.route('/admin')
def admin_dashboard():
    """
    Admin dashboard for managing terms and viewing analytics.
    In a production environment, you would want to add authentication.
    """
    return render_template('admin.html')

@app.route('/slack/whatis', methods=['POST'])
def slack_whatis():
    """
    Handle the /whatis slash command from Slack.
    """
    # Verify the request is coming from Slack
    if not slack_utils.verify_slack_request(
        request.get_data(),
        request.headers.get('X-Slack-Request-Timestamp', ''),
        request.headers.get('X-Slack-Signature', '')
    ):
        return jsonify({"error": "Invalid request"}), 403
    
    # Parse the form data from Slack
    slack_data = request.form
    
    # Get the term from the text field
    term = slack_data.get('text', '').strip()
    
    # Get user ID and channel ID
    user_id = slack_data.get('user_id', '')
    channel_id = slack_data.get('channel_id', '')
    
    # Get the response URL for delayed responses
    response_url = slack_data.get('response_url', '')
    
    # If no term was provided, return a help message
    if not term:
        return jsonify({
            "response_type": "ephemeral",
            "text": "Please provide a term to look up. Usage: `/whatis [term]`"
        })
    
    # Look up the term in the database
    term_data = db.get_term(term)
    
    # Log the query
    db.log_query(user_id, term, found=bool(term_data))
    
    # If the term wasn't found, look for similar terms
    similar_terms = None
    if not term_data:
        similar_terms = db.find_similar_terms(term)
    
    # Format the response message
    message = slack_utils.format_term_response(term_data, similar_terms)
    
    # Determine if the response should be public or private
    # In public channels, make the response visible to everyone
    # In direct messages, keep it private (ephemeral)
    response_type = "in_channel" if not slack_utils.is_direct_message(channel_id) else "ephemeral"
    
    # Return the response
    return jsonify({
        "response_type": response_type,
        "text": message
    })

@app.route('/admin/terms', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_terms():
    """
    Admin endpoint to manage terms in the glossary.
    This is a simple API endpoint for adding, updating, and deleting terms.
    In a production environment, you would want to add authentication.
    """
    # For demonstration purposes only - in a real app, add proper authentication
    
    if request.method == 'GET':
        # Get all terms
        terms = db.get_all_terms()
        return jsonify(terms)
    
    elif request.method == 'POST':
        # Add a new term
        data = request.json
        if not data or 'term' not in data or 'definition' not in data:
            return jsonify({"error": "Missing term or definition"}), 400
        
        success = db.add_term(data['term'], data['definition'])
        if success:
            return jsonify({"message": "Term added successfully"}), 201
        else:
            return jsonify({"error": "Term already exists"}), 409
    
    elif request.method == 'PUT':
        # Update an existing term
        data = request.json
        if not data or 'term' not in data or 'definition' not in data:
            return jsonify({"error": "Missing term or definition"}), 400
        
        success = db.update_term(data['term'], data['definition'])
        if success:
            return jsonify({"message": "Term updated successfully"})
        else:
            return jsonify({"error": "Term not found"}), 404
    
    elif request.method == 'DELETE':
        # Delete a term
        data = request.json
        if not data or 'term' not in data:
            return jsonify({"error": "Missing term"}), 400
        
        success = db.delete_term(data['term'])
        if success:
            return jsonify({"message": "Term deleted successfully"})
        else:
            return jsonify({"error": "Term not found"}), 404

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

if __name__ == '__main__':
    # Make sure the database is initialized
    db.init_db()
    
    # Get the port from the environment variable or use 5000 as default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=True) 