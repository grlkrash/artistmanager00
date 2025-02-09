"""Enhanced logging configuration for the artist manager agent."""
import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Dict
import json
import traceback

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
logger = logging.getLogger("artist_manager")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# File handler for general logs
file_handler = logging.handlers.RotatingFileHandler(
    'logs/artist_manager.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
file_handler.setFormatter(file_format)

# Error file handler
error_handler = logging.handlers.RotatingFileHandler(
    'logs/errors.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(file_format)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_handler)

def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """Log an error with full traceback and context."""
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc(),
        'timestamp': datetime.now().isoformat(),
        'context': context or {}
    }
    logger.error(f"Error occurred: {json.dumps(error_info, indent=2)}")

def log_event(event_type: str, data: Dict[str, Any]) -> None:
    """Log a structured event."""
    event_info = {
        'event_type': event_type,
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    logger.info(f"Event: {json.dumps(event_info, indent=2)}")

# Export for convenience
log = logger.info
error = logger.error
warning = logger.warning
debug = logger.debug 