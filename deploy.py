"""Deployment script for the Artist Manager Bot."""
import os
import sys
import asyncio
import signal
from datetime import datetime
import logging
from dotenv import load_dotenv
import psutil

from artist_manager_agent.agent import ArtistManagerAgent
from artist_manager_agent.models import ArtistProfile
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.log import logger, log_event, log_error

# Load environment variables
load_dotenv()

def handle_exception(loop, context):
    """Handle exceptions in the event loop."""
    msg = context.get("exception", context["message"])
    logger.error(f"Caught exception: {msg}")
    if "exception" in context:
        logger.error(f"Exception traceback: {context['exception'].__traceback__}")

async def shutdown(sig: signal.Signals, bot: ArtistManagerBot, loop: asyncio.AbstractEventLoop) -> None:
    """Handle graceful shutdown."""
    logger.info(f"Received exit signal {sig.name}...")
    try:
        tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        await bot.app.stop()
        logger.info("Bot stopped successfully")
    except Exception as e:
        log_error(e, {"shutdown": "bot_stop"})
    finally:
        loop.stop()

async def run_bot() -> None:
    """Run the bot with proper initialization and error handling."""
    # Check required environment variables
    required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return

    try:
        # Initialize bot
        artist_profile = ArtistProfile(
            id="default",
            name="Artist",
            genre="",
            career_stage="emerging",
            goals=[],
            strengths=[],
            areas_for_improvement=[],
            achievements=[],
            social_media={},
            streaming_profiles={},
            brand_guidelines={}
        )
        
        bot = ArtistManagerBot(
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            artist_profile=artist_profile,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            db_url=os.getenv("DATABASE_URL", "sqlite:///artist_manager.db")
        )

        # Get the current event loop
        loop = asyncio.get_running_loop()
        
        # Set up exception handler
        loop.set_exception_handler(handle_exception)
        
        # Set up signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s, bot, loop))
            )

        # Run the bot
        await bot.run()

    except Exception as e:
        log_error(e, {"main": "bot_initialization"})
        raise

def main() -> None:
    """Main entry point."""
    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the bot
        loop.run_until_complete(run_bot())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        except Exception as e:
            logger.error(f"Error during loop cleanup: {str(e)}")
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    main() 