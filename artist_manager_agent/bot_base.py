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
from .utils import logger, log_event
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
from .handlers.base_handler import BaseBotHandler
from .handlers.core_handlers import CoreHandlers
from .handlers.onboarding_handlers import OnboardingHandlers
from .handlers.home_handler import HomeHandlers
from .handlers.name_change_handler import NameChangeHandlers
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

class CoreHandlers(BaseBotHandler):
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

class BaseBot:
    """Base class for the Artist Manager bot."""
    
    _instance: ClassVar[Optional['BaseBot']] = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self, db_url=None):
        """Initialize the bot."""
        self._initialized = False
        self.profiles = {}
        self.db_url = db_url
        
        # Initialize handlers as None
        self.onboarding = None
        self.core_handlers = None
        self.goal_handlers = None
        self.task_handlers = None
        self.project_handlers = None
        self.music_handlers = None
        self.blockchain_handlers = None
        self.auto_handlers = None
        self.team_handlers = None
        self.home_handlers = None
        self.name_change_handlers = None
        
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
            # 1. Initialize persistence first with proper state tracking
            logger.info("Initializing persistence...")
            persistence_path = Path(self.config["persistence_path"])
            persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.persistence = RobustPersistence(
                filepath=str(persistence_path.resolve()),
                backup_count=5,  # Increased from 3
                store_data=True,
                update_interval=30,  # Decreased from 60
                store_callback_data=True,
                store_user_data=True,
                store_chat_data=True,
                store_bot_data=True
            )
            
            # 2. Load existing state before initializing components
            if hasattr(self.persistence, 'get_bot_data'):
                self.bot_data = self.persistence.get_bot_data()
            else:
                self.bot_data = {}
            
            # 3. Initialize application with persistence
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
                .arbitrary_callback_data(True)  # Enable arbitrary callback data
            )
            
            self.application = builder.build()
            
            # 4. Initialize handler registry
            logger.info("Initializing handler registry...")
            self.handler_registry = HandlerRegistry()
            
            # 5. Initialize all handlers in correct order
            logger.info("Initializing bot handlers...")
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
            
            # 6. Initialize supporting components
            logger.info("Initializing supporting components...")
            self.team_manager = TeamManager(team_id="default")
            self.dashboard = Dashboard(self)
            self.project_manager = ProjectManager(self)
            self.task_manager_integration = TaskManagerIntegration(self.persistence)
            
            # 7. Register all handlers
            logger.info("Registering handlers...")
            self._register_handlers()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise
            
    def _register_handlers(self):
        """Register all handlers with the registry."""
        try:
            # Clear any existing handlers
            if hasattr(self.application, 'handlers'):
                self.application.handlers.clear()
                logger.info("Cleared existing handlers")
            
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
            
            # Register each handler group
            for group, handler_list, name in handlers:
                if not handler_list:
                    logger.warning(f"{name} not available")
                    continue
                    
                for handler in handler_list:
                    if handler is not None:
                        logger.info(f"Registering {name} in group {group}")
                        self.application.add_handler(handler, group=group)
                    else:
                        logger.warning(f"Null handler found in {name}")
            
            # Register error handler last
            self.application.add_error_handler(self._error_handler)
            logger.info("All handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise

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
        
        message = "🎵 *Welcome to Artist Manager Bot* 🎵\n\nWhat would you like to manage today?"
        
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