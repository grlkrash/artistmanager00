from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import os
from datetime import datetime, timedelta
import asyncio
from supabase import create_client, Client
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from .bot_commands import (
    BotCommandHandler,
    AWAITING_GOAL,
    AWAITING_GOAL_DEADLINE,
    AWAITING_TASK_TITLE,
    AWAITING_TASK_DESCRIPTION,
    AWAITING_TASK_ASSIGNEE,
    AWAITING_TASK_DEADLINE,
    AWAITING_TEAM_ROLE,
    AWAITING_TEAM_SKILLS,
    AWAITING_RELEASE_TITLE,
    AWAITING_RELEASE_DATE,
    AWAITING_RELEASE_TYPE,
    AWAITING_HEALTH_NOTE,
)

class ServiceIntegration(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

class SupabaseIntegration(ServiceIntegration):
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    async def initialize(self) -> None:
        # Test connection
        await self.client.auth.get_user()

    async def close(self) -> None:
        pass

    async def sync_artist_data(self, data: Dict[str, Any]) -> None:
        await self.client.table("artists").upsert(data).execute()

    async def sync_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        await self.client.table("tasks").upsert(tasks).execute()

class TelegramIntegration(ServiceIntegration):
    def __init__(self, token: str, agent: Any):
        self.token = token
        self.agent = agent
        self.application = Application.builder().token(token).build()
        self.command_handler = BotCommandHandler(agent)

    async def initialize(self) -> None:
        """Initialize bot with all command handlers."""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.command_handler.handle_start))
        self.application.add_handler(CommandHandler("help", self.command_handler.handle_help))
        
        # Career management
        self.application.add_handler(CommandHandler("strategy", self.command_handler.handle_strategy))
        self.application.add_handler(CommandHandler("progress", self._not_implemented))
        
        # Goals conversation handler
        goals_handler = ConversationHandler(
            entry_points=[CommandHandler("goals", self.command_handler.handle_goals)],
            states={
                AWAITING_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_goal_input)],
                AWAITING_GOAL_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_goal_deadline)]
            },
            fallbacks=[CommandHandler("cancel", self._cancel_conversation)]
        )
        self.application.add_handler(goals_handler)
        
        # Tasks conversation handler
        tasks_handler = ConversationHandler(
            entry_points=[CommandHandler("tasks", self.command_handler.handle_tasks)],
            states={
                AWAITING_TASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_task_title)],
                AWAITING_TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_task_description)],
                AWAITING_TASK_ASSIGNEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_task_assignee)],
                AWAITING_TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_task_deadline)]
            },
            fallbacks=[CommandHandler("cancel", self._cancel_conversation)]
        )
        self.application.add_handler(tasks_handler)
        
        # Team conversation handler
        team_handler = ConversationHandler(
            entry_points=[CommandHandler("team", self.command_handler.handle_team)],
            states={
                AWAITING_TEAM_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_team_role)],
                AWAITING_TEAM_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_team_skills)]
            },
            fallbacks=[CommandHandler("cancel", self._cancel_conversation)]
        )
        self.application.add_handler(team_handler)
        
        # Release conversation handler
        release_handler = ConversationHandler(
            entry_points=[CommandHandler("release", self.command_handler.handle_release)],
            states={
                AWAITING_RELEASE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_release_title)],
                AWAITING_RELEASE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_release_date)],
                AWAITING_RELEASE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_release_type)]
            },
            fallbacks=[CommandHandler("cancel", self._cancel_conversation)]
        )
        self.application.add_handler(release_handler)
        
        # Health conversation handler
        health_handler = ConversationHandler(
            entry_points=[CommandHandler("health", self.command_handler.handle_health)],
            states={
                AWAITING_HEALTH_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.command_handler.handle_health_note)]
            },
            fallbacks=[CommandHandler("cancel", self._cancel_conversation)]
        )
        self.application.add_handler(health_handler)
        
        # Other commands
        self.application.add_handler(CommandHandler("schedule", self.command_handler.handle_schedule))
        self.application.add_handler(CommandHandler("master", self.command_handler.handle_master))
        self.application.add_handler(CommandHandler("guidance", self.command_handler.handle_guidance))
        self.application.add_handler(CommandHandler("crisis", self.command_handler.handle_crisis))

        # Handle callback queries from inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.command_handler.handle_callback))

        # Handle regular messages
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_message
            )
        )

        await self.application.initialize()
        await self.application.start()
        await self.application.run_polling()

    async def _cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the current conversation."""
        await update.message.reply_text(
            "Operation cancelled. What else can I help you with?"
        )
        return ConversationHandler.END

    async def _handle_goal_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle goal input in conversation."""
        user_id = str(update.effective_user.id)
        state = self.command_handler._get_user_state(user_id)
        state["goal"] = update.message.text
        
        await update.message.reply_text(
            "When would you like to achieve this goal? (e.g., '3 months', '1 year')"
        )
        return AWAITING_GOAL_DEADLINE

    async def _handle_goal_deadline(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle goal deadline in conversation."""
        user_id = str(update.effective_user.id)
        state = self.command_handler._get_user_state(user_id)
        deadline = update.message.text
        
        self.agent.artist.goals.append(f"{state['goal']} (by {deadline})")
        self.command_handler._clear_user_state(user_id)
        
        await update.message.reply_text(
            f"Goal added: {state['goal']} (by {deadline})"
        )
        return ConversationHandler.END

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle non-command messages."""
        if not update.message or not update.message.text:
            return

        response = await self.agent.handle_telegram_message(
            update.message.text,
            str(update.message.from_user.id)
        )
        await update.message.reply_text(response)

    async def close(self) -> None:
        await self.application.stop()
        await self.application.shutdown()

class SpotifyIntegration(ServiceIntegration):
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        # Initialize Spotify client here

    async def initialize(self) -> None:
        # Initialize Spotify API client
        pass

    async def close(self) -> None:
        pass

    async def get_artist_stats(self, artist_id: str) -> Dict[str, Any]:
        # Get artist statistics from Spotify
        pass

class SocialMediaIntegration(ServiceIntegration):
    def __init__(self, credentials: Dict[str, Dict[str, str]]):
        self.credentials = credentials
        # Initialize social media clients here

    async def initialize(self) -> None:
        # Initialize social media API clients
        pass

    async def close(self) -> None:
        pass

    async def post_update(self, platform: str, content: Dict[str, Any]) -> bool:
        # Post updates to social media
        pass

class ServiceManager:
    def __init__(self):
        self.services: Dict[str, ServiceIntegration] = {}

    async def initialize_service(self, name: str, service: ServiceIntegration) -> None:
        await service.initialize()
        self.services[name] = service

    async def close_all(self) -> None:
        for service in self.services.values():
            await service.close()

    def get_service(self, name: str) -> Optional[ServiceIntegration]:
        return self.services.get(name) 