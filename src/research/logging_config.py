import logging
import os

def setup_logging():
    """Configure logging with a level set by the LOG_LEVEL environment variable (default: INFO)."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
