"""Base bot class with core functionality."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
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

class ArtistManagerBotBase:
    """Base class for the Artist Manager Bot."""
    
    def __init__(
        self,
        telegram_token: str = None,
        artist_profile: ArtistProfile = None,
        openai_api_key: str = None,
        model: str = "gpt-3.5-turbo",
        db_url: str = "sqlite:///artist_manager.db",
        persistence_path: str = "bot_data.pickle"
    ):
        """Initialize the bot."""
        self.token = telegram_token
        self.default_profile = artist_profile
        self.profiles = {}
        self.db_url = db_url
        self.agent = None
        
        # Store configuration
        self.config = {
            "model": model,
            "persistence_path": persistence_path
        }
        
        # Initialize components (but don't start them yet)
        self._init_components()
        
    def _init_components(self):
        """Initialize bot components in the correct order."""
        try:
            # 1. Initialize persistence first
            logger.info("Initializing persistence...")
            self.persistence = RobustPersistence(
                filepath=str(Path(self.config["persistence_path"]).resolve()),
                backup_count=3
            )
            
            # 2. Initialize application builder with persistence
            logger.info("Initializing application...")
            self.application = (
                ApplicationBuilder()
                .token(self.token)
                .persistence(self.persistence)
                .build()
            )
            
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
            # Register handlers by group
            self.handler_registry.register_handler(0, self.core_handlers)  # Core handlers
            self.handler_registry.register_handler(1, self.goal_handlers)  # Goal handlers
            self.handler_registry.register_handler(2, self.project_handlers)  # Project handlers
            self.handler_registry.register_handler(3, self.blockchain_handlers)  # Blockchain handlers
            self.handler_registry.register_handler(4, self.onboarding)  # Onboarding handlers
            self.handler_registry.register_handler(5, self.auto_handlers)  # Auto mode handlers
            self.handler_registry.register_handler(6, self.team_handlers)  # Team handlers
            self.handler_registry.register_handler(7, self.music_handlers)  # Music handlers
            self.handler_registry.register_handler(8, self.task_handlers)  # Task handlers
            
            # Register all handlers with the application
            self.handler_registry.register_all(self.application)
            
            logger.info("All handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise
            
    async def start(self):
        """Start the bot with proper initialization sequence."""
        try:
            # 1. Register handlers and load data
            await self._register_and_load()
            
            # 2. Initialize application
            logger.info("Initializing application...")
            await self.application.initialize()
            
            # 3. Start application
            logger.info("Starting application...")
            await self.application.start()
            
            # 4. Start polling
            logger.info("Starting polling...")
            await self.application.updater.start_polling()
            
            logger.info("Bot started successfully")
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            raise
            
    async def stop(self):
        """Stop the bot with proper cleanup."""
        try:
            # 1. Stop polling first
            logger.info("Stopping polling...")
            await self.application.updater.stop()
            
            # 2. Save persistence data
            logger.info("Saving persistence data...")
            await self.persistence.flush()
            
            # 3. Save task manager data
            logger.info("Saving task manager data...")
            await self.task_manager_integration.save_to_persistence()
            
            # 4. Stop application
            logger.info("Stopping application...")
            await self.application.stop()
            
            # 5. Final cleanup
            logger.info("Performing final cleanup...")
            await self.application.shutdown()
            self.handler_registry.clear()
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            raise

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        
        try:
            if query.data.startswith("goal_"):
                await self.goal_handlers.handle_goal_callback(update, context)
            elif query.data.startswith("auto_"):
                await self.auto_handlers.handle_auto_callback(update, context)
            elif query.data.startswith("profile_"):
                await self.handle_profile_callback(query)
            elif query.data.startswith("blockchain_"):
                await self.blockchain_handlers.handle_blockchain_callback(update, context)
            elif query.data.startswith("music_"):
                await self.music_handlers.handle_music_callback(update, context)
            elif query.data == "start_onboarding":
                await self.onboarding.start_onboarding(update, context)
            else:
                await query.answer("Unknown callback")
                
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
            await query.answer("Error processing request")

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