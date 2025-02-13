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
    LOG_FORMAT,
    load_env_vars
)

logger = get_logger(__name__)

def check_running_instance():
    """Check if another instance is running and kill it."""
    pid_file = Path(DATA_DIR) / "bot.pid"
    
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text())
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                if process.name().startswith('python'):
                    logger.info(f"Killing existing bot process {pid}")
                    process.terminate()
                    process.wait(timeout=5)
        except (ValueError, psutil.NoSuchProcess, psutil.TimeoutExpired) as e:
            logger.warning(f"Error handling existing process: {e}")
    
    # Write current PID
    pid_file.write_text(str(os.getpid()))
    atexit.register(lambda: pid_file.unlink(missing_ok=True))

async def cleanup_resources(bot: ArtistManagerBot) -> None:
    """Clean up bot resources."""
    try:
        await bot.application.stop()
        await bot.application.shutdown()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise

async def run_bot(bot: ArtistManagerBot) -> None:
    """Run the bot."""
    try:
        # Initialize application
        await bot.application.initialize()
        await bot.application.start()
        await bot.application.updater.start_polling()
        
        # Keep the bot running until interrupted
        try:
            # Create stop signal
            stop_signal = asyncio.Event()
            
            # Handle signals for graceful shutdown
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop_signal.set)
            
            logger.info("Bot is running. Press Ctrl+C to stop")
            await stop_signal.wait()
            
        except asyncio.CancelledError:
            pass
        finally:
            # Remove signal handlers
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)
    
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise
    finally:
        try:
            # Ensure proper cleanup
            logger.info("Stopping bot...")
            await bot.application.stop()
            logger.info("Shutting down bot...")
            await bot.application.shutdown()
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise

def main():
    """Main entry point for the bot."""
    try:
        # Initialize logging
        setup_logging(LOG_LEVEL, LOG_FORMAT)
        
        # Load environment variables
        load_env_vars()
        
        # Check for existing instance
        check_running_instance()
        
        # Create data directory if it doesn't exist
        data_dir = Path(DATA_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Starting Artist Manager Bot...")
        
        # Initialize the bot
        bot = ArtistManagerBot(BOT_TOKEN, data_dir)
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the bot
            loop.run_until_complete(run_bot(bot))
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            # Clean up the loop
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception as e:
                logger.error(f"Error cleaning up event loop: {e}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 