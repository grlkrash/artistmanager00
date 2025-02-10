"""Base bot class with core functionality."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ForceReply, Message
from telegram.ext import (
    Application,
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
    TeamHandlers
)
from .bot_goals import GoalsMixin
from .persistence import RobustPersistence
from .dashboard import Dashboard
from .team_manager import TeamManager
from .ai_handler import AIHandler
from .handlers.handler_registry import HandlerRegistry
from .auto_handlers import AutoHandlers
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

class ArtistManagerBotBase:
    """Base class for the Artist Manager Bot."""
    
    def __init__(
        self,
        telegram_token: str = None,
        artist_profile: ArtistProfile = None,
        openai_api_key: str = None,
        model: str = "gpt-3.5-turbo",
        db_url: str = "sqlite:///artist_manager.db"
    ):
        """Initialize the bot."""
        self.token = telegram_token
        self.default_profile = artist_profile
        self.profiles = {}
        self.db_url = db_url
        self.agent = None
        self.persistence = None
        self.help_message = ""
        self._auto_mode = False
        self._auto_task = None
        self._default_auto_settings = {
            "frequency": 3600,  # 1 hour
            "ai_level": "balanced",
            "notifications": "important",
            "task_limit": 5,
            "goal_check_interval": 86400,  # 24 hours
            "analytics_interval": 604800  # 7 days
        }
        
        # Initialize handler registry
        self.handler_registry = HandlerRegistry()
        
        # Initialize components
        self.team_manager = TeamManager(team_id="default")
        self.team_handlers = TeamHandlers(self)
        self.onboarding = OnboardingHandlers(self)
        self.dashboard = Dashboard(self)
        self.ai_handler = AIHandler(model=model)
        self.auto_mode = AutoMode(self)
        self.auto_handlers = AutoHandlers(self)
        self.project_manager = ProjectManager(self)
        self.project_handlers = ProjectHandlers(self)
        self.task_manager_integration = TaskManagerIntegration()
        self.goal_handlers = GoalHandlers(self)
        self.task_handlers = TaskHandlers(self)
        self.blockchain_handlers = BlockchainHandlers(self)
        self.music_handlers = MusicHandlers(self)
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register all handlers with the registry."""
        try:
            # Register handlers by group
            self.handler_registry.register_handler("onboarding", self.onboarding)
            self.handler_registry.register_handler("goals", self.goal_handlers)
            self.handler_registry.register_handler("tasks", self.task_handlers)
            self.handler_registry.register_handler("core", self)
            self.handler_registry.register_handler("projects", self.project_handlers)
            self.handler_registry.register_handler("team", self.team_handlers)
            self.handler_registry.register_handler("auto", self.auto_handlers)
            self.handler_registry.register_handler("blockchain", self.blockchain_handlers)
            self.handler_registry.register_handler("music", self.music_handlers)
            
            logger.info("All handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise
            
    def register_handlers(self, application: Application) -> None:
        """Register all handlers with the application."""
        try:
            self.handler_registry.register_all(application)
            logger.info("All handlers registered with application")
        except Exception as e:
            logger.error(f"Error registering handlers with application: {str(e)}")
            raise
            
    def get_handlers(self) -> List[BaseHandler]:
        """Get core command handlers."""
        return [
            CommandHandler("help", self.help),
            CommandHandler("home", self.show_menu),
            CommandHandler("me", self.view_profile),
            CommandHandler("update", self.edit_profile)
        ]
        
    async def run(self):
        """Start the bot."""
        try:
            # Create application
            application = Application.builder().token(self.token).build()
            
            # Register all handlers
            self.register_handlers(application)
            
            # Start the bot
            await application.run_polling()
            
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            raise

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        
        try:
            if query.data.startswith("goal_"):
                await self.goal_handlers.handle_goal_callback(update, context)
            elif query.data.startswith("auto_"):
                await self.handle_auto_callback(update, context)
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