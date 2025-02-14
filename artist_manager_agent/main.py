"""Main entry point for the Artist Manager Bot."""
import os
import sys
import signal
import atexit
import psutil
import asyncio
import logging
from pathlib import Path
import pickle

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)

from .core import Bot
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

def init_persistence():
    """Initialize persistence directory and file."""
    data_dir = Path(DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    persistence_path = Path(PERSISTENCE_PATH)
    if not persistence_path.exists():
        # Create initial empty persistence data
        initial_data = {
            "user_data": {},
            "chat_data": {},
            "bot_data": {},
            "callback_data": None,
            "conversations": {},
            "store_flags": {
                "_store_user_data": True,
                "_store_chat_data": True,
                "_store_bot_data": True,
                "_store_callback_data": True
            }
        }
        with open(persistence_path, "wb") as f:
            pickle.dump(initial_data, f)
    return persistence_path

async def run_bot(bot: Bot) -> None:
    """Run the bot."""
    stop_event = asyncio.Event()
    
    try:
        # Initialize and start bot
        try:
            logger.info("Starting bot...")
            await bot.start()
            logger.info("Bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start bot: {e}", exc_info=True)
            raise
        
        def signal_handler():
            """Handle shutdown signals."""
            logger.info("Received shutdown signal")
            asyncio.create_task(handle_shutdown())
            stop_event.set()
            
        async def handle_shutdown():
            """Handle shutdown gracefully."""
            try:
                logger.info("Initiating graceful shutdown...")
                
                # Stop accepting new updates
                if hasattr(bot, 'application') and bot.application.updater:
                    logger.info("Stopping updater...")
                    await bot.application.updater.stop()
                
                # Cancel any pending tasks
                if hasattr(bot, 'cancel_tasks'):
                    logger.info("Cancelling pending tasks...")
                    await bot.cancel_tasks()
                
                logger.info("Shutdown sequence completed")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}", exc_info=True)
        
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
        
        logger.info("Bot is running. Press Ctrl+C to stop")
        
        # Wait for stop signal
        await stop_event.wait()
        
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        try:
            logger.info("Starting cleanup process...")
            
            # Stop the bot
            try:
                logger.info("Stopping bot...")
                await bot.stop()
            except Exception as e:
                logger.error(f"Error stopping bot: {e}", exc_info=True)
            
            # Remove signal handlers
            try:
                loop = asyncio.get_running_loop()
                for sig in (signal.SIGINT, signal.SIGTERM):
                    try:
                        loop.remove_signal_handler(sig)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Error removing signal handlers: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            raise

async def main_async():
    """Async main function."""
    try:
        # Setup logging
        setup_logging(level=LOG_LEVEL, format_str=LOG_FORMAT)
        
        # Load environment variables
        load_env_vars()
        
        # Check for running instance
        check_running_instance()
        
        # Initialize persistence
        data_dir = init_persistence()
        
        # Initialize and run bot
        bot = Bot(token=BOT_TOKEN, data_dir=data_dir.parent)
        await run_bot(bot)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

def main():
    """Main entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 