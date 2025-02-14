"""Configuration settings for the Artist Manager Bot."""
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

def load_env_vars():
    """Load environment variables from .env file."""
    # Try current directory
    if os.path.exists(".env"):
        logger.info("Loading .env from current directory")
        load_dotenv(".env")
        return True
        
    # Try project root
    project_env = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(project_env):
        logger.info(f"Loading .env from {project_env}")
        load_dotenv(project_env)
        return True
        
    logger.warning("No .env file found")
    return False

# Load environment variables
load_env_vars()

# Bot Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
    # Try to read directly from .env file as fallback
    try:
        with open(".env") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    BOT_TOKEN = line.split("=", 1)[1].strip()
                    logger.info("Found bot token in .env file")
                    break
    except Exception as e:
        logger.error(f"Error reading .env file: {e}")
    
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
PERSISTENCE_PATH = os.path.join(DATA_DIR, "persistence.pickle")

# Database
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/bot.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# OpenAI
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "150"))

# Create data directory if it doesn't exist
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

# Log configuration
logger.info(f"Data directory: {DATA_DIR}")
logger.info(f"Database URL: {DB_URL}")
logger.info(f"Log level: {LOG_LEVEL}")
logger.info(f"OpenAI model: {DEFAULT_MODEL}")
logger.info("Bot token loaded" if BOT_TOKEN else "No bot token found") 