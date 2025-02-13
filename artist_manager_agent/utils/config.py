"""Configuration settings for the Artist Manager Bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Try to load environment variables from different locations
def load_env_vars():
    """Load environment variables from .env file."""
    # Try current directory
    if os.path.exists(".env"):
        load_dotenv(".env")
        return True
    # Try project root
    project_env = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(project_env):
        load_dotenv(project_env)
        return True
    return False

# Load environment variables
load_env_vars()

# Bot Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("Warning: TELEGRAM_BOT_TOKEN not found in environment variables")
    # Try to read directly from .env file as fallback
    try:
        with open(".env") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    BOT_TOKEN = line.split("=", 1)[1].strip()
                    break
    except Exception as e:
        print(f"Error reading .env file: {e}")
    
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