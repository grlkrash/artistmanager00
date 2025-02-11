"""Artist Manager Bot package."""
from .bot_main import ArtistManagerBot
from .utils.logger import logger, log_event, log_error

__version__ = "0.1.0"

__all__ = ["ArtistManagerBot", "logger", "log_event", "log_error"] 