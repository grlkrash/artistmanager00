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
    
    try:
        # Cancel all tasks first
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        [task.cancel() for task in tasks]
        
        # Wait for tasks to complete with timeout
        logger.info("Waiting for tasks to complete...")
        await asyncio.wait(tasks, timeout=5)
        
        # Stop the bot if it exists
        if bot:
            logger.info("Stopping bot...")
            try:
                # Stop polling first
                await bot.application.updater.stop()
                # Stop the bot
                await bot.application.stop()
                # Final cleanup
                await bot.application.shutdown()
            except Exception as e:
                logger.error(f"Error stopping bot: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    finally:
        # Stop the event loop
        loop.stop()
        logger.info("Shutdown complete")

async def run_bot(bot):
    """Run the bot with proper lifecycle management."""
    try:
        # Initialize bot first
        logger.info("Initializing bot...")
        await bot.application.initialize()
        
        # Start the bot
        logger.info("Starting bot...")
        await bot.application.start()
        
        # Start polling in the background
        logger.info("Starting polling...")
        await bot.application.updater.start_polling()
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("Bot task cancelled, initiating graceful shutdown...")
        
        # Stop polling first
        logger.info("Stopping polling...")
        await bot.application.updater.stop()
        
        # Stop the bot
        logger.info("Stopping bot...")
        await bot.application.stop()
        
        # Final cleanup
        logger.info("Shutting down...")
        await bot.application.shutdown()
        
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        raise
    finally:
        logger.info("Bot stopped")

def main():
    """Main entry point for the bot."""
    loop = None
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
        
        # Setup event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Add signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s, loop, bot))
            )
            
        # Run bot until complete or interrupted
        loop.run_until_complete(run_bot(bot))
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        sys.exit(1)
    finally:
        if loop is not None:
            try:
                # Clean up any remaining tasks
                pending = asyncio.all_tasks(loop)
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                # Shut down async generators
                loop.run_until_complete(loop.shutdown_asyncgens())
                
                # Close the loop
                loop.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
            
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    main() 