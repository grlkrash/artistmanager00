"""Main bot class for the Artist Manager Bot."""
import os
import sys
import asyncio
import logging
from pathlib import Path

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    PicklePersistence
)

from .bot_base import BaseBot
from .handlers.core_handlers import CoreHandlers
from .handlers.goal_handlers import GoalHandlers
from .handlers.task_handlers import TaskHandlers
from .handlers.project_handlers import ProjectHandlers
from .handlers.music_handlers import MusicHandlers
from .handlers.blockchain_handlers import BlockchainHandlers
from .handlers.auto_handlers import AutoHandlers
from .handlers.team_handlers import TeamHandlers
from .handlers.onboarding_handlers import OnboardingHandlers
from .handlers.home_handler import HomeHandlers
from .handlers.name_change_handler import NameChangeHandlers

from .utils.logger import get_logger
from .utils.config import (
    BOT_TOKEN,
    DATA_DIR,
    PERSISTENCE_PATH
)

class ArtistManagerBot(BaseBot):
    """Main bot class that inherits from base bot."""
    
    def __init__(self, token: str, data_dir: Path):
        """Initialize the bot."""
        super().__init__(db_url=str(data_dir / "bot.db"))
        
        self.token = token
        self.data_dir = data_dir
        
        # Set up persistence
        persistence = PicklePersistence(
            filepath=str(data_dir / "bot_persistence"),
            store_data={"user_data", "chat_data", "bot_data", "callback_data"},
            update_interval=60
        )
        
        # Initialize application
        self.application = Application.builder() \
            .token(token) \
            .persistence(persistence) \
            .arbitrary_callback_data(True) \
            .build()
            
        # Initialize handlers
        self.onboarding = OnboardingHandlers(self)
        self.core_handlers = CoreHandlers(self)
        self.goal_handlers = GoalHandlers(self)
        self.task_handlers = TaskHandlers(self)
        self.project_handlers = ProjectHandlers(self)
        self.music_handlers = MusicHandlers(self)
        self.blockchain_handlers = BlockchainHandlers(self)
        self.auto_handlers = AutoHandlers(self)
        self.team_handlers = TeamHandlers(self)
        self.home_handlers = HomeHandlers(self)
        self.name_change_handlers = NameChangeHandlers(self)
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Bot initialized successfully")

    def _register_handlers(self):
        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.core_handlers.start))
        self.application.add_handler(CommandHandler("help", self.core_handlers.help))
        
        # Register message handlers
        self.application.add_handler(MessageHandler(filters.TEXT, self.core_handlers.handle_message))
        
        # Register callback query handlers
        self.application.add_handler(CallbackQueryHandler(self.core_handlers.handle_callback_query))
        
        # Register error handler
        self.application.add_error_handler(self.core_handlers.handle_error)

    async def start(self):
        """Start the bot with proper initialization."""
        try:
            # Ensure we're not already running
            if self._running:
                logger.warning("Bot is already running")
                return
                
            # Ensure we have an event loop
            if not self._event_loop or self._event_loop.is_closed():
                try:
                    self._event_loop = asyncio.get_event_loop()
                except RuntimeError:
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
                try:
                    # Cancel all running tasks
                    pending = asyncio.all_tasks(self._event_loop)
                    for task in pending:
                        task.cancel()
                    # Wait for tasks to complete with timeout
                    await asyncio.wait(pending, timeout=5.0)
                    # Close the event loop
                    self._event_loop.stop()
                    self._event_loop.close()
                except Exception as e:
                    logger.error(f"Error cleaning up event loop: {str(e)}")
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            self._running = False
            raise 