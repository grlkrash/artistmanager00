"""Deploy script for the Artist Manager Bot."""
import os
import sys
import signal
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from artist_manager_agent.bot_main import ArtistManagerBot
from artist_manager_agent.models import ArtistProfile
from artist_manager_agent.log import logger, log_event, log_error

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def setup_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        "data",
        "data/bot_persistence",
        "data/bot_persistence/backups"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True)
            logger.info(f"Created directory: {directory}")

async def shutdown(signal, loop, bot=None):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info(f"Received exit signal {signal.name}")
    
    if bot:
        logger.info("Stopping bot...")
        await bot.stop()
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    [task.cancel() for task in tasks]
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
        bot = ArtistManagerBot(
            telegram_token=telegram_token,
            artist_profile=artist_profile,
            openai_api_key=openai_api_key,
            persistence_path="data/bot_persistence/bot_data.pickle"
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
        await bot.start()
        
        # Run forever
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        sys.exit(1)
    finally:
        loop.close()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main()) 