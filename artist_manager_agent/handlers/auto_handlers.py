"""Auto mode handlers for the Artist Manager Bot."""
from datetime import datetime
import uuid
import logging
import asyncio
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, ForceReply
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    BaseHandler
)
from ..models import ArtistProfile, Task
from .base_handler import BaseHandlerMixin

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_FREQUENCY = "AWAITING_FREQUENCY"
AWAITING_AI_LEVEL = "AWAITING_AI_LEVEL"
AWAITING_NOTIFICATIONS = "AWAITING_NOTIFICATIONS"

class AutoHandlers(BaseHandlerMixin):
    """Auto mode handlers."""
    
    group = "auto"  # Handler group for registration
    
    def __init__(self, bot):
        self.bot = bot
        self._auto_mode = False
        self._auto_task = None
        self._default_settings = {
            "frequency": 3600,  # 1 hour
            "ai_level": "balanced",
            "notifications": "important",
            "task_limit": 5,
            "goal_check_interval": 86400,  # 24 hours
            "analytics_interval": 604800  # 7 days
        }

    def get_handlers(self) -> List[BaseHandler]:
        """Get auto mode-related handlers."""
        return [
            CommandHandler("auto", self.show_options),
            CommandHandler("autosetup", self.setup),
            self.get_conversation_handler(),
            CallbackQueryHandler(self.handle_auto_callback, pattern="^auto_")
        ]

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for auto mode configuration."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.setup, pattern="^auto_settings$"),
                CommandHandler("autosetup", self.setup)
            ],
            states={
                AWAITING_FREQUENCY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_frequency)
                ],
                AWAITING_AI_LEVEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_ai_level)
                ],
                AWAITING_NOTIFICATIONS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_notifications)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_auto_setup)
            ],
            name="auto_setup",
            persistent=True
        )

    async def show_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show auto mode options."""
        try:
            user_id = update.effective_user.id
            profile = self.bot.profiles.get(user_id)
            
            if not profile:
                await update.message.reply_text(
                    "Please complete your profile setup first using /me"
                )
                return

            keyboard = [
                [
                    InlineKeyboardButton("Enable Auto Mode", callback_data="auto_enable"),
                    InlineKeyboardButton("Disable Auto Mode", callback_data="auto_disable")
                ],
                [
                    InlineKeyboardButton("Configure Settings", callback_data="auto_settings"),
                    InlineKeyboardButton("View Status", callback_data="auto_status")
                ]
            ]
            
            await update.message.reply_text(
                "🤖 Auto Mode Settings\n\n"
                "Auto mode uses AI to help manage your career:\n"
                "• Automated task scheduling\n"
                "• Smart goal tracking\n"
                "• Proactive suggestions\n"
                "• Performance analytics\n\n"
                "What would you like to do?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
                
        except Exception as e:
            logger.error(f"Error showing auto mode options: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error loading auto mode options. Please try again."
            )

    async def setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Configure auto mode settings."""
        try:
            settings = context.user_data.get("auto_settings", self._default_settings)
            
            keyboard = [
                [
                    InlineKeyboardButton("Every 1h", callback_data="auto_freq_1"),
                    InlineKeyboardButton("Every 3h", callback_data="auto_freq_3"),
                    InlineKeyboardButton("Every 6h", callback_data="auto_freq_6")
                ],
                [
                    InlineKeyboardButton("Conservative AI", callback_data="auto_ai_conservative"),
                    InlineKeyboardButton("Balanced AI", callback_data="auto_ai_balanced"),
                    InlineKeyboardButton("Proactive AI", callback_data="auto_ai_proactive")
                ],
                [
                    InlineKeyboardButton("All Notifications", callback_data="auto_notif_all"),
                    InlineKeyboardButton("Important Only", callback_data="auto_notif_important"),
                    InlineKeyboardButton("Minimal", callback_data="auto_notif_minimal")
                ],
                [InlineKeyboardButton("« Back", callback_data="auto_back")]
            ]
            
            await update.message.reply_text(
                "⚙️ Auto Mode Configuration\n\n"
                "Current settings:\n"
                f"• Check frequency: Every {settings['frequency']//3600}h\n"
                f"• AI proactiveness: {settings['ai_level'].title()}\n"
                f"• Notification level: {settings['notifications'].title()}\n\n"
                "Select new settings:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_FREQUENCY
            
        except Exception as e:
            logger.error(f"Error starting auto mode setup: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting setup. Please try again."
            )
            return ConversationHandler.END

    async def handle_auto_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle auto mode-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("auto_", "")
        
        if action == "enable":
            # Save current settings or use defaults
            if "auto_settings" not in context.user_data:
                context.user_data["auto_settings"] = self._default_settings.copy()
            
            self._auto_mode = True
            
            # Start background task if not running
            if not self._auto_task or self._auto_task.done():
                self._auto_task = asyncio.create_task(
                    self._process_tasks(update, context)
                )
            
            await query.edit_message_text(
                "🤖 Auto Mode Enabled\n\n"
                "I will now:\n"
                "• Monitor your goals and suggest tasks\n"
                "• Track project deadlines\n"
                "• Analyze performance metrics\n"
                "• Provide AI-powered insights\n\n"
                "Use /auto to change settings or disable"
            )
            
        elif action == "disable":
            self._auto_mode = False
            if self._auto_task:
                self._auto_task.cancel()
            
            await query.edit_message_text(
                "Auto mode has been disabled. Use /auto to re-enable."
            )
            
        elif action == "settings":
            await self.setup(update, context)
            
        elif action.startswith("freq_"):
            hours = int(action.split("_")[1])
            context.user_data["auto_settings"]["frequency"] = hours * 3600
            await self.show_options(update, context)
            
        elif action.startswith("ai_"):
            level = action.split("_")[1]
            context.user_data["auto_settings"]["ai_level"] = level
            await self.show_options(update, context)
            
        elif action.startswith("notif_"):
            level = action.split("_")[1]
            context.user_data["auto_settings"]["notifications"] = level
            await self.show_options(update, context)
            
        elif action == "status":
            await self._show_status(update, context)
            
        elif action == "back":
            await self.show_options(update, context)

    async def _show_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current auto mode status."""
        try:
            settings = context.user_data.get("auto_settings", self._default_settings)
            
            status = "🟢 Enabled" if self._auto_mode else "🔴 Disabled"
            last_check = getattr(self, "_last_check", None)
            last_check_str = last_check.strftime("%Y-%m-%d %H:%M:%S") if last_check else "Never"
            
            message = (
                f"🤖 Auto Mode Status: {status}\n\n"
                "Current settings:\n"
                f"• Check frequency: Every {settings['frequency']//3600}h\n"
                f"• AI proactiveness: {settings['ai_level'].title()}\n"
                f"• Notification level: {settings['notifications'].title()}\n"
                f"• Task limit: {settings['task_limit']}\n"
                f"• Goal check interval: {settings['goal_check_interval']//3600}h\n"
                f"• Analytics interval: {settings['analytics_interval']//86400} days\n\n"
                f"Last check: {last_check_str}"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("Enable" if not self._auto_mode else "Disable",
                                       callback_data="auto_enable" if not self._auto_mode else "auto_disable")
                ],
                [InlineKeyboardButton("Configure Settings", callback_data="auto_settings")],
                [InlineKeyboardButton("« Back", callback_data="auto_back")]
            ]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing auto mode status: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error loading the status. Please try again."
            )

    async def _process_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Background task for auto mode processing."""
        user_id = update.effective_user.id
        
        while self._auto_mode:
            try:
                # Get user profile and settings
                profile = self.bot.profiles.get(user_id)
                settings = context.user_data.get("auto_settings", self._default_settings)
                
                if profile:
                    # Process goals and create tasks
                    await self._process_goals(update, context, profile)
                    
                    # Check project deadlines
                    await self._check_deadlines(update, context)
                    
                    # Analyze performance metrics
                    await self._analyze_metrics(update, context, profile)
                    
                    # Generate insights and suggestions
                    await self._generate_insights(update, context, profile)
                    
                    # Update last check time
                    self._last_check = datetime.now()
                
                # Wait before next check based on settings
                freq = settings.get("frequency", self._default_settings["frequency"])
                await asyncio.sleep(freq)
                
            except Exception as e:
                logger.error(f"Error in auto mode processing: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def cancel_auto_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel auto mode setup."""
        context.user_data.clear()
        await update.message.reply_text(
            "Auto mode setup cancelled. You can start over with /autosetup"
        )
        return ConversationHandler.END 