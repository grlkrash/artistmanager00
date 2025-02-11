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
from typing import Optional, Dict, Any
from telegram.ext import CallbackQueryHandler

from .models import ArtistProfile
from .bot_main import ArtistManagerBot
from .log import logger
from .handlers.name_change_handler import get_name_change_handler
from .handlers.home_handler import get_home_handlers

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

async def initialize_bot(bot: ArtistManagerBot) -> None:
    """Initialize the bot with proper error handling."""
    try:
        # Create default profile if none exists
        if not bot.profiles:
            default_profile = ArtistProfile(
                id="default",
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
            bot.profiles["default"] = default_profile
            
        # Register handlers
        logger.info("Registering handlers...")
        application = bot.application
        
        # Add name change handlers
        name_change_handler = get_name_change_handler()
        application.add_handler(name_change_handler)
        
        # Add home handlers
        for handler in get_home_handlers():
            application.add_handler(handler)
            
        # Add global callback handler last
        application.add_handler(
            CallbackQueryHandler(bot.handle_callback),
            group=999
        )
        
        logger.info("All handlers registered successfully")
        
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        raise

async def run_bot(bot: ArtistManagerBot) -> None:
    """Run the bot with proper lifecycle management."""
    try:
        # Initialize bot
        await initialize_bot(bot)
        
        # Start polling
        await bot.start()
        
        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(bot.stop()))
            
        # Keep the bot running
        stop_event = asyncio.Event()
        await stop_event.wait()
        
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        raise
    finally:
        # Ensure proper cleanup
        await bot.stop()

def main():
    """Main entry point."""
    try:
        # Set up asyncio policy for Windows if needed
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create and initialize bot
            bot = ArtistManagerBot()
            
            # Run the bot
            loop.run_until_complete(run_bot(bot))
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            raise
        finally:
            try:
                # Clean up any remaining tasks
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