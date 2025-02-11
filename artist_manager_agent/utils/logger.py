"""Logging utilities for the Artist Manager Bot."""
import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Dict, Optional
import json
import traceback

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def log_event(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Log a structured event."""
    event_info = {
        'event_type': event_type,
        'timestamp': datetime.now().isoformat(),
        'data': data or {}
    }
    logger.info(f"Event: {json.dumps(event_info, indent=2)}")

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Log an error with full traceback and context."""
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc(),
        'timestamp': datetime.now().isoformat(),
        'context': context or {}
    }
    logger.error(f"Error occurred: {json.dumps(error_info, indent=2)}")

def setup_logging(level: int, format_str: str) -> None:
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Create formatters
    formatter = logging.Formatter(format_str)
    
    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/artist_manager.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    error_handler = logging.handlers.RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

# Create default logger
logger = get_logger("artist_manager")

# Configure logging
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

# Export for convenience
log = logger.info
error = logger.error
warning = logger.warning
debug = logger.debug

__all__ = [
    'get_logger',
    'log_event',
    'log_error',
    'logger',
    'log',
    'error',
    'warning',
    'debug'
] 