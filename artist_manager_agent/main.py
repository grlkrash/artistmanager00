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

async def cleanup_resources(bot: Bot) -> None:
    """Clean up bot resources."""
    if not bot:
        return
        
    try:
        logger.info("Starting cleanup process...")
        
        # Stop the bot first
        if hasattr(bot, 'stop'):
            try:
                logger.info("Stopping bot...")
                await bot.stop()
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
        
        # Clean up application
        if hasattr(bot, 'application'):
            try:
                logger.info("Stopping application...")
                await bot.application.stop()
                await bot.application.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down application: {e}")
        
        # Final cleanup
        if hasattr(bot, '_cleanup'):
            try:
                logger.info("Running final cleanup...")
                await bot._cleanup()
            except Exception as e:
                logger.error(f"Error in final cleanup: {e}")
                
        logger.info("Cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise

async def run_bot(bot: Bot) -> None:
    """Run the bot."""
    stop_signal = asyncio.Event()
    shutdown_tasks = set()
    
    try:
        # Initialize application with proper error handling
        try:
            logger.info("Starting bot...")
            await bot.start()
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
        
        def signal_handler():
            """Handle shutdown signals in a thread-safe way."""
            loop = asyncio.get_running_loop()
            
            async def shutdown():
                try:
                    logger.info("Initiating graceful shutdown...")
                    
                    # Stop accepting new updates
                    if bot.application and bot.application.updater:
                        logger.info("Stopping updater...")
                        await bot.application.updater.stop()
                    
                    # Cancel all tasks
                    logger.info("Cancelling tasks...")
                    await bot.cancel_tasks()
                    
                    # Stop the bot
                    logger.info("Stopping bot...")
                    await bot.stop()
                    
                    # Set stop signal
                    stop_signal.set()
                    
                    logger.info("Shutdown sequence completed")
                except Exception as e:
                    logger.error(f"Error during shutdown: {e}")
            
            # Ensure signal handling is thread-safe
            task = loop.create_task(shutdown())
            shutdown_tasks.add(task)
            task.add_done_callback(shutdown_tasks.discard)
        
        # Handle signals for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
        
        logger.info("Bot is running. Press Ctrl+C to stop")
        
        # Wait for stop signal
        await stop_signal.wait()
        
        # Wait for any pending shutdown tasks with timeout
        if shutdown_tasks:
            try:
                done, pending = await asyncio.wait(shutdown_tasks, timeout=5.0)
                if pending:
                    logger.warning(f"{len(pending)} shutdown tasks did not complete in time")
            except Exception as e:
                logger.error(f"Error waiting for shutdown tasks: {e}")
        
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise
    finally:
        # Ensure cleanup
        try:
            # Remove signal handlers
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.remove_signal_handler(sig)
                except Exception:
                    pass
            
            # Final cleanup
            await cleanup_resources(bot)
            
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")

async def main_async():
    """Async main function."""
    try:
        # Setup logging
        setup_logging(level=LOG_LEVEL, format_str=LOG_FORMAT)
        
        # Load environment variables
        load_env_vars()
        
        # Check for running instance
        check_running_instance()
        
        # Initialize bot
        data_dir = Path(DATA_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        bot = Bot(token=BOT_TOKEN, data_dir=data_dir)
        await bot.start()
        
        # Create stop event
        stop_event = asyncio.Event()
        
        # Handle shutdown signals
        def signal_handler(sig):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            stop_event.set()
            
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Keep the bot running until stop event is set
        try:
            await stop_event.wait()
        finally:
            logger.info("Stopping bot...")
            await bot.stop()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

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
            "conversations": {}
        }
        persistence_path.write_text(str(initial_data))
    return persistence_path

def main():
    """Main entry point for the bot."""
    # Load environment variables
    load_env_vars()
    
    # Setup logging
    setup_logging(level=LOG_LEVEL, fmt=LOG_FORMAT)
    
    # Check for running instance
    check_running_instance()
    
    # Initialize persistence
    data_dir = init_persistence()
    
    # Initialize and run bot
    bot = Bot(token=BOT_TOKEN, data_dir=data_dir.parent)
    bot.run()

if __name__ == "__main__":
    main() 