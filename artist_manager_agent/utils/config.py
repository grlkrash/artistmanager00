"""Configuration settings for the Artist Manager Bot."""
import os
from pathlib import Path
import logging

# Bot settings
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_bot_token_here")

# Directory settings
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PERSISTENCE_PATH = DATA_DIR / "bot_persistence"

# Logging settings
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Model settings
DEFAULT_MODEL = "gpt-4"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2000

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PERSISTENCE_PATH.mkdir(parents=True, exist_ok=True) 