"""Core handlers for the Artist Manager Bot."""
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, BaseHandler
from .base_handler import BaseBotHandler
from artist_manager_agent.utils.logger import get_logger

logger = get_logger(__name__)

class CoreHandlers(BaseBotHandler):
    """Core command handlers."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 1  # Core handler group
        logger.info("Initialized CoreHandlers with group 1")

    def get_handlers(self) -> List[BaseHandler]:
        """Get core command handlers."""
        logger.info("Registering core handlers")
        handlers = [
            CommandHandler("help", self.show_help, block=False),
            CommandHandler("settings", self.show_settings, block=False),
            CommandHandler("menu", self.show_menu, block=False),
            CommandHandler("health", self.health_check, block=False),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message, block=False),
            CallbackQueryHandler(self.handle_callback, pattern="^core_(.*|settings_.*)$", block=False)
        ]
        logger.debug(f"Core handlers: {[type(h).__name__ for h in handlers]}")
        logger.info(f"Registered {len(handlers)} core handlers")
        return handlers

    async def health_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /health command."""
        try:
            # Check bot status
            status = {
                "bot_running": self.bot._running,
                "handlers_initialized": all(hasattr(self.bot, h) for h in [
                    'onboarding', 'core', 'home', 'goals', 'tasks', 'projects', 'music', 'team'
                ]),
                "persistence_available": hasattr(self.bot, 'persistence'),
                "application_running": hasattr(self.bot, 'application') and self.bot.application is not None
            }
            
            # Format status message
            message = "🤖 Bot Health Status:\n\n"
            for component, is_healthy in status.items():
                emoji = "✅" if is_healthy else "❌"
                message += f"{emoji} {component.replace('_', ' ').title()}\n"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}")
            await update.message.reply_text("Error checking bot health status.")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle core-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            action = query.data.replace("core_", "").replace("settings_", "")
            logger.info(f"Core handler processing callback: {query.data} -> {action}")
            
            if action == "menu":
                await self.show_menu(update, context)
            elif action == "manager_name":
                # Route to name change handler
                await self.bot.name_change.start_name_change(update, context)
            elif action == "notifications":
                keyboard = [
                    [
                        InlineKeyboardButton("All", callback_data="core_settings_notif_all"),
                        InlineKeyboardButton("Important Only", callback_data="core_settings_notif_important")
                    ],
                    [
                        InlineKeyboardButton("Minimal", callback_data="core_settings_notif_minimal"),
                        InlineKeyboardButton("None", callback_data="core_settings_notif_none")
                    ],
                    [InlineKeyboardButton("« Back to Settings", callback_data="core_settings")]
                ]
                await self._send_or_edit_message(
                    update,
                    "🔔 *Notification Settings*\n\n"
                    "Choose how often you want to receive notifications:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            elif action.startswith("notif_"):
                notif_level = action.replace("notif_", "")
                context.user_data["notification_level"] = notif_level
                await self._send_or_edit_message(
                    update,
                    f"✅ Notification level set to: {notif_level.title()}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back to Settings", callback_data="core_settings")
                    ]])
                )
            elif action == "privacy":
                keyboard = [
                    [
                        InlineKeyboardButton("Public Profile", callback_data="core_settings_privacy_public"),
                        InlineKeyboardButton("Private Profile", callback_data="core_settings_privacy_private")
                    ],
                    [InlineKeyboardButton("« Back to Settings", callback_data="core_settings")]
                ]
                await self._send_or_edit_message(
                    update,
                    "🔒 *Privacy Settings*\n\n"
                    "Choose your profile visibility:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            elif action == "language":
                keyboard = [
                    [
                        InlineKeyboardButton("English 🇬🇧", callback_data="core_settings_lang_en"),
                        InlineKeyboardButton("Español 🇪🇸", callback_data="core_settings_lang_es")
                    ],
                    [InlineKeyboardButton("« Back to Settings", callback_data="core_settings")]
                ]
                await self._send_or_edit_message(
                    update,
                    "🌐 *Language Settings*\n\n"
                    "Choose your preferred language:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            elif action == "theme":
                keyboard = [
                    [
                        InlineKeyboardButton("Light ☀️", callback_data="core_settings_theme_light"),
                        InlineKeyboardButton("Dark 🌙", callback_data="core_settings_theme_dark")
                    ],
                    [InlineKeyboardButton("« Back to Settings", callback_data="core_settings")]
                ]
                await self._send_or_edit_message(
                    update,
                    "🎨 *Theme Settings*\n\n"
                    "Choose your preferred theme:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                logger.warning(f"Unknown action in core handler: {action}")
                await self._send_or_edit_message(
                    update,
                    "Sorry, this feature is not available yet.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back to Settings", callback_data="core_settings")
                    ]])
                )
        except Exception as e:
            logger.error(f"Error in core callback handler: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Settings", callback_data="core_settings")
                ]])
            )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the main menu."""
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
        
        await self._send_or_edit_message(
            update,
            "🎵 *Welcome to Artist Manager Bot* 🎵\n\n"
            "What would you like to manage today?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show help message."""
        help_text = (
            "🤖 *Artist Manager Bot Help*\n\n"
            "Available commands:\n"
            "/help - Show this help message\n"
            "/menu - Show main menu\n"
            "/settings - Show bot settings\n"
            "/health - Check bot health status\n\n"
            "Main features:\n"
            "• Goals Management 🎯\n"
            "• Task Tracking 📝\n"
            "• Project Management 🚀\n"
            "• Music Distribution 🎵\n"
            "• Team Management 👥\n"
            "• Auto Mode ⚙️\n"
            "• Blockchain Integration ��\n\n"
            "Need more help? Use the menu buttons below:"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("Quick Start Guide", callback_data="core_guide"),
                InlineKeyboardButton("FAQ", callback_data="core_faq")
            ],
            [
                InlineKeyboardButton("Support", callback_data="core_support"),
                InlineKeyboardButton("Settings", callback_data="core_settings")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await update.message.reply_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show user profile."""
        user_id = str(update.effective_user.id)
        profile = self.bot.profiles.get(user_id)
        
        if not profile:
            keyboard = [[InlineKeyboardButton("Create Profile", callback_data="menu_profile_create")]]
            await self._send_or_edit_message(
                update,
                "You don't have a profile yet. Would you like to create one?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        keyboard = [
            [
                InlineKeyboardButton("Edit Profile", callback_data="menu_profile_edit"),
                InlineKeyboardButton("View Stats", callback_data="menu_profile_stats")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            f"👤 *{profile.name}*\n\n"
            f"Genre: {profile.genre}\n"
            f"Career Stage: {profile.career_stage}\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def show_profile_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show profile creation prompt."""
        keyboard = [[InlineKeyboardButton("Create Profile", callback_data="menu_profile_create")]]
        await self._send_or_edit_message(
            update,
            "You don't have a profile yet. Would you like to create one?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show settings menu."""
        keyboard = [
            [
                InlineKeyboardButton("Manager Name 👤", callback_data="core_settings_manager_name"),
                InlineKeyboardButton("Notifications 🔔", callback_data="core_settings_notifications")
            ],
            [
                InlineKeyboardButton("Privacy 🔒", callback_data="core_settings_privacy"),
                InlineKeyboardButton("Language 🌐", callback_data="core_settings_language")
            ],
            [
                InlineKeyboardButton("Theme 🎨", callback_data="core_settings_theme")
            ],
            [InlineKeyboardButton("« Back", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            "⚙️ *Settings*\n\n"
            "Configure your preferences:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        message = update.message.text
        
        # Ignore messages if a conversation is active
        if context.user_data.get("conversation_active"):
            return
            
        user_id = str(update.effective_user.id)
        profile = self.bot.profiles.get(user_id)
        
        if not profile:
            # New user - start onboarding
            await self.bot.onboarding.start_onboarding(update, context)
            return
            
        # For now, just show the main menu for any text message
        await self.show_menu(update, context)

    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        logger.error(f"Error handling update {update}: {context.error}")
        
        try:
            if update and update.effective_message:
                error_message = "Sorry, something went wrong. Please try again later."
                if isinstance(context.error, TimeoutError):
                    error_message = "Request timed out. Please try again."
                elif isinstance(context.error, error.NetworkError):
                    error_message = "Network error occurred. Please check your connection."
                elif isinstance(context.error, error.BadRequest):
                    error_message = "Invalid request. Please try again."
                elif isinstance(context.error, error.Unauthorized):
                    error_message = "Authentication failed. Please check your bot token."
                
                await update.effective_message.reply_text(
                    error_message,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back to Menu", callback_data="menu_main")
                    ]])
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        logger.info("Handling /start command")
        await self.bot.onboarding.start_onboarding(update, context) 