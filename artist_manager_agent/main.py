"""Main entry point for the Artist Manager Bot."""
import os
import sys
import signal
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
import uuid
import threading

from .models import ArtistProfile
from .bot_main import ArtistManagerBot
from .log import logger

# Load environment variables
load_dotenv()

# Global state
_bot_instance = None
_bot_lock = threading.Lock()
_stop_event = None

def get_required_env(key: str) -> str:
    """Get a required environment variable or exit."""
    value = os.getenv(key)
    if not value:
        logger.error(f"Missing required environment variable: {key}")
        sys.exit(1)
    return value

async def shutdown(sig, loop, bot=None):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info(f"Received exit signal {signal.name}")
    
    try:
        # Stop the bot first if it exists
        if bot:
            logger.info("Stopping bot...")
            try:
                await bot.stop()
            except Exception as e:
                logger.error(f"Error stopping bot: {str(e)}")
        
        # Cancel all tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"Cancelling {len(tasks)} outstanding tasks")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop the event loop
        loop.stop()
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    finally:
        logger.info("Shutdown complete")

def get_bot_instance() -> ArtistManagerBot:
    """Get or create the bot instance."""
    global _bot_instance
    with _bot_lock:
        if _bot_instance is None:
            _bot_instance = ArtistManagerBot()
        return _bot_instance

async def run_bot():
    """Run the bot."""
    global _stop_event
    
    try:
        # Get bot instance
        bot = get_bot_instance()
        
        # Create default profile if needed
        if not bot.default_profile:
            default_profile = ArtistProfile(
                id=str(uuid.uuid4()),
                name="Default Artist",
                genre="Unknown",
                career_stage="Unknown",
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
                }
            )
            bot.default_profile = default_profile
        
        # Initialize the application
        logger.info("Starting bot...")
        
        # Initialize application first
        if not bot.application._initialized:
            await bot.application.initialize()
        
        # Start polling with clean state
        logger.info("Starting polling...")
        if not bot.application.updater.running:
            await bot.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "inline_query"]
            )
        
        # Create stop event
        _stop_event = asyncio.Event()
        
        # Wait for stop signal
        await _stop_event.wait()
        
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        raise
    finally:
        # Ensure cleanup happens
        try:
            if bot and hasattr(bot, 'application'):
                logger.info("Stopping bot...")
                if hasattr(bot.application, 'updater') and bot.application.updater.running:
                    await bot.application.updater.stop()
                if bot.application.running:
                    await bot.application.stop()
                    await bot.application.shutdown()
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")

def main():
    """Entry point for the bot."""
    try:
        # Set up asyncio policy for Windows if needed
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the bot
            loop.run_until_complete(run_bot())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            raise
        finally:
            try:
                # Clean up
                tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
                for task in tasks:
                    task.cancel()
                
                # Wait for tasks to complete with timeout
                if tasks:
                    loop.run_until_complete(
                        asyncio.wait(tasks, timeout=5)
                    )
                
                # Close the loop
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 