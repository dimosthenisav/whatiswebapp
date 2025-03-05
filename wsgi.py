import sys
import logging
from app import app

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info(f"Starting application with Python version: {sys.version}")
logger.info(f"sys.path: {sys.path}")

# This is the entry point for Vercel
application = app

if __name__ == '__main__':
    try:
        logger.info("Starting development server")
        app.run()
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True) 