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

from .bot_base import BaseBot
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
        if bot and hasattr(bot, 'application'):
            await bot.application.stop()
            await bot.application.shutdown()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise

async def run_bot(bot: ArtistManagerBot) -> None:
    """Run the bot."""
    try:
        # Initialize application
        await bot.start()
        
        # Create stop event and signal handler
        stop_signal = asyncio.Event()
        shutdown_tasks = set()
        
        def signal_handler():
            """Handle shutdown signals in a thread-safe way."""
            loop = asyncio.get_running_loop()
            
            async def shutdown():
                try:
                    # Stop accepting new updates
                    if bot.application and bot.application.updater:
                        await bot.application.updater.stop()
                    
                    # Cancel all tasks
                    await bot.cancel_tasks()
                    
                    # Stop the bot
                    await bot.stop()
                    
                    # Set stop signal
                    stop_signal.set()
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
        
        # Wait for any pending shutdown tasks
        if shutdown_tasks:
            try:
                await asyncio.wait(shutdown_tasks, timeout=5.0)
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
            
            # Final stop attempt
            if bot:
                await bot.stop()
            
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")

def main():
    """Main entry point for the bot."""
    try:
        # Initialize logging first
        setup_logging(LOG_LEVEL, LOG_FORMAT)
        logger.info("Starting Artist Manager Bot...")
        
        # Load environment variables
        load_env_vars()
        
        # Check for existing instance
        check_running_instance()
        
        # Create data directory if it doesn't exist
        data_dir = Path(DATA_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize bot (loop will be created/managed internally)
        bot = None
        try:
            bot = ArtistManagerBot(BOT_TOKEN, data_dir)
            
            # Get the loop (it's already initialized by the bot)
            loop = asyncio.get_event_loop()
            
            # Run the bot
            loop.run_until_complete(run_bot(bot))
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            if bot:
                loop.run_until_complete(bot.stop())
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            if bot:
                loop.run_until_complete(bot.stop())
            raise
        finally:
            try:
                # Clean up the event loop
                if bot:
                    loop.run_until_complete(bot.cleanup_loop())
            except Exception as e:
                logger.error(f"Error during final cleanup: {e}")
            finally:
                # Always close the loop
                if loop and not loop.is_closed():
                    loop.close()
                asyncio.set_event_loop(None)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 