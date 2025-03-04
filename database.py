import sqlite3
import os
from datetime import datetime

# Database file path
DB_PATH = "whatis.db"

def init_db():
    """
    Initialize the database by creating necessary tables if they don't exist.
    """
    # Connect to the database (creates the file if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create terms table to store glossary terms and definitions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term TEXT UNIQUE NOT NULL,
        definition TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create logs table to track usage analytics
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        term TEXT NOT NULL,
        found BOOLEAN NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database initialized successfully.")

def get_term(term):
    """
    Get the definition of a term from the database.
    
    Args:
        term (str): The term to look up
        
    Returns:
        dict or None: Dictionary with term info if found, None otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    # Case-insensitive search for the exact term
    cursor.execute("SELECT * FROM terms WHERE LOWER(term) = LOWER(?)", (term,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        # Convert SQLite Row to dictionary
        return dict(result)
    return None

def find_similar_terms(term, threshold=80):
    """
    Find similar terms using basic string comparison.
    
    Args:
        term (str): The term to find similar matches for
        threshold (int): Similarity threshold (0-100)
        
    Returns:
        list: List of similar terms with their definitions
    """
    from fuzzywuzzy import fuzz
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all terms from the database
    cursor.execute("SELECT * FROM terms")
    all_terms = cursor.fetchall()
    conn.close()
    
    similar_terms = []
    for db_term in all_terms:
        # Calculate similarity ratio
        similarity = fuzz.ratio(term.lower(), db_term['term'].lower())
        if similarity >= threshold:
            similar_terms.append(dict(db_term))
    
    # Sort by similarity (highest first)
    similar_terms.sort(key=lambda x: fuzz.ratio(term.lower(), x['term'].lower()), reverse=True)
    
    return similar_terms

def log_query(user_id, term, found):
    """
    Log a query to the database for analytics.
    
    Args:
        user_id (str): Slack user ID
        term (str): The term that was queried
        found (bool): Whether the term was found in the database
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO logs (user_id, term, found) VALUES (?, ?, ?)",
        (user_id, term, found)
    )
    
    conn.commit()
    conn.close()

def add_term(term, definition):
    """
    Add a new term to the glossary.
    
    Args:
        term (str): The term to add
        definition (str): The definition of the term
        
    Returns:
        bool: True if successful, False if term already exists
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO terms (term, definition) VALUES (?, ?)",
            (term, definition)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # Term already exists (due to UNIQUE constraint)
        success = False
    
    conn.close()
    return success

def update_term(term, definition):
    """
    Update an existing term's definition.
    
    Args:
        term (str): The term to update
        definition (str): The new definition
        
    Returns:
        bool: True if successful, False if term doesn't exist
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE terms SET definition = ?, updated_at = CURRENT_TIMESTAMP WHERE LOWER(term) = LOWER(?)",
        (definition, term)
    )
    
    # Check if any rows were affected
    success = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return success

def delete_term(term):
    """
    Delete a term from the glossary.
    
    Args:
        term (str): The term to delete
        
    Returns:
        bool: True if successful, False if term doesn't exist
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM terms WHERE LOWER(term) = LOWER(?)", (term,))
    
    # Check if any rows were affected
    success = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return success

def get_all_terms():
    """
    Get all terms from the glossary.
    
    Returns:
        list: List of dictionaries containing all terms and definitions
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM terms ORDER BY term")
    results = cursor.fetchall()
    
    conn.close()
    
    # Convert SQLite Row objects to dictionaries
    return [dict(row) for row in results]

# Initialize the database when this module is imported
if not os.path.exists(DB_PATH):
    init_db() 