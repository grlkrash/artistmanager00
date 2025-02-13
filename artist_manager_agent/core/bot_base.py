"""Base bot class with core functionality."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, ClassVar, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ForceReply, Message
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    BaseHandler,
    PicklePersistence
)
from .agent import ArtistManagerAgent
from ..models import (
    ArtistProfile,
    Task,
    Event,
    Contract,
    FinancialRecord,
    PaymentRequest,
    PaymentMethod,
    PaymentStatus,
    Project,
    CollaboratorProfile,
    CollaboratorRole,
    Track,
    MasteringPreset,
    DistributionPlatform
)
from ..utils import logger, log_event
from ..services.auto_mode import AutoMode
from ..managers.project_manager import ProjectManager
from ..integrations.task_manager_integration import TaskManagerIntegration
from ..handlers.features import (
    GoalHandlers,
    TaskHandlers,
    BlockchainHandlers,
    MusicHandlers,
    OnboardingHandlers,
    ProjectHandlers,
    TeamHandlers,
    AutoHandlers
)
from ..handlers.features.bot_goals import GoalsMixin
from ..persistence import RobustPersistence
from ..managers.dashboard import Dashboard
from ..managers.team_manager import TeamManager
from ..services.ai_handler import AIHandler
from ..handlers.utils.handler_registry import HandlerRegistry
from ..handlers.core.base_handler import BaseBotHandler
from ..handlers.core.core_handlers import CoreHandlers
from ..handlers.features.onboarding_handlers import OnboardingHandlers
from ..handlers.features.home_handler import HomeHandlers
from ..handlers.features.name_change_handler import NameChangeHandlers
from ..utils.config import (
    BOT_TOKEN,
    DB_URL,
    PERSISTENCE_PATH,
    LOG_LEVEL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS
)
import uuid
import logging
import asyncio
from functools import partial
import psutil
import sys
import os
import json
import shutil
import pickle
from pathlib import Path
import threading

class BaseBot:
    """Base class for the Artist Manager bot."""
    
    _instances: ClassVar[Dict[str, 'BaseBot']] = {}
    _lock = threading.Lock()
    _main_loop: Optional[asyncio.AbstractEventLoop] = None
    _initialized_loop = False
    _task_groups: Dict[str, Set[asyncio.Task]] = {}
    _task_group_states: Dict[str, bool] = {}
    
    @classmethod
    def _ensure_loop(cls) -> asyncio.AbstractEventLoop:
        """Ensure event loop is initialized and return it."""
        if cls._main_loop is None or cls._main_loop.is_closed():
            try:
                # First try to get the running loop
                try:
                    cls._main_loop = asyncio.get_running_loop()
                except RuntimeError:
                    # If no loop is running, create a new one
                    cls._main_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(cls._main_loop)
                
                # Set up exception handler
                def handle_exception(loop, context):
                    exception = context.get('exception', context['message'])
                    logger.error(f"Caught event loop exception: {exception}")
                    if isinstance(exception, Exception):
                        logger.error(f"Exception traceback: {exception.__traceback__}")
                    
                cls._main_loop.set_exception_handler(handle_exception)
                cls._initialized_loop = True
                logger.info("Event loop initialized with exception handler")
            except Exception as e:
                logger.error(f"Error initializing event loop: {e}")
                raise
        return cls._main_loop
    
    def __new__(cls, *args, **kwargs):
        """Create a new instance or return existing one for the specific class."""
        with cls._lock:
            if cls.__name__ not in cls._instances:
                # Ensure loop exists before creating instance
                loop = cls._ensure_loop()
                if not loop.is_running():
                    try:
                        # Test the loop with a small task
                        async def test_loop():
                            await asyncio.sleep(0)
                        loop.run_until_complete(test_loop())
                    except Exception as e:
                        logger.error(f"Error testing event loop: {e}")
                        raise
                instance = super().__new__(cls)
                instance._initialized = False
                instance._running = False
                cls._instances[cls.__name__] = instance
            return cls._instances[cls.__name__]
    
    def __init__(self, db_url=None):
        """Initialize the bot."""
        with self._lock:
            if self._initialized:
                return
                
            try:
                self.db_url = db_url or DB_URL
                self.agent = None
                self.logger = logging.getLogger(__name__)
                self.logger.setLevel(LOG_LEVEL)
                
                # Initialize components in correct order
                self._init_components()
                
                self._initialized = True
                logger.info(f"{self.__class__.__name__} initialized successfully")
                
            except Exception as e:
                logger.error(f"Error initializing {self.__class__.__name__}: {str(e)}")
                raise
    
    def _init_components(self):
        """Initialize bot components in the correct order."""
        try:
            # 1. Initialize configuration
            self.config = {
                "persistence_path": PERSISTENCE_PATH,
                "model": DEFAULT_MODEL,
                "temperature": DEFAULT_TEMPERATURE,
                "max_tokens": DEFAULT_MAX_TOKENS
            }
            
            # 2. Initialize persistence structure (but don't load data yet)
            logger.info("Initializing persistence structure...")
            persistence_path = Path(self.config["persistence_path"])
            persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup of existing persistence file if it exists
            if persistence_path.exists():
                backup_path = persistence_path.with_suffix('.bak')
                shutil.copy2(persistence_path, backup_path)
                logger.info(f"Created backup of persistence file at {backup_path}")
            
            # Initialize persistence with correct parameters
            self.persistence = RobustPersistence(
                filepath=str(persistence_path.resolve()),
                store_data={
                    "user_data": True,
                    "chat_data": True,
                    "bot_data": True,
                    "callback_data": True
                },
                update_interval=30,
                backup_count=5
            )
            
            # 3. Initialize application with persistence and error handlers
            logger.info("Initializing application...")
            builder = Application.builder()
            builder.token(self.token or BOT_TOKEN)
            builder.persistence(self.persistence)
            builder.concurrent_updates(True)
            
            # Build application and add error handler
            self.application = builder.build()
            self.application.add_error_handler(self._error_handler)
            
            # 4. Initialize handler registry
            logger.info("Initializing handler registry...")
            self.handler_registry = HandlerRegistry()
            
            # 5. Initialize task groups
            self._task_groups = {}
            self._task_group_states = {}
            
            # 6. Initialize empty state (will be loaded lazily)
            logger.info("Initializing empty state...")
            self.bot_data = {}
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            self._cleanup_failed_init()
            raise
            
    def _cleanup_failed_init(self):
        """Clean up after failed initialization."""
        try:
            # Clean up persistence
            if hasattr(self, 'persistence') and self.persistence:
                try:
                    asyncio.run(self.persistence.flush())
                except Exception as e:
                    logger.error(f"Error flushing persistence during cleanup: {e}")
            
            # Clean up application
            if hasattr(self, 'application') and self.application:
                try:
                    asyncio.run(self.application.shutdown())
                except Exception as e:
                    logger.error(f"Error shutting down application during cleanup: {e}")
            
            # Clean up handler registry
            if hasattr(self, 'handler_registry') and self.handler_registry:
                try:
                    self.handler_registry.clear()
                except Exception as e:
                    logger.error(f"Error clearing handler registry during cleanup: {e}")
                    
        except Exception as e:
            logger.error(f"Error during failed initialization cleanup: {e}")

    def _init_supporting_components(self):
        """Initialize supporting components."""
        self.team_manager = TeamManager(team_id="default")
        self.dashboard = Dashboard(self)
        self.project_manager = ProjectManager(self)
        self.task_manager_integration = TaskManagerIntegration(self.persistence)

    async def start(self):
        """Start the bot with proper initialization."""
        try:
            if self._running:
                logger.warning("Bot is already running")
                return
            
            # Set running flag early to allow task creation
            self._running = True
            
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
                # Don't raise here, continue with bot startup
            
            # Start polling
            logger.info("Starting polling...")
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            logger.info("Bot started successfully")
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            self._running = False  # Reset running flag on error
            raise

    async def stop(self):
        """Stop the bot and cleanup."""
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
            self._running = False  # Ensure flag is cleared even on error
            raise

    @classmethod
    async def cleanup_loop(cls) -> None:
        """Clean up the event loop."""
        if cls._main_loop and not cls._main_loop.is_closed():
            try:
                # Cancel all remaining tasks
                tasks = [t for t in asyncio.all_tasks(cls._main_loop) 
                        if t is not asyncio.current_task() and not t.done()]
                
                if tasks:
                    # Log tasks being cancelled
                    logger.info(f"Cancelling {len(tasks)} remaining tasks")
                    
                    # Cancel all tasks
                    for task in tasks:
                        task.cancel()
                    
                    # Wait with timeout
                    try:
                        await asyncio.wait(tasks, timeout=5.0)
                        # Check for tasks that didn't complete
                        pending = [t for t in tasks if not t.done()]
                        if pending:
                            logger.warning(f"{len(pending)} tasks did not complete in time")
                    except Exception as e:
                        logger.error(f"Error waiting for tasks to cancel: {e}")
                
                # Clear task groups and states
                cls._task_groups.clear()
                cls._task_group_states.clear()
                
                # Shut down async generators
                try:
                    await cls._main_loop.shutdown_asyncgens()
                except Exception as e:
                    logger.error(f"Error shutting down async generators: {e}")
                
                # Stop and close the loop
                try:
                    if cls._main_loop.is_running():
                        cls._main_loop.stop()
                    await asyncio.sleep(0.1)  # Give pending callbacks a chance to complete
                    cls._main_loop.close()
                except Exception as e:
                    logger.error(f"Error closing event loop: {e}")
                
                # Reset class state
                cls._main_loop = None
                cls._initialized_loop = False
                
            except Exception as e:
                logger.error(f"Error cleaning up event loop: {e}")
                raise

    async def _cleanup(self) -> None:
        """Internal cleanup method."""
        try:
            # Stop the bot if running
            if self._running:
                logger.info("Stopping bot during cleanup...")
                await self.stop()
            
            # Additional cleanup steps
            logger.info("Running additional cleanup steps...")
            
            # Clean up persistence with proper error handling
            if hasattr(self, 'persistence') and self.persistence:
                try:
                    logger.info("Closing persistence...")
                    await self.persistence.close()
                except Exception as e:
                    logger.error(f"Error closing persistence: {e}")
            
            # Clean up application with proper error handling
            if hasattr(self, 'application') and self.application:
                try:
                    logger.info("Final application shutdown...")
                    await self.application.shutdown()
                except Exception as e:
                    logger.error(f"Error in final application shutdown: {e}")
            
            # Clean up event loop
            if self._main_loop and not self._main_loop.is_closed():
                logger.info("Cleaning up event loop...")
                await self.cleanup_loop()
                
            logger.info("Cleanup completed successfully")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
            raise

    def __del__(self):
        """Ensure cleanup on deletion with proper error handling."""
        if hasattr(self, '_main_loop') and self._main_loop and not self._main_loop.is_closed():
            try:
                # Create a new event loop if necessary
                if self._main_loop.is_closed():
                    self._main_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._main_loop)
                
                # Run cleanup
                self._main_loop.run_until_complete(self._cleanup())
            except Exception as e:
                logger.error(f"Error during cleanup in __del__: {str(e)}")
            finally:
                # Always try to close the loop
                if not self._main_loop.is_closed():
                    try:
                        self._main_loop.close()
                    except Exception as e:
                        logger.error(f"Error closing loop in __del__: {str(e)}")

    def _register_handlers(self):
        """Register handlers with the application."""
        # This is now a hook for child classes to implement
        pass

    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in updates."""
        try:
            error = context.error
            logger.error(f"Update {update} caused error {error}")
            
            if update and update.effective_message:
                error_message = "Sorry, something went wrong. Please try again."
                if isinstance(error, TimeoutError):
                    error_message = "Request timed out. Please try again."
                elif isinstance(error, NetworkError):
                    error_message = "Network error occurred. Please check your connection."
                
                await update.effective_message.reply_text(
                    error_message,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back to Menu", callback_data="menu_main")
                    ]])
                )
                
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")

    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle menu-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            action = query.data.replace("menu_", "")
            
            if action == "goals":
                await self.goal_handlers.show_menu(update, context)
            elif action == "tasks":
                await self.task_handlers.show_menu(update, context)
            elif action == "projects":
                await self.project_handlers.show_menu(update, context)
            elif action == "music":
                await self.music_handlers.show_menu(update, context)
            elif action == "team":
                await self.team_handlers.show_menu(update, context)
            elif action == "auto":
                await self.auto_handlers.show_menu(update, context)
            elif action == "blockchain":
                await self.blockchain_handlers.show_menu(update, context)
            elif action == "profile":
                await self.show_profile(update, context)
            elif action == "main":
                await self.show_menu(update, context)
            else:
                logger.warning(f"Unknown menu action: {action}")
                await self.show_menu(update, context)
                
        except Exception as e:
            logger.error(f"Error handling menu callback: {str(e)}")
            await query.message.reply_text(
                "Sorry, something went wrong. Please try again."
            )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show main menu."""
        keyboard = [
            [
                InlineKeyboardButton("Goals 🎯", callback_data="menu_goals"),
                InlineKeyboardButton("Tasks 📝", callback_data="menu_tasks")
            ],
            [
                InlineKeyboardButton("Projects 🚀", callback_data="menu_projects"),
                InlineKeyboardButton("Music 🎵", callback_data="menu_music")
            ],
            [
                InlineKeyboardButton("Team 👥", callback_data="menu_team"),
                InlineKeyboardButton("Auto Mode ⚙️", callback_data="menu_auto")
            ],
            [
                InlineKeyboardButton("Blockchain 🔗", callback_data="menu_blockchain"),
                InlineKeyboardButton("Profile 👤", callback_data="menu_profile")
            ]
        ]
        
        message = "�� *Welcome to Artist Manager Bot* 🎵\n\nWhat would you like to manage today?"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

    async def view_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """View artist profile."""
        profile = self.default_profile
        if not profile:
            await update.message.reply_text(
                "No profile found. Use /onboard to create one."
            )
            return

        profile_text = (
            f"👤 *Artist Profile*\n\n"
            f"*Name:* {profile.name}\n"
            f"*Genre:* {profile.genre or 'Not specified'}\n"
            f"*Career Stage:* {profile.career_stage}\n\n"
            f"*Goals:*\n" + "\n".join([f"- {goal}" for goal in profile.goals]) + "\n\n"
            f"*Strengths:*\n" + "\n".join([f"- {strength}" for strength in profile.strengths]) + "\n\n"
            f"*Areas for Improvement:*\n" + "\n".join([f"- {area}" for area in profile.areas_for_improvement]) + "\n\n"
            f"*Achievements:*\n" + "\n".join([f"- {achievement}" for achievement in profile.achievements])
        )

        keyboard = [
            [InlineKeyboardButton("Edit Profile", callback_data="profile_edit")],
            [InlineKeyboardButton("Back to Menu", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            profile_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def edit_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start profile editing process."""
        keyboard = [
            [
                InlineKeyboardButton("Name", callback_data="profile_edit_name"),
                InlineKeyboardButton("Genre", callback_data="profile_edit_genre")
            ],
            [
                InlineKeyboardButton("Career Stage", callback_data="profile_edit_stage"),
                InlineKeyboardButton("Goals", callback_data="profile_edit_goals")
            ],
            [
                InlineKeyboardButton("Strengths", callback_data="profile_edit_strengths"),
                InlineKeyboardButton("Areas for Improvement", callback_data="profile_edit_improvements")
            ],
            [
                InlineKeyboardButton("Achievements", callback_data="profile_edit_achievements"),
                InlineKeyboardButton("Social Media", callback_data="profile_edit_social")
            ],
            [InlineKeyboardButton("Back to Profile", callback_data="profile_view")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "What would you like to edit?",
            reply_markup=reply_markup
        )

    async def handle_profile_callback(self, query: CallbackQuery) -> None:
        """Handle profile-related callbacks."""
        try:
            action = query.data.replace("profile_", "")
            
            if action == "view":
                await self.view_profile(query.message, query.message.bot_data)
            elif action == "edit":
                await self.edit_profile(query.message, query.message.bot_data)
            elif action.startswith("edit_"):
                section = action.replace("edit_", "")
                await query.message.reply_text(
                    f"To edit your {section}, use:\n"
                    f"/update {section} <new value>\n\n"
                    "Example:\n"
                    f"/update {section} My new {section}"
                )
            else:
                await query.message.reply_text("This feature is not implemented yet.")
                
        except Exception as e:
            logger.error(f"Error in profile callback: {str(e)}")
            await query.message.reply_text("Error processing profile action")

    async def start_polling(self):
        """Start polling with clean state."""
        self.logger.info("Starting polling with clean state...")
        try:
            await self.application.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "inline_query"]
            )
        except Exception as e:
            self.logger.error(f"Error starting polling: {e}")
            raise 

    async def _register_and_load(self):
        """Register handlers and load persistence data."""
        try:
            # 1. Load persistence data first
            logger.info("Loading persistence data...")
            if hasattr(self.persistence, 'load'):
                await self.persistence.load()
            
            # Load profiles from persistence
            if hasattr(self.persistence, 'bot_data'):
                logger.info("Checking for profiles in persistence...")
                if 'profiles' in self.persistence.bot_data:
                    self.profiles = self.persistence.bot_data['profiles']
                    logger.info(f"Loaded {len(self.profiles)} profiles from persistence")
                    logger.debug(f"Profile IDs in memory: {list(self.profiles.keys())}")
                else:
                    logger.info("No profiles found in persistence, initializing empty profiles")
                    self.persistence.bot_data['profiles'] = self.profiles
            else:
                logger.warning("Persistence has no bot_data attribute")
                
            # 2. Register handlers in correct order
            logger.info("Registering handlers...")
            self._register_handlers()
            
            # 3. Load task manager data
            logger.info("Loading task manager data...")
            if hasattr(self, 'task_manager_integration'):
                await self.task_manager_integration.load_from_persistence()
            
            logger.info("All data loaded and handlers registered")
            
        except Exception as e:
            logger.error(f"Error during registration and loading: {str(e)}")
            raise 

    async def _load_persistence(self):
        """Load data from persistence."""
        try:
            if hasattr(self, 'persistence') and self.persistence:
                self.bot_data = await self.persistence.get_bot_data()
                logger.info("Loaded persisted data successfully")
        except Exception as e:
            logger.error(f"Error loading persistence: {e}")
            raise 

    @classmethod
    def get_task_group(cls, group: str) -> Set[asyncio.Task]:
        """Get or create a task group."""
        if group not in cls._task_groups:
            cls._task_groups[group] = set()
            cls._task_group_states[group] = True
        return cls._task_groups[group]

    async def create_task(self, coro, group: str = "default") -> asyncio.Task:
        """Create a task in a specific group for better management."""
        if not coro:
            raise ValueError("Coroutine cannot be None")
            
        if not self._main_loop:
            try:
                self._main_loop = self._ensure_loop()
            except Exception as e:
                logger.error(f"Failed to ensure event loop: {e}")
                raise RuntimeError("No event loop available") from e
                
        if not self._running:
            logger.warning("Attempting to create task while bot is not running")
            if not self._task_group_states.get(group, False):
                raise RuntimeError(f"Task group {group} is stopped")
            
        task_group = self.get_task_group(group)
        
        try:
            # Create the task
            task = self._main_loop.create_task(self._wrap_task(coro, group))
            
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
                        logger.error(f"Task traceback: {task.get_stack()}")
                except asyncio.CancelledError:
                    logger.debug(f"Task in group {group} was cancelled")
                except Exception as e:
                    logger.error(f"Error checking task exception in group {group}: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling task completion in group {group}: {e}")

    async def _wrap_task(self, coro, group: str):
        """Wrap a coroutine with proper error handling and cleanup."""
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