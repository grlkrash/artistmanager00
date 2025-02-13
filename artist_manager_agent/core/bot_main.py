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
from ..handlers.core.core_handlers import CoreHandlers
from ..handlers.features.goal_handlers import GoalHandlers
from ..handlers.features.task_handlers import TaskHandlers
from ..handlers.features.project_handlers import ProjectHandlers
from ..handlers.features.music_handlers import MusicHandlers
from ..handlers.features.blockchain_handlers import BlockchainHandlers
from ..handlers.features.auto_handlers import AutoHandlers
from ..handlers.features.team_handlers import TeamHandlers
from ..handlers.features.onboarding_handlers import OnboardingHandlers
from ..handlers.features.home_handler import HomeHandlers
from ..handlers.features.name_change_handler import NameChangeHandlers
from ..managers.team_manager import TeamManager
from ..managers.dashboard import Dashboard
from ..managers.project_manager import ProjectManager
from ..integrations.task_manager_integration import TaskManagerIntegration

from ..utils.logger import get_logger

logger = get_logger(__name__)

class ArtistManagerBot(BaseBot):
    """Main bot class that inherits from base bot."""
    
    def __init__(self, token: str, data_dir: Path):
        """Initialize the bot."""
        try:
            if not token:
                raise ValueError("Bot token cannot be empty")
                
            # Set token and data directory
            self.token = token
            self.data_dir = data_dir
            
            # Initialize handlers as None first
            self.onboarding = None
            self.core = None
            self.home = None
            self.name_change = None
            self.goals = None
            self.tasks = None
            self.projects = None
            self.music = None
            self.team = None
            self.auto = None
            self.blockchain = None
            
            # Initialize base class first
            super().__init__(db_url=str(data_dir / "bot.db"))
            
            # Initialize handlers
            self._init_handlers()
            
            # Register handlers
            self._register_handlers()
            
            logger.info("ArtistManagerBot initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing bot: {e}")
            raise

    def _init_handlers(self):
        """Initialize all handlers."""
        try:
            # Initialize handlers in order of priority
            handlers = [
                ('onboarding', OnboardingHandlers),
                ('core', CoreHandlers),
                ('home', HomeHandlers),
                ('name_change', NameChangeHandlers),
                ('goals', GoalHandlers),
                ('tasks', TaskHandlers),
                ('projects', ProjectHandlers),
                ('music', MusicHandlers),
                ('team', TeamHandlers),
                ('auto', AutoHandlers),
                ('blockchain', BlockchainHandlers)
            ]
            
            # Initialize each handler with proper error handling
            for attr_name, handler_class in handlers:
                try:
                    handler = handler_class(self)
                    if not hasattr(handler, 'get_handlers'):
                        raise AttributeError(f"{attr_name} handler missing get_handlers method")
                    setattr(self, attr_name, handler)
                    logger.debug(f"Initialized {attr_name} handler")
                except Exception as e:
                    logger.error(f"Error initializing {attr_name} handler: {e}")
                    raise RuntimeError(f"Failed to initialize {attr_name} handler") from e
                    
            # Initialize supporting components
            self._init_supporting_components()
            
            logger.info("All handlers initialized successfully")
            
        except Exception as e:
            logger.error(f"Error in _init_handlers: {e}")
            raise

    def _init_supporting_components(self):
        """Initialize supporting components."""
        try:
            # Initialize team manager
            self.team_manager = TeamManager(team_id="default")
            
            # Initialize dashboard
            self.dashboard = Dashboard(self)
            
            # Initialize project manager
            self.project_manager = ProjectManager(self)
            
            # Initialize task manager integration
            self.task_manager_integration = TaskManagerIntegration(self.persistence)
            
            logger.info("Supporting components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing supporting components: {e}")
            raise

    def _register_handlers(self):
        """Register handlers with the application."""
        try:
            # Verify all handlers are initialized
            required_handlers = [
                'onboarding', 'core', 'home', 'name_change', 'goals',
                'tasks', 'projects', 'music', 'team', 'auto', 'blockchain'
            ]
            
            for handler_name in required_handlers:
                if not hasattr(self, handler_name):
                    raise RuntimeError(f"Required handler {handler_name} is not initialized")
                if not getattr(self, handler_name):
                    raise RuntimeError(f"Handler {handler_name} is None")
                if not hasattr(getattr(self, handler_name), 'get_handlers'):
                    raise RuntimeError(f"Handler {handler_name} missing get_handlers method")
            
            # Clear existing handlers
            if hasattr(self.application, 'handlers'):
                self.application.handlers.clear()
                logger.info("Cleared existing handlers")
            
            # Add enhanced debug handler
            self.application.add_handler(
                MessageHandler(filters.COMMAND, self._debug_command),
                group=-1
            )
            logger.info("Added enhanced debug handler")
            
            # Register handlers in priority order
            handlers_to_register = [
                (0, self.onboarding.get_handlers(), "Onboarding handlers"),
                (1, self.core.get_handlers(), "Core handlers"),
                (2, self.home.get_handlers(), "Home handlers"),
                (3, self.name_change.get_handlers(), "Name change handlers"),
                (4, self.goals.get_handlers(), "Goal handlers"),
                (5, self.tasks.get_handlers(), "Task handlers"),
                (6, self.projects.get_handlers(), "Project handlers"),
                (7, self.music.get_handlers(), "Music handlers"),
                (8, self.team.get_handlers(), "Team handlers"),
                (9, self.auto.get_handlers(), "Auto mode handlers"),
                (10, self.blockchain.get_handlers(), "Blockchain handlers")
            ]
            
            # Track registered handlers to prevent duplicates
            registered = set()
            
            for group, handlers, description in handlers_to_register:
                if not handlers:
                    logger.warning(f"No {description} to register")
                    continue
                    
                if not isinstance(handlers, (list, tuple)):
                    handlers = [handlers]
                    
                for handler in handlers:
                    if handler is None:
                        logger.warning(f"Skipping None handler in {description}")
                        continue
                        
                    # Generate unique identifier for handler
                    handler_id = id(handler)
                    
                    if handler_id not in registered:
                        self.application.add_handler(handler, group=group)
                        registered.add(handler_id)
                        logger.debug(f"Registered {type(handler).__name__} in group {group}")
                    else:
                        logger.warning(f"Skipping duplicate handler {type(handler).__name__}")
                        
                logger.info(f"Registered {len(handlers)} {description}")
            
            # Add error handler
            self.application.add_error_handler(self._error_handler)
            logger.info("Added error handler")
            
            logger.info("All handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {e}")
            raise

    async def start(self):
        """Start the bot with proper initialization."""
        try:
            # Ensure we're not already running
            if self._running:
                logger.warning("Bot is already running")
                return
            
            # Start base class
            logger.info("Starting bot...")
            await super().start()
            
            # Initialize any additional components
            logger.info("Initializing additional components...")
            
            # Start background tasks in appropriate groups with error handling
            logger.info("Starting background tasks...")
            try:
                self.create_task(self._run_periodic_cleanup(), group="maintenance")
                logger.info("Started maintenance tasks")
            except Exception as e:
                logger.error(f"Failed to start maintenance tasks: {e}")
                
            try:
                self.create_task(self._monitor_task_queue(), group="tasks")
                logger.info("Started task monitoring")
            except Exception as e:
                logger.error(f"Failed to start task monitoring: {e}")
                
            try:
                self.create_task(self._update_analytics(), group="analytics")
                logger.info("Started analytics updates")
            except Exception as e:
                logger.error(f"Failed to start analytics updates: {e}")
            
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
            
            # Stop background tasks by group with timeouts
            logger.info("Stopping background tasks...")
            
            async def stop_group(group: str):
                try:
                    await asyncio.wait_for(self.cancel_tasks(group), timeout=5.0)
                    logger.info(f"Successfully stopped {group} tasks")
                except asyncio.TimeoutError:
                    logger.error(f"Timeout stopping {group} tasks")
                except Exception as e:
                    logger.error(f"Error stopping {group} tasks: {e}")
            
            # Stop tasks in parallel
            await asyncio.gather(
                stop_group("maintenance"),
                stop_group("tasks"),
                stop_group("analytics"),
                return_exceptions=True
            )
            
            # Stop base class last
            logger.info("Stopping bot...")
            await super().stop()
            
            self._running = False
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            self._running = False
            raise

    async def _run_periodic_cleanup(self):
        """Run periodic cleanup tasks."""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                logger.debug("Running periodic cleanup")
                # Add actual cleanup logic here
                await self._cleanup_old_data()
                await self._cleanup_temp_files()
            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _monitor_task_queue(self):
        """Monitor and process task queue."""
        while True:
            try:
                await asyncio.sleep(1)  # Check every second
                # Add actual task processing logic here
                await self._process_pending_tasks()
            except asyncio.CancelledError:
                logger.info("Task queue monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error monitoring task queue: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _update_analytics(self):
        """Update analytics data periodically."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                logger.debug("Updating analytics")
                # Add actual analytics update logic here
                await self._gather_analytics()
                await self._update_metrics()
            except asyncio.CancelledError:
                logger.info("Analytics update task cancelled")
                break
            except Exception as e:
                logger.error(f"Error updating analytics: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _cleanup_old_data(self):
        """Clean up old data."""
        # Implementation here
        pass

    async def _cleanup_temp_files(self):
        """Clean up temporary files."""
        # Implementation here
        pass

    async def _process_pending_tasks(self):
        """Process pending tasks."""
        # Implementation here
        pass

    async def _gather_analytics(self):
        """Gather analytics data."""
        # Implementation here
        pass

    async def _update_metrics(self):
        """Update metrics."""
        # Implementation here
        pass

    async def _debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Debug handler for logging command updates."""
        try:
            logger.debug("=== Debug Handler Start ===")
            logger.debug(f"Raw update: {update.to_dict()}")
            logger.debug(f"Update type: {type(update)}")
            
            if update.effective_message:
                logger.debug(f"Message type: {type(update.effective_message)}")
                logger.debug(f"Message content: {update.effective_message.to_dict()}")
                
                if update.effective_message.text:
                    logger.debug(f"Message text: {update.effective_message.text}")
                    if update.effective_message.text.startswith('/'):
                        command = update.effective_message.text.split()[0]
                        logger.debug(f"Command detected: {command}")
                        
            if context.user_data:
                logger.debug(f"User data: {context.user_data}")
            if context.chat_data:
                logger.debug(f"Chat data: {context.chat_data}")
                
            logger.debug("=== Debug Handler End ===")
            
        except Exception as e:
            logger.error(f"Error in debug handler: {e}")

    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Error handler for handling errors."""
        try:
            logger.error(f"Error in handler: {context.error}")
            await update.effective_message.reply_text("An error occurred. Please try again later.")
        except Exception as e:
            logger.error(f"Error in _error_handler: {e}")
            await update.effective_message.reply_text("An error occurred. Please try again later.") 