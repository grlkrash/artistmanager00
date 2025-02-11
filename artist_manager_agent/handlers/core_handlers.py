"""Core handlers for the Artist Manager Bot."""
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, BaseHandler
from .base_handler import BaseBotHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CoreHandlers(BaseBotHandler):
    """Core command handlers."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 1  # Core handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get core command handlers."""
        return [
            CommandHandler("help", self.show_help),
            CommandHandler("settings", self.show_settings),
            CallbackQueryHandler(self.handle_core_callback, pattern="^core_(.*|settings_.*)$")
        ]

    async def handle_core_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle core-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both core_ and menu_ patterns
            original_data = query.data
            action = query.data.replace("core_", "").replace("menu_", "")
            logger.info(f"Core handler processing callback: {original_data} -> {action}")
            
            if action == "menu" or action == "main":
                logger.info("Showing main menu")
                await self.show_menu(update, context)
            elif action == "goals":
                logger.info("Routing to goals menu")
                await self.bot.goal_handlers.show_menu(update, context)
            elif action == "tasks":
                logger.info("Routing to tasks menu")
                await self.bot.task_handlers.show_menu(update, context)
            elif action == "projects":
                logger.info("Routing to projects menu")
                await self.bot.project_handlers.show_menu(update, context)
            elif action == "music":
                logger.info("Routing to music menu")
                await self.bot.music_handlers.show_menu(update, context)
            elif action == "team":
                logger.info("Routing to team menu")
                await self.bot.team_handlers.show_menu(update, context)
            elif action == "auto":
                logger.info("Routing to auto mode menu")
                await self.bot.auto_handlers.show_menu(update, context)
            elif action == "blockchain":
                logger.info("Routing to blockchain menu")
                await self.bot.blockchain_handlers.show_menu(update, context)
            elif action == "profile" or action == "profile_create":
                logger.info("Routing to profile")
                if action == "profile_create":
                    await self.bot.onboarding.start_onboarding(update, context)
                else:
                    await self.show_profile(update, context)
            elif action == "help":
                logger.info("Showing help")
                await self.show_help(update, context)
            else:
                logger.warning(f"Unknown action in core handler: {action}")
                await self._send_or_edit_message(
                    update,
                    "Sorry, this feature is not available yet.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back to Menu", callback_data="menu_main")
                    ]])
                )
        except Exception as e:
            logger.error(f"Error in core callback handler: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Menu", callback_data="menu_main")
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
        keyboard = [
            [
                InlineKeyboardButton("Commands", callback_data="core_commands"),
                InlineKeyboardButton("FAQ", callback_data="core_faq")
            ],
            [
                InlineKeyboardButton("Tutorial", callback_data="core_tutorial"),
                InlineKeyboardButton("Support", callback_data="core_support")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            "🤖 *Help & Support*\n\n"
            "What can I help you with?",
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