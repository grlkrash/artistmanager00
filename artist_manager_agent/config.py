"""Configuration settings for the Artist Manager bot."""

import os
from pathlib import Path

# Bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Database settings
DB_URL = os.getenv("DATABASE_URL", "sqlite:///artist_manager.db")

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Persistence settings
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PERSISTENCE_PATH = str(DATA_DIR / "bot_data.pickle")

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Default model settings
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048 