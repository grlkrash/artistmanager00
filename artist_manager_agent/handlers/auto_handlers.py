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
from .base_handler import BaseBotHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
AWAITING_FREQUENCY = "AWAITING_FREQUENCY"
AWAITING_AI_LEVEL = "AWAITING_AI_LEVEL"
AWAITING_NOTIFICATIONS = "AWAITING_NOTIFICATIONS"

class AutoHandlers(BaseBotHandler):
    """Auto mode handlers."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 7  # Set handler group
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
            CommandHandler("auto", self.show_menu),
            CallbackQueryHandler(self.handle_callback, pattern="^(menu_auto|auto_.*|auto_menu)$")
        ]

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle auto mode-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both auto_ and menu_auto patterns
            action = query.data.replace("menu_auto", "menu").replace("auto_", "").strip("_")
            logger.info(f"Auto mode handler processing callback: {query.data} -> {action}")
            
            if action == "menu" or action == "":
                await self.show_menu(update, context)
            elif action == "enable":
                await self._enable_auto_mode(update, context)
            elif action == "disable":
                await self._disable_auto_mode(update, context)
            elif action == "configure":
                await self._show_configure_options(update, context)
            elif action == "status":
                await self._show_status(update, context)
            else:
                logger.warning(f"Unknown auto mode action: {action}")
                await self.show_menu(update, context)
                
        except Exception as e:
            logger.error(f"Error in auto mode callback handler: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="auto_menu")
                ]])
            )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the auto mode menu."""
        keyboard = [
            [
                InlineKeyboardButton("Enable Auto Mode", callback_data="auto_enable"),
                InlineKeyboardButton("Disable Auto Mode", callback_data="auto_disable")
            ],
            [
                InlineKeyboardButton("Configure", callback_data="auto_configure"),
                InlineKeyboardButton("View Status", callback_data="auto_status")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            "⚙️ *Auto Mode Management*\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def _enable_auto_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Enable auto mode."""
        keyboard = [
            [
                InlineKeyboardButton("Configure", callback_data="auto_configure"),
                InlineKeyboardButton("View Status", callback_data="auto_status")
            ],
            [InlineKeyboardButton("« Back", callback_data="auto_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "Auto mode has been enabled! 🤖\n\n"
            "I will now:\n"
            "• Monitor your goals\n"
            "• Track deadlines\n"
            "• Suggest actions\n"
            "• Provide insights",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _disable_auto_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Disable auto mode."""
        keyboard = [[InlineKeyboardButton("« Back", callback_data="auto_menu")]]
        
        await self._send_or_edit_message(
            update,
            "Auto mode has been disabled.\n"
            "You can re-enable it at any time.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_configure_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show auto mode configuration options."""
        keyboard = [
            [
                InlineKeyboardButton("Check Frequency", callback_data="auto_config_freq"),
                InlineKeyboardButton("AI Level", callback_data="auto_config_ai")
            ],
            [
                InlineKeyboardButton("Notifications", callback_data="auto_config_notif"),
                InlineKeyboardButton("Task Limit", callback_data="auto_config_tasks")
            ],
            [InlineKeyboardButton("« Back", callback_data="auto_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "Configure auto mode settings:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
                [InlineKeyboardButton("Configure Settings", callback_data="auto_configure")],
                [InlineKeyboardButton("« Back", callback_data="auto_menu")]
            ]
            
            await self._send_or_edit_message(
                update,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing auto mode status: {str(e)}")
            await self._handle_error(update)

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

    async def handle_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle frequency input."""
        try:
            text = update.message.text.strip()
            if text.isdigit():
                hours = int(text)
                if 1 <= hours <= 24:
                    context.user_data["auto_settings"]["frequency"] = hours * 3600
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("Conservative", callback_data="auto_ai_conservative"),
                            InlineKeyboardButton("Balanced", callback_data="auto_ai_balanced"),
                            InlineKeyboardButton("Proactive", callback_data="auto_ai_proactive")
                        ]
                    ]
                    
                    await update.message.reply_text(
                        "Great! Now select the AI proactiveness level:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return AWAITING_AI_LEVEL
                    
            await update.message.reply_text(
                "Please enter a valid number of hours between 1 and 24:"
            )
            return AWAITING_FREQUENCY
            
        except Exception as e:
            logger.error(f"Error handling frequency: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your input. Please try again."
            )
            return ConversationHandler.END

    async def handle_ai_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle AI level selection."""
        try:
            level = update.message.text.lower()
            if level in ["conservative", "balanced", "proactive"]:
                context.user_data["auto_settings"]["ai_level"] = level
                
                keyboard = [
                    [
                        InlineKeyboardButton("All", callback_data="auto_notif_all"),
                        InlineKeyboardButton("Important Only", callback_data="auto_notif_important"),
                        InlineKeyboardButton("Minimal", callback_data="auto_notif_minimal")
                    ]
                ]
                
                await update.message.reply_text(
                    "Perfect! Finally, choose your notification preferences:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return AWAITING_NOTIFICATIONS
                
            await update.message.reply_text(
                "Please select one of: conservative, balanced, or proactive"
            )
            return AWAITING_AI_LEVEL
            
        except Exception as e:
            logger.error(f"Error handling AI level: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your input. Please try again."
            )
            return ConversationHandler.END

    async def handle_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle notification preferences."""
        try:
            level = update.message.text.lower()
            if level in ["all", "important", "minimal"]:
                context.user_data["auto_settings"]["notifications"] = level
                
                # Save settings
                settings = context.user_data["auto_settings"]
                
                keyboard = [
                    [
                        InlineKeyboardButton("Enable Auto Mode", callback_data="auto_enable"),
                        InlineKeyboardButton("View Settings", callback_data="auto_status")
                    ]
                ]
                
                await update.message.reply_text(
                    "✅ Auto mode configuration complete!\n\n"
                    f"• Check frequency: Every {settings['frequency']//3600}h\n"
                    f"• AI proactiveness: {settings['ai_level'].title()}\n"
                    f"• Notifications: {settings['notifications'].title()}\n\n"
                    "What would you like to do next?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return ConversationHandler.END
                
            await update.message.reply_text(
                "Please select one of: all, important, or minimal"
            )
            return AWAITING_NOTIFICATIONS
            
        except Exception as e:
            logger.error(f"Error handling notifications: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your input. Please try again."
            )
            return ConversationHandler.END 