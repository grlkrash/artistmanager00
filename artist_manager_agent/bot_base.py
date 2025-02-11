"""Base bot class with core functionality."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, ClassVar
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
    BaseHandler
)
from .agent import ArtistManagerAgent
from .models import (
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
from .log import logger, log_event
from .auto_mode import AutoMode
from .project_manager import ProjectManager
from .task_manager_integration import TaskManagerIntegration
from .handlers import (
    GoalHandlers,
    TaskHandlers,
    BlockchainHandlers,
    MusicHandlers,
    OnboardingHandlers,
    ProjectHandlers,
    TeamHandlers,
    AutoHandlers
)
from .bot_goals import GoalsMixin
from .persistence import RobustPersistence
from .dashboard import Dashboard
from .team_manager import TeamManager
from .ai_handler import AIHandler
from .handlers.handler_registry import HandlerRegistry
from .handlers.base_handler import BaseHandlerMixin
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
from .config import (
    BOT_TOKEN, DB_URL, PERSISTENCE_PATH, LOG_LEVEL,
    DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS
)
import threading

class CoreHandlers(BaseHandlerMixin):
    """Core command handlers."""
    
    group = 0  # Core handler group for registration
    
    def __init__(self, bot):
        """Initialize core handlers."""
        self.bot = bot
        
    def get_handlers(self) -> List[BaseHandler]:
        """Get core command handlers."""
        return [
            CommandHandler("help", self.bot.help),
            CommandHandler("home", self.bot.show_menu),
            CommandHandler("me", self.bot.view_profile),
            CommandHandler("update", self.bot.edit_profile)
        ]

class ArtistManagerBot:
    """Base class for the Artist Manager bot."""
    
    _instance: ClassVar[Optional['ArtistManagerBot']] = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self, db_url=None):
        """Initialize the bot."""
        if self._initialized:
            return
            
        try:
            with self._lock:
                if not self._initialized:
                    self.db_url = db_url or DB_URL
                    self.agent = None
                    self.logger = logging.getLogger(__name__)
                    self.logger.setLevel(LOG_LEVEL)
                    self.application = None
                    self.persistence = None
                    self.handler_registry = None
                    self.task_manager = None
                    self.token = BOT_TOKEN
                    self.default_profile = None
                    self.profiles = {}
                    self.config = {
                        "persistence_path": PERSISTENCE_PATH,
                        "model": DEFAULT_MODEL,
                        "temperature": DEFAULT_TEMPERATURE,
                        "max_tokens": DEFAULT_MAX_TOKENS
                    }
                    self._init_components()
                    self._initialized = True
        except Exception as e:
            logger.error(f"Error initializing bot: {str(e)}")
            raise
    
    def _init_components(self):
        """Initialize bot components in the correct order."""
        try:
            # 1. Initialize persistence first
            logger.info("Initializing persistence...")
            persistence_path = Path(self.config["persistence_path"])
            persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.persistence = RobustPersistence(
                filepath=str(persistence_path.resolve()),
                backup_count=3,
                store_data=True,
                update_interval=60
            )
            
            # 2. Initialize application builder with persistence
            logger.info("Initializing application...")
            builder = (
                ApplicationBuilder()
                .token(self.token)
                .persistence(self.persistence)
                .concurrent_updates(True)
                .connection_pool_size(8)
                .connect_timeout(30.0)
                .pool_timeout(30.0)
                .read_timeout(30.0)
                .write_timeout(30.0)
            )
            
            self.application = builder.build()
            
            # 3. Initialize handler registry
            logger.info("Initializing handler registry...")
            self.handler_registry = HandlerRegistry()
            
            # 4. Initialize all other components
            logger.info("Initializing bot components...")
            self.team_manager = TeamManager(team_id="default")
            self.team_handlers = TeamHandlers(self)
            self.onboarding = OnboardingHandlers(self)
            self.dashboard = Dashboard(self)
            self.ai_handler = AIHandler(model=self.config["model"])
            self.auto_mode = AutoMode(self)
            self.auto_handlers = AutoHandlers(self)
            self.project_manager = ProjectManager(self)
            self.project_handlers = ProjectHandlers(self)
            self.task_manager_integration = TaskManagerIntegration(self.persistence)
            self.goal_handlers = GoalHandlers(self)
            self.task_handlers = TaskHandlers(self)
            self.blockchain_handlers = BlockchainHandlers(self)
            self.music_handlers = MusicHandlers(self)
            self.core_handlers = CoreHandlers(self)
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise
            
    async def _register_and_load(self):
        """Register handlers and load persistence data."""
        try:
            # 1. Load persistence data first
            logger.info("Loading persistence data...")
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
            await self.task_manager_integration.load_from_persistence()
            
            logger.info("All data loaded and handlers registered")
            
        except Exception as e:
            logger.error(f"Error during registration and loading: {str(e)}")
            raise
            
    def _register_handlers(self):
        """Register all handlers with the registry."""
        try:
            # Validate handler dependencies first
            logger.info("Validating handler dependencies...")
            handlers = [
                (0, self.core_handlers, "Core handlers"),
                (1, self.onboarding, "Onboarding handlers"),
                (2, self.goal_handlers, "Goal handlers"),
                (3, self.project_handlers, "Project handlers"),
                (4, self.blockchain_handlers, "Blockchain handlers"),
                (5, self.auto_handlers, "Auto mode handlers"),
                (6, self.team_handlers, "Team handlers"),
                (7, self.music_handlers, "Music handlers"),
                (8, self.task_handlers, "Task handlers")
            ]
            
            # Verify all handlers exist
            for group, handler, name in handlers:
                if not handler:
                    raise ValueError(f"{name} not initialized")
                
            # Register handlers in order
            logger.info("Registering handlers in order...")
            for group, handler, name in handlers:
                try:
                    logger.debug(f"Registering {name} (group {group})")
                    self.handler_registry.register_handler(group, handler)
                except Exception as e:
                    logger.error(f"Error registering {name}: {str(e)}")
                    raise
                
            # Register all handlers with the application
            logger.info("Registering handlers with application...")
            self.handler_registry.register_all(self.application)
            
            # Register core command handlers directly
            logger.info("Registering core command handlers...")
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CommandHandler("menu", self.show_menu))
            
            # Register global callback handler last
            logger.info("Registering global callback handler...")
            self.application.add_handler(
                CallbackQueryHandler(self.handle_callback),
                group=999  # Make this the last handler to process callbacks
            )
            
            logger.info("All handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise
            
    async def start(self):
        """Start the bot with proper initialization sequence."""
        try:
            # Check if already running
            if hasattr(self, '_running') and self._running:
                logger.warning("Bot is already running")
                return
                
            # 1. Register handlers and load data
            await self._register_and_load()
            
            # 2. Initialize application
            logger.info("Initializing application...")
            if not self.application._initialized:
                await self.application.initialize()
            
            # 3. Clean up only conversation states
            logger.info("Cleaning up old conversation states...")
            if hasattr(self.persistence, 'chat_data'):
                for chat_id in self.persistence.chat_data:
                    if 'conversation_state' in self.persistence.chat_data[chat_id]:
                        del self.persistence.chat_data[chat_id]['conversation_state']
            if hasattr(self.persistence, 'user_data'):
                for user_id in self.persistence.user_data:
                    if 'conversation_state' in self.persistence.user_data[user_id]:
                        del self.persistence.user_data[user_id]['conversation_state']
            await self.persistence._backup_data()
            
            # 4. Start application if not already started
            logger.info("Starting application...")
            if not self.application.running:
                await self.application.start()
            
            # 5. Start polling with clean state
            logger.info("Starting polling with clean state...")
            if hasattr(self.application, 'updater') and not self.application.updater.running:
                await self.application.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=["message", "callback_query", "inline_query"]
                )
            
            self._running = True
            logger.info("Bot started successfully")
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            # Try to clean up if possible
            try:
                if hasattr(self, 'application'):
                    if hasattr(self.application, 'updater') and self.application.updater.running:
                        await self.application.updater.stop()
                    if self.application.running:
                        await self.application.stop()
                        await self.application.shutdown()
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {str(cleanup_error)}")
            raise
            
    async def stop(self):
        """Stop the bot with proper cleanup sequence."""
        try:
            if not hasattr(self, '_running') or not self._running:
                logger.warning("Bot is not running")
                return
                
            logger.info("Stopping bot...")
            
            # 1. Stop polling first
            if hasattr(self.application, 'updater') and self.application.updater.running:
                logger.info("Stopping updater...")
                await self.application.updater.stop()
            
            # 2. Stop application
            if self.application.running:
                logger.info("Stopping application...")
                await self.application.stop()
            
            # 3. Final cleanup
            logger.info("Performing final cleanup...")
            await self.application.shutdown()
            if hasattr(self.persistence, '_backup_data'):
                await self.persistence._backup_data()
            
            self._running = False
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            # Set running to false even if cleanup fails
            self._running = False
            raise

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        
        try:
            # Try to answer the callback query first to prevent timeout
            try:
                await query.answer()
            except Exception as e:
                logger.warning(f"Could not answer callback query: {str(e)}")
            
            # Log the callback for debugging
            logger.info(f"Global callback handler received: {query.data}")
            
            if query.data.startswith("onboard_"):
                # Route to onboarding handlers
                logger.info("Routing to onboarding handlers")
                return await self.onboarding.handle_onboard_callback(update, context)
            elif query.data.startswith("goal_"):
                await self.goal_handlers.handle_goal_callback(update, context)
            elif query.data.startswith("auto_"):
                await self.auto_handlers.handle_auto_callback(update, context)
            elif query.data.startswith("profile_"):
                await self.handle_profile_callback(query)
            elif query.data.startswith("blockchain_"):
                await self.blockchain_handlers.handle_blockchain_callback(update, context)
            elif query.data.startswith("music_"):
                await self.music_handlers.handle_music_callback(update, context)
            elif query.data.startswith("dashboard_"):
                await self.dashboard.handle_dashboard_callback(update, context)
            elif query.data == "help":
                await self.help(update, context)
            else:
                # Log unknown callback data
                logger.warning(f"Unknown callback data: {query.data}")
                await query.message.reply_text(
                    "Sorry, I don't recognize that command. Please try again or use /help for available commands."
                )
                
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
            await query.message.reply_text(
                "Sorry, something went wrong. Please try again or use /help for available commands."
            )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show help message."""
        await update.message.reply_text(
            self.help_message,
            parse_mode="Markdown"
        )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show main menu."""
        keyboard = [
            [
                InlineKeyboardButton("Goals 🎯", callback_data="goal_menu"),
                InlineKeyboardButton("Tasks 📝", callback_data="task_menu")
            ],
            [
                InlineKeyboardButton("Projects 🚀", callback_data="project_menu"),
                InlineKeyboardButton("Music 🎵", callback_data="music_menu")
            ],
            [
                InlineKeyboardButton("Team 👥", callback_data="team_menu"),
                InlineKeyboardButton("Auto Mode ⚙️", callback_data="auto_menu")
            ],
            [
                InlineKeyboardButton("Blockchain 🔗", callback_data="blockchain_menu"),
                InlineKeyboardButton("Profile 👤", callback_data="profile_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🎵 *Welcome to Artist Manager Bot* 🎵\n\n"
            "What would you like to manage today?",
            reply_markup=reply_markup,
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