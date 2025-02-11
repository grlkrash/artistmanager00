"""Main entry point for the Artist Manager Bot."""
import os
import sys
import signal
import atexit
import psutil
import asyncio
import logging
from pathlib import Path

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    PicklePersistence
)

from .bot_main import ArtistManagerBot
from .utils.logger import get_logger, setup_logging
from .utils.config import (
    BOT_TOKEN,
    DATA_DIR,
    PERSISTENCE_PATH,
    LOG_LEVEL,
    LOG_FORMAT
)

logger = get_logger(__name__)

def write_pid_file():
    """Write PID file for process tracking."""
    pid = os.getpid()
    pid_file = Path(DATA_DIR) / "bot.pid"
    pid_file.write_text(str(pid))
    return pid_file

def cleanup_pid_file(pid_file):
    """Clean up PID file on exit."""
    try:
        pid_file.unlink()
    except Exception as e:
        logger.error(f"Error removing PID file: {e}")

def kill_existing_bot():
    """Kill any existing bot process."""
    try:
        pid_file = Path(DATA_DIR) / "bot.pid"
        if pid_file.exists():
            pid = int(pid_file.read_text())
            try:
                process = psutil.Process(pid)
                if process.is_running():
                    process.terminate()
                    process.wait(timeout=5)
            except psutil.NoSuchProcess:
                pass
            pid_file.unlink()
    except Exception as e:
        logger.error(f"Error killing existing bot: {e}")

async def cleanup_resources(bot: ArtistManagerBot) -> None:
    """Cleanup resources before shutdown."""
    try:
        logger.info("Cleaning up bot resources...")
        # Save persistence data
        if hasattr(bot, 'persistence') and bot.persistence:
            await bot.persistence.flush()
        # Close any open connections
        if hasattr(bot, 'application'):
            await bot.application.shutdown()
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

def signal_handler(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}")
    sys.exit(0)

async def initialize_bot(bot: ArtistManagerBot) -> None:
    """Initialize the bot with proper error handling."""
    try:
        logger.info("Starting bot initialization...")
        
        # 1. Clear existing state
        if hasattr(bot, 'application') and bot.application:
            logger.info("Shutting down existing application...")
            await bot.application.shutdown()
            bot.application.handlers.clear()
            
        # 2. Reset initialization flags
        bot._initialized = False
        logger.info("Reset initialization flags")
        
        # 3. Clear any existing handler instances
        bot.onboarding = None
        bot.core_handlers = None
        bot.goal_handlers = None
        bot.task_handlers = None
        bot.project_handlers = None
        bot.music_handlers = None
        bot.blockchain_handlers = None
        bot.auto_handlers = None
        bot.team_handlers = None
        bot.home_handlers = None
        bot.name_change_handlers = None
        logger.info("Cleared existing handler instances")
        
        # 4. Initialize components and register handlers
        await bot._register_and_load()
        logger.info("Completed bot initialization")
        
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        raise

async def run_bot(bot: ArtistManagerBot) -> None:
    """Run the bot with proper lifecycle management."""
    try:
        # Kill any existing bot process
        kill_existing_bot()
        
        # Write PID file
        pid_file = write_pid_file()
        atexit.register(cleanup_pid_file, pid_file)
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start polling with clean state
        logger.info("Starting polling...")
        await bot.application.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "inline_query"],
            close_loop=False
        )
        
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        raise
    finally:
        await cleanup_resources(bot)

def main():
    """Main entry point for the bot."""
    try:
        # Set up logging
        setup_logging(LOG_LEVEL, LOG_FORMAT)
        logger.info("Starting Artist Manager Bot...")
        
        # Create data directory if it doesn't exist
        data_dir = Path(DATA_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize bot
        bot = ArtistManagerBot(BOT_TOKEN, data_dir)
        
        # Run the bot
        asyncio.run(run_bot(bot))
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 