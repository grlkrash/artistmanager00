"""Main entry point for the Artist Manager Bot."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from typing import Dict, Any, Optional
import os
import logging
from datetime import datetime
from pathlib import Path
import sys
import signal
import asyncio
from dotenv import load_dotenv

from .models import ArtistProfile
from .team_manager import TeamManager
from .models import PaymentRequest, PaymentMethod, PaymentStatus
from .handlers.onboarding_handlers import OnboardingHandlers
from .bot_main import ArtistManagerBot
from .log import logger

# Load environment variables
load_dotenv()

def get_required_env(key: str) -> str:
    """Get a required environment variable or exit."""
    value = os.getenv(key)
    if not value:
        logger.error(f"Missing required environment variable: {key}")
        sys.exit(1)
    return value

async def run_bot():
    """Run the bot with proper lifecycle management."""
    try:
        # Get required environment variables
        telegram_token = get_required_env("TELEGRAM_BOT_TOKEN")  # Updated to match .env
        openai_api_key = get_required_env("OPENAI_API_KEY")
        
        # Optional environment variables with defaults
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        db_url = os.getenv("DATABASE_URL", "sqlite:///artist_manager.db")
        persistence_path = os.getenv("PERSISTENCE_PATH", "data/bot_persistence/bot_data.pickle")
        
        # Create data directories
        Path("data/bot_persistence").mkdir(parents=True, exist_ok=True)
        
        # Create default artist profile
        artist_profile = ArtistProfile(
            id="default",
            name="Artist",
            genre="",
            career_stage="emerging",
            goals=[],
            strengths=[],
            areas_for_improvement=["Not specified"],
            achievements=[],
            social_media={},
            streaming_profiles={},
            brand_guidelines={
                "description": "Default brand guidelines",
                "colors": [],
                "fonts": [],
                "tone": "professional"
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Initialize bot
        logger.info("Creating bot instance...")
        bot = ArtistManagerBot(
            telegram_token=telegram_token,
            artist_profile=artist_profile,
            openai_api_key=openai_api_key,
            model=model,
            db_url=db_url,
            persistence_path=persistence_path
        )
        
        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop, bot)))
        
        # Start the bot
        logger.info("Starting bot...")
        await bot.start()
        
        # Keep the bot running
        logger.info("Bot is running. Press CTRL+C to stop.")
        await asyncio.Event().wait()  # Run forever until interrupted
        
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        if 'bot' in locals():
            await bot.stop()
        sys.exit(1)

async def shutdown(sig: signal.Signals, loop: asyncio.AbstractEventLoop, bot: ArtistManagerBot):
    """Handle graceful shutdown."""
    logger.info(f"Received signal {sig.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    try:
        # Stop the bot first
        if bot:
            logger.info("Stopping bot...")
            await bot.stop()
        
        # Cancel other tasks
        logger.info(f"Cancelling {len(tasks)} outstanding tasks...")
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop the event loop
        logger.info("Stopping event loop...")
        loop.stop()
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    finally:
        sys.exit(0)

def main():
    """Entry point for the bot."""
    try:
        # Set up asyncio policy for Windows if needed
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Run the bot
        asyncio.run(run_bot())
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 