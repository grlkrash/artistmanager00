"""Main bot class that combines base functionality with mixins."""
from datetime import datetime
from pathlib import Path
from typing import Optional
from .bot_base import ArtistManagerBotBase
from .bot_goals import GoalsMixin
from .persistence import RobustPersistence
from .task_manager_integration import TaskManagerIntegration
from .models import ArtistProfile
from .log import logger

class ArtistManagerBot(ArtistManagerBotBase, GoalsMixin):
    """Main bot class that inherits from base and mixins."""
    
    def __init__(
        self,
        telegram_token: str = None,
        artist_profile: ArtistProfile = None,
        openai_api_key: str = None,
        model: str = "gpt-3.5-turbo",
        db_url: str = "sqlite:///artist_manager.db",
        persistence_path: str = "bot_data.pickle"
    ):
        """Initialize the bot with proper dependency order."""
        try:
            # Initialize base class and mixins
            super().__init__(
                telegram_token=telegram_token,
                artist_profile=artist_profile,
                openai_api_key=openai_api_key,
                model=model,
                db_url=db_url,
                persistence_path=persistence_path
            )
            
            logger.info("Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing bot: {str(e)}")
            raise
            
    async def start(self):
        """Start the bot with proper initialization."""
        try:
            # Initialize persistence
            await self.persistence.load()
            await self.task_manager_integration.load_from_persistence()
            
            # Start the bot
            await super().start()
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            raise
            
    async def stop(self):
        """Stop the bot and cleanup."""
        try:
            # Save persistence data
            await self.persistence.flush()
            await self.task_manager_integration.save_to_persistence()
            
            # Cleanup handlers
            self.handler_registry.clear()
            
            # Stop the bot
            await super().stop()
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            raise 