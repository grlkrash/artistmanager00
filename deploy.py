"""Deployment script for the Artist Manager Bot."""
import os
from dotenv import load_dotenv

from artist_manager_agent.models import ArtistProfile
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.log import logger

# Load environment variables
load_dotenv()

def main() -> None:
    """Main entry point."""
    try:
        # Check required environment variables
        required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return

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

        # Run the bot
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
    finally:
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    main() 