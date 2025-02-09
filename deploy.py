"""Deployment script for the Artist Manager Bot."""
import os
import sys
import logging
import asyncio
import signal
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

from artist_manager_agent.models import ArtistProfile
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.log import logger

# Load environment variables
load_dotenv()

def setup_directories():
    """Create necessary directories for the bot."""
    # Create data directory structure
    data_dir = Path("data")
    persistence_dir = data_dir / "bot_persistence"
    backups_dir = persistence_dir / "backups"
    
    # Create directories if they don't exist
    for directory in [data_dir, persistence_dir, backups_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")

async def shutdown(signal, loop, bot=None):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info(f"Received exit signal {signal.name}")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    if bot:
        logger.info("Stopping bot...")
        await bot.stop()
    
    [task.cancel() for task in tasks]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    """Main entry point for the bot."""
    try:
        # Setup directory structure
        setup_directories()
        
        # Get environment variables
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not telegram_token or not openai_api_key:
            logger.error("Missing required environment variables")
            sys.exit(1)
            
        # Create empty artist profile for now
        artist_profile = ArtistProfile(
            id="default",
            name="Artist",
            genre="",
            career_stage="emerging",
            goals=[],
            strengths=[],
            areas_for_improvement=["Not specified"],
            achievements=[],  # Empty list for achievements
            social_media={},  # Empty dict for social media
            streaming_profiles={},  # Empty dict for streaming profiles
            brand_guidelines={  # Dict for brand guidelines
                "description": "Default brand guidelines",
                "colors": [],
                "fonts": [],
                "tone": "professional"
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Initialize bot
        bot = ArtistManagerBot(
            telegram_token=telegram_token,
            artist_profile=artist_profile,
            openai_api_key=openai_api_key
        )
        
        # Get event loop
        loop = asyncio.get_event_loop()
        
        # Add signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s, loop, bot))
            )
            
        logger.info("Starting bot...")
        await bot.run()
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
    finally:
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1) 