"""Main bot class that combines base functionality with mixins."""
from datetime import datetime
from pathlib import Path
from typing import Optional, ClassVar
from .bot_base import ArtistManagerBot as ArtistManagerBotBase
from .bot_goals import GoalsMixin
from .persistence import RobustPersistence
from .task_manager_integration import TaskManagerIntegration
from .models import ArtistProfile
from .log import logger
import asyncio
import threading

class ArtistManagerBot(ArtistManagerBotBase, GoalsMixin):
    """Main bot class that inherits from base and mixins."""
    
    _instance: ClassVar[Optional['ArtistManagerBot']] = None
    _lock = threading.Lock()
    _initialized = False
    _running = False
    _event_loop = None
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance
    
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
        if self._initialized:
            return
            
        try:
            with self._lock:
                if not self._initialized:
                    # Initialize base class first
                    logger.info("Initializing bot...")
                    super().__init__(db_url=db_url)
                    
                    # Store initial profile
                    if artist_profile:
                        self.profiles[str(artist_profile.id)] = artist_profile
                    
                    # Initialize event loop
                    if not self._event_loop:
                        self._event_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self._event_loop)
                    
                    self._initialized = True
                    self._running = False
                    logger.info("Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing bot: {str(e)}")
            raise
            
    async def start(self):
        """Start the bot with proper initialization."""
        try:
            # Ensure we're not already running
            if self._running:
                logger.warning("Bot is already running")
                return
                
            # Ensure we have an event loop
            if not self._event_loop:
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)
            
            # Start base class
            logger.info("Starting bot...")
            await super().start()
            
            # Initialize any additional components
            logger.info("Initializing additional components...")
            
            # Start background tasks if needed
            logger.info("Starting background tasks...")
            
            self._running = True
            logger.info("Bot started successfully")
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            self._running = False
            raise
            
    async def stop(self):
        """Stop the bot and cleanup."""
        try:
            if not self._running:
                logger.warning("Bot is not running")
                return
                
            # Stop background tasks first
            logger.info("Stopping background tasks...")
            
            # Cleanup additional components
            logger.info("Cleaning up components...")
            
            # Stop base class last
            logger.info("Stopping bot...")
            await super().stop()
            
            self._running = False
            
            # Clean up event loop
            if self._event_loop and not self._event_loop.is_closed():
                pending = asyncio.all_tasks(self._event_loop)
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                self._event_loop.stop()
                self._event_loop.close()
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            self._running = False
            raise 