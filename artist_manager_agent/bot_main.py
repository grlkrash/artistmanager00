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
            # Initialize persistence first
            self.persistence = RobustPersistence(
                filepath=str(Path(persistence_path).resolve()),
                backup_count=3
            )
            
            # Initialize task manager with persistence
            self.task_manager_integration = TaskManagerIntegration(self.persistence)
            
            # Initialize base class and mixins
            super().__init__(
                telegram_token=telegram_token,
                artist_profile=artist_profile,
                openai_api_key=openai_api_key,
                model=model,
                db_url=db_url
            )
            
            logger.info("Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing bot: {str(e)}")
            raise
            
    async def start(self):
        """Start the bot with proper initialization."""
        try:
            # Initialize persistence
            await self._init_persistence()
            
            # Start the bot
            await super().run()
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            raise
            
    async def _init_persistence(self):
        """Initialize persistence and load data."""
        try:
            await self.persistence.load_data()
            await self.task_manager_integration.load_from_persistence()
        except Exception as e:
            logger.error(f"Error initializing persistence: {str(e)}")
            raise 