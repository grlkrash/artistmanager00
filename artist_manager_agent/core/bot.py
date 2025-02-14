"""Main bot implementation for the Artist Manager Bot."""
import os
import sys
import signal
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Set, Any, Tuple, Union, List
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    BaseHandler
)

# Fix imports to use parent package
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
from ..persistence import RobustPersistence
from ..utils.logger import get_logger

logger = get_logger(__name__)

class Bot:
    """Main bot class for the Artist Manager Bot."""
    
    _instances: Dict[str, 'Bot'] = {}
    _lock = asyncio.Lock()
    _main_loop: Optional[asyncio.AbstractEventLoop] = None
    _initialized_loop = False
    _task_groups: Dict[str, Set[asyncio.Task]] = {}
    _task_group_states: Dict[str, bool] = {}
    
    def __init__(self, token: str, data_dir: Path):
        """Initialize the bot."""
        try:
            if not token:
                raise ValueError("Bot token cannot be empty")
                
            # Set token and data directory
            self.token = token
            self.data_dir = data_dir
            self._running = False
            self._initialized = False
            
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
            
            # Initialize components
            self._init_components()
            
            # Initialize handlers
            self._init_handlers()
            
            # Register handlers
            self._register_handlers()
            
            self._initialized = True
            logger.info("Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing bot: {e}")
            raise

    def _init_components(self):
        """Initialize bot components."""
        try:
            # Initialize persistence
            persistence_path = self.data_dir / "persistence.pickle"
            persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.persistence = RobustPersistence(
                filepath=str(persistence_path.resolve())
            )
            
            # Initialize application
            logger.info("Initializing application...")
            builder = ApplicationBuilder()
            builder.token(self.token)
            builder.persistence(self.persistence)
            builder.concurrent_updates(True)
            
            # Build application and add error handler
            self.application = builder.build()
            self.application.add_error_handler(self._error_handler)
            
            # Initialize supporting components
            self._init_supporting_components()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
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
                    
            logger.info("All handlers initialized successfully")
            
        except Exception as e:
            logger.error(f"Error in _init_handlers: {e}")
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
        """Start the bot."""
        try:
            if self._running:
                logger.warning("Bot is already running")
                return
                
            # Load persisted state
            logger.info("Loading persisted state...")
            try:
                # Load persistence data
                await self.persistence.load()
                
                # Load bot data
                self.bot_data = await self.persistence.get_bot_data()
                
                # Initialize profiles if needed
                if 'profiles' not in self.bot_data:
                    self.bot_data['profiles'] = {}
                self.profiles = self.bot_data['profiles']
                
                logger.info(f"Loaded {len(self.profiles)} profiles from persistence")
            except Exception as e:
                logger.error(f"Error loading persisted state: {e}")
                # Continue with empty state if load fails
                self.bot_data = {}
                self.profiles = {}
                logger.info("Continuing with empty state")
            
            # Start application
            logger.info("Starting application...")
            await self.application.initialize()
            await self.application.start()
            
            # Set running flag before creating tasks
            self._running = True
            
            # Initialize task groups
            logger.info("Initializing task groups...")
            self._task_group_states["maintenance"] = True
            self._task_group_states["tasks"] = True
            self._task_group_states["analytics"] = True
            
            # Start background tasks
            logger.info("Starting background tasks...")
            try:
                await self.create_task(self._run_periodic_cleanup(), group="maintenance")
                await self.create_task(self._monitor_task_queue(), group="tasks")
                await self.create_task(self._update_analytics(), group="analytics")
            except Exception as e:
                logger.error(f"Error starting background tasks: {e}")
            
            # Start polling
            logger.info("Starting polling...")
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            logger.info("Bot started successfully")
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            self._running = False
            raise

    async def stop(self):
        """Stop the bot."""
        try:
            if not self._running:
                logger.warning("Bot is not running")
                return
                
            logger.info("Starting bot shutdown sequence...")
            
            # Stop accepting new updates first
            logger.info("Stopping polling...")
            if hasattr(self.application, 'updater') and self.application.updater:
                await self.application.updater.stop()
            
            # Cancel all tasks by group with proper cleanup
            logger.info("Stopping background tasks...")
            try:
                await self.cancel_tasks(timeout=10.0)  # Give tasks more time to cleanup
            except Exception as e:
                logger.error(f"Error cancelling tasks: {e}")
            
            # Save state before shutting down
            logger.info("Saving state...")
            try:
                await self.persistence.flush()
            except Exception as e:
                logger.error(f"Error saving state: {e}")
            
            # Stop application
            logger.info("Stopping application...")
            try:
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Error stopping application: {e}")
            
            # Clear state
            self._running = False
            self._task_groups.clear()
            self._task_group_states.clear()
            
            logger.info("Bot shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during bot shutdown: {str(e)}")
            self._running = False
            raise

    async def create_task(self, coro, group: str = "default") -> asyncio.Task:
        """Create a task in a specific group."""
        if not coro:
            raise ValueError("Coroutine cannot be None")
            
        if not self._running:
            logger.warning("Attempting to create task while bot is not running")
            if not self._task_group_states.get(group, False):
                logger.error(f"Task group {group} is stopped")
                return None
            
        task_group = self._task_groups.setdefault(group, set())
        
        try:
            # Create the task
            task = asyncio.create_task(self._wrap_task(coro, group))
            
            # Add to group and set up cleanup
            task_group.add(task)
            task.add_done_callback(lambda t: self._handle_task_done(t, group))
            
            logger.debug(f"Created task in group {group}: {task.get_name()}")
            return task
            
        except Exception as e:
            logger.error(f"Error creating task in group {group}: {e}")
            raise RuntimeError(f"Failed to create task in group {group}") from e

    def _handle_task_done(self, task: asyncio.Task, group: str) -> None:
        """Handle task completion and cleanup."""
        try:
            # Remove from group if still present
            if group in self._task_groups and task in self._task_groups[group]:
                self._task_groups[group].remove(task)
                logger.debug(f"Removed completed task from group {group}")
                
            if not task.cancelled():
                try:
                    exc = task.exception()
                    if exc:
                        logger.error(f"Task in group {group} failed with error: {exc}")
                except asyncio.CancelledError:
                    logger.debug(f"Task in group {group} was cancelled")
                except Exception as e:
                    logger.error(f"Error checking task exception in group {group}: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling task completion in group {group}: {e}")

    async def _wrap_task(self, coro, group: str):
        """Wrap a coroutine with proper error handling."""
        try:
            return await coro
        except asyncio.CancelledError:
            logger.info(f"Task in group {group} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in task group {group}: {e}", exc_info=True)
            raise

    async def cancel_tasks(self, group: str = None, timeout: float = 5.0) -> None:
        """Cancel tasks in a specific group or all tasks."""
        groups = [group] if group else list(self._task_groups.keys())
        
        for g in groups:
            if g in self._task_groups:
                logger.info(f"Cancelling tasks in group {g}")
                self._task_group_states[g] = False
                tasks = list(self._task_groups[g])
                
                if not tasks:
                    logger.debug(f"No tasks to cancel in group {g}")
                    continue
                
                # Cancel all tasks in the group
                for task in tasks:
                    if not task.done():
                        task.cancel()
                        logger.debug(f"Cancelled task {task.get_name()} in group {g}")
                
                try:
                    # Wait for tasks to complete with timeout
                    done, pending = await asyncio.wait(
                        tasks, 
                        timeout=timeout,
                        return_when=asyncio.ALL_COMPLETED
                    )
                    
                    # Handle any tasks that didn't complete in time
                    if pending:
                        logger.warning(f"{len(pending)} tasks in group {g} did not complete in time")
                        for task in pending:
                            if not task.done():
                                logger.warning(f"Force cancelling task {task.get_name()}")
                                task.cancel()
                                
                except Exception as e:
                    logger.error(f"Error waiting for tasks in group {g} to cancel: {e}")
                finally:
                    # Clear group regardless of errors
                    self._task_groups[g].clear()
                    logger.info(f"Cleared task group {g}")

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