import os
import json
from datetime import datetime
from fuzzywuzzy import fuzz
import redis
import logging
import sys
import traceback
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Redis configuration with retry mechanism
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

def get_redis_client():
    """Create and return a Redis client with retries."""
    REDIS_URL = os.getenv('REDIS_TLS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379'))
    logger.debug("Attempting to connect to Redis...")
    logger.debug(f"Environment variables present: REDIS_TLS_URL={'REDIS_TLS_URL' in os.environ}, REDIS_URL={'REDIS_URL' in os.environ}")
    
    for attempt in range(MAX_RETRIES):
        try:
            # Configure Redis client with SSL/TLS for Upstash
            client = redis.from_url(
                REDIS_URL,
                ssl=True,
                ssl_cert_reqs=None,
                decode_responses=True
            )
            # Test the connection
            client.ping()
            logger.debug(f"Successfully connected to Redis on attempt {attempt + 1}")
            return client
        except Exception as e:
            logger.error(f"Redis connection attempt {attempt + 1} failed!")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("All Redis connection attempts failed!")
                logger.error(f"Traceback:\n{''.join(traceback.format_tb(sys.exc_info()[2]))}")
                raise

# Initialize Redis client
try:
    redis_client = get_redis_client()
except Exception as e:
    logger.error("Failed to initialize Redis client!")
    logger.error(f"Error: {str(e)}")
    redis_client = None

def init_db():
    """
    Initialize the database if needed.
    For Redis, we don't need to create tables, but we can set up initial data.
    """
    if redis_client is None:
        logger.error("Cannot initialize database - Redis client is not initialized")
        return False
        
    try:
        logger.debug("Checking if database needs initialization")
        if not redis_client.exists('terms:count'):
            redis_client.set('terms:count', 0)
            logger.debug("Database initialized with terms:count = 0")
            # Add a test term to verify write operations
            test_term = {
                'term': 'test',
                'definition': 'This is a test term.',
                'created_at': datetime.utcnow().isoformat()
            }
            redis_client.set('term:test', json.dumps(test_term))
            logger.debug("Test term added successfully")
        return True
    except Exception as e:
        logger.error("Database initialization error!")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Traceback:\n{''.join(traceback.format_tb(sys.exc_info()[2]))}")
        return False

def get_term(term):
    """Get a term from the database."""
    try:
        term_key = f'term:{term.lower()}'
        term_data = redis_client.get(term_key)
        if term_data:
            return json.loads(term_data)
        return None
    except Exception as e:
        logger.error(f"Error getting term: {str(e)}")
        return None

def find_similar_terms(term, threshold=80):
    """Find similar terms."""
    try:
        similar_terms = []
        # Get all terms
        for key in redis_client.scan_iter("term:*"):
            term_data = redis_client.get(key)
            if term_data:
                term_obj = json.loads(term_data)
                similarity = fuzz.ratio(term.lower(), term_obj['term'].lower())
                if similarity >= threshold:
                    similar_terms.append(term_obj)
        
        similar_terms.sort(key=lambda x: fuzz.ratio(term.lower(), x['term'].lower()), reverse=True)
        return similar_terms
    except Exception as e:
        logger.error(f"Error finding similar terms: {str(e)}")
        return []

def log_query(user_id, term, found):
    """Log a query."""
    try:
        log_data = {
            'user_id': user_id,
            'term': term,
            'found': found,
            'timestamp': datetime.utcnow().isoformat()
        }
        redis_client.rpush('logs', json.dumps(log_data))
    except Exception as e:
        logger.error(f"Error logging query: {str(e)}")

def add_term(term, definition):
    """Add a new term."""
    try:
        term_key = f'term:{term.lower()}'
        if redis_client.exists(term_key):
            return False
        
        term_data = {
            'term': term,
            'definition': definition,
            'created_at': datetime.utcnow().isoformat()
        }
        redis_client.set(term_key, json.dumps(term_data))
        redis_client.incr('terms:count')
        return True
    except Exception as e:
        logger.error(f"Error adding term: {str(e)}")
        return False

def update_term(term, definition):
    """Update an existing term."""
    try:
        term_key = f'term:{term.lower()}'
        if not redis_client.exists(term_key):
            return False
        
        term_data = json.loads(redis_client.get(term_key))
        term_data['definition'] = definition
        term_data['updated_at'] = datetime.utcnow().isoformat()
        redis_client.set(term_key, json.dumps(term_data))
        return True
    except Exception as e:
        logger.error(f"Error updating term: {str(e)}")
        return False

def delete_term(term):
    """Delete a term."""
    try:
        term_key = f'term:{term.lower()}'
        if redis_client.exists(term_key):
            redis_client.delete(term_key)
            redis_client.decr('terms:count')
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting term: {str(e)}")
        return False

def get_all_terms():
    """Get all terms."""
    try:
        terms = []
        for key in redis_client.scan_iter("term:*"):
            term_data = redis_client.get(key)
            if term_data:
                terms.append(json.loads(term_data))
        return sorted(terms, key=lambda x: x['term'].lower())
    except Exception as e:
        logger.error(f"Error getting all terms: {str(e)}")
        return []

# Initialize the database when this module is imported
init_db() 