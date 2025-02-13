"""Main bot class for the Artist Manager Bot."""
import os
import sys
import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    PicklePersistence,
    ContextTypes,
    ConversationHandler
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

logger = get_logger(__name__)

class ArtistManagerBot(BaseBot):
    """Main bot class that inherits from base bot."""
    
    def __init__(self, token: str, data_dir: Path):
        """Initialize the bot."""
        if not token:
            raise ValueError("Bot token cannot be empty")
            
        logger.info("Initializing ArtistManagerBot...")
        # Set token before calling super().__init__
        self.token = token
        self.data_dir = data_dir
        logger.debug(f"Bot initialized with data directory: {data_dir}")
        
        # Initialize base class after setting token
        super().__init__(db_url=str(data_dir / "bot.db"))
        
        # Initialize handlers
        self._init_handlers()
        
        logger.info("Bot initialized successfully")

    def _init_handlers(self):
        """Initialize all handlers."""
        try:
            logger.info("Initializing bot handlers...")
            
            # Initialize all handlers
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
            
        except Exception as e:
            logger.error(f"Error initializing handlers: {e}")
            raise

    def _register_handlers(self):
        """Register all handlers."""
        try:
            # Clear any existing handlers
            if hasattr(self.application, 'handlers'):
                self.application.handlers.clear()
                logger.info("Cleared existing handlers")
            
            # Add debug handler to log all updates
            async def debug_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                logger.debug("=== Debug Handler Start ===")
                logger.debug(f"Raw update: {update.to_dict()}")
                logger.debug(f"Update type: {type(update)}")
                if update.effective_message:
                    logger.debug(f"Message type: {type(update.effective_message)}")
                    logger.debug(f"Message content: {update.effective_message.to_dict()}")
                    if update.effective_message.text:
                        logger.debug(f"Message text: {update.effective_message.text}")
                        if update.effective_message.text.startswith('/'):
                            logger.debug(f"Command detected: {update.effective_message.text}")
                logger.debug("=== Debug Handler End ===")
                return None
            
            self.application.add_handler(MessageHandler(filters.ALL, debug_handler), group=-1)
            logger.info("Added enhanced debug handler")
            
            # Register handlers in priority order
            handlers = [
                (0, self.onboarding.get_handlers(), "Onboarding handlers"),
                (1, self.core_handlers.get_handlers(), "Core handlers"),
                (2, self.goal_handlers.get_handlers(), "Goal handlers"),
                (3, self.task_handlers.get_handlers(), "Task handlers"),
                (4, self.project_handlers.get_handlers(), "Project handlers"),
                (5, self.music_handlers.get_handlers(), "Music handlers"),
                (6, self.blockchain_handlers.get_handlers(), "Blockchain handlers"),
                (7, self.auto_handlers.get_handlers(), "Auto mode handlers"),
                (8, self.team_handlers.get_handlers(), "Team handlers"),
                (9, self.home_handlers.get_handlers(), "Home handlers"),
                (10, self.name_change_handlers.get_handlers(), "Name change handlers")
            ]
            
            # Track registered handlers to avoid duplicates
            registered_handlers = set()
            
            # Register each handler group
            for group, handler_list, name in handlers:
                if not handler_list:
                    logger.warning(f"{name} not available")
                    continue
                    
                for handler in handler_list:
                    if handler is not None:
                        # Check for duplicates
                        handler_id = id(handler)
                        if handler_id not in registered_handlers:
                            logger.debug(f"Registering {name} handler {type(handler).__name__} in group {group}")
                            if isinstance(handler, CommandHandler):
                                logger.debug(f"Command: {handler.commands}, Callback: {handler.callback.__name__}")
                            elif isinstance(handler, ConversationHandler):
                                logger.debug(f"Conversation Handler: {handler.name}")
                                logger.debug(f"Entry points: {[type(h).__name__ for h in handler.entry_points]}")
                                logger.debug(f"States: {list(handler.states.keys())}")
                            self.application.add_handler(handler, group=group)
                            registered_handlers.add(handler_id)
                            logger.info(f"Successfully registered {type(handler).__name__} in group {group}")
                        else:
                            logger.warning(f"Skipping duplicate handler in {name}")
                    else:
                        logger.warning(f"Null handler found in {name}")
            
            # Register error handler only if not already registered
            if not hasattr(self.application, '_error_handlers') or not self.application._error_handlers:
                self.application.add_error_handler(self.core_handlers.handle_error)
                logger.info("Registered error handler")
            
            logger.info(f"Successfully registered {len(registered_handlers)} unique handlers")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}", exc_info=True)
            raise
            
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