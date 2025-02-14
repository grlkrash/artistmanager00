"""Artist Manager Bot package."""
from .core import Bot
from .utils.logger import logger, log_event, log_error

__version__ = "0.1.0"

__all__ = [
    "Bot",
    "logger",
    "log_event",
    "log_error"
] 