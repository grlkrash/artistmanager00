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
    BaseHandler,
    PicklePersistence
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
from .utils.config import (
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
    
    _instance: ClassVar[Optional['BaseBot']] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
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
                self.application = None
                self.persistence = None
                self.handler_registry = None
                self.task_manager = None
                self.token = None  # Will be set by child class
                self.default_profile = None
                self.config = {
                    "persistence_path": PERSISTENCE_PATH,
                    "model": DEFAULT_MODEL,
                    "temperature": DEFAULT_TEMPERATURE,
                    "max_tokens": DEFAULT_MAX_TOKENS
                }
                
                # Initialize components
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
            
            store_data = {
                "user_data": True,
                "chat_data": True,
                "bot_data": True,
                "callback_data": True
            }
            
            self.persistence = RobustPersistence(
                filepath=str(persistence_path.resolve()),
                store_data=store_data,
                update_interval=30,
                backup_count=5
            )
            
            # 2. Load existing state before initializing components
            self.bot_data = {}  # Initialize empty first
            
            # 3. Initialize application with persistence
            logger.info("Initializing application...")
            builder = Application.builder()
            builder.token(self.token or BOT_TOKEN)
            builder.persistence(self.persistence)
            builder.concurrent_updates(True)
            self.application = builder.build()
            
            # 4. Initialize handler registry
            logger.info("Initializing handler registry...")
            self.handler_registry = HandlerRegistry()
            
            # 5. Initialize supporting components
            logger.info("Initializing supporting components...")
            self._init_supporting_components()
            
            logger.info("Core components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise

    def _init_supporting_components(self):
        """Initialize supporting components."""
        self.team_manager = TeamManager(team_id="default")
        self.dashboard = Dashboard(self)
        self.project_manager = ProjectManager(self)
        self.task_manager_integration = TaskManagerIntegration(self.persistence)

    async def _cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'application'):
                # Stop all running tasks
                tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                for task in tasks:
                    task.cancel()
                
                # Wait for tasks to complete
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Stop application
                await self.application.stop()
                await self.application.shutdown()
                
            if hasattr(self, 'persistence'):
                await self.persistence.close()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise

    def __del__(self):
        """Ensure cleanup on deletion."""
        if hasattr(self, '_event_loop') and self._event_loop and not self._event_loop.is_closed():
            try:
                self._event_loop.run_until_complete(self._cleanup())
            except Exception as e:
                logger.error(f"Error during cleanup in __del__: {str(e)}")

    def _register_handlers(self):
        """Register handlers with the application."""
        # This is now a hook for child classes to implement
        pass

    async def start(self):
        """Start the bot."""
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

    async def stop(self):
        """Stop the bot."""
        try:
            await self._cleanup()
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
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