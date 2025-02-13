"""Home handlers for the Artist Manager Bot."""
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    BaseHandler
)
from ..core.base_handler import BaseBotHandler
from ...utils.logger import get_logger
from ...models import ArtistProfile

logger = get_logger(__name__)

class HomeHandlers(BaseBotHandler):
    """Handlers for home/main menu functionality."""
    
    def __init__(self, bot):
        """Initialize home handlers."""
        super().__init__(bot)
        self.group = 9  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get home menu handlers."""
        return [
            CommandHandler("home", self.show_menu),
            CallbackQueryHandler(self.handle_callback, pattern="^(home_menu|home_.*|menu_.*)$")
        ]

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle home-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both home_ and menu_ patterns
            action = query.data.replace("menu_", "").replace("home_", "").strip("_")
            logger.info(f"Home handler processing callback: {query.data} -> {action}")
            
            if action == "menu" or action == "":
                await self.show_menu(update, context)
            elif action == "goals":
                await self.bot.goal_handlers.show_menu(update, context)
            elif action == "tasks":
                await self.bot.task_handlers.show_menu(update, context)
            elif action == "projects":
                await self.bot.project_handlers.show_menu(update, context)
            elif action == "music":
                await self.bot.music_handlers.show_menu(update, context)
            elif action == "team":
                await self.bot.team_handlers.show_menu(update, context)
            elif action == "auto":
                await self.bot.auto_handlers.show_menu(update, context)
            elif action == "blockchain":
                await self.bot.blockchain_handlers.show_menu(update, context)
            elif action == "profile":
                await self._show_profile(update, context)
            else:
                logger.warning(f"Unknown home action: {action}")
                await self.show_menu(update, context)
                
        except Exception as e:
            logger.error(f"Error in home callback handler: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="home_menu")
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

    async def _show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            [InlineKeyboardButton("« Back to Menu", callback_data="home_menu")]
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

async def show_feature_unavailable(query, feature_name: str) -> None:
    """Show a consistent message for unavailable features."""
    await query.message.edit_text(
        f"The {feature_name} feature is coming soon! 🚀\n\n"
        "We're working hard to bring you this functionality.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Back to Dashboard", callback_data="back_to_dashboard")
        ]])
    )

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main dashboard for returning users."""
    logger.info("Showing dashboard for returning user")
    
    # Get user profile
    user_id = str(update.effective_user.id)
    profile = context.bot_data.get('profiles', {}).get(user_id)
    
    if not profile:
        # No profile found, redirect to start
        message = (
            "I don't see an existing profile for you. Let's create one!\n\n"
            "Use /start to begin the setup process."
        )
        if update.callback_query:
            await update.callback_query.message.edit_text(message)
        else:
            await update.message.reply_text(message)
        return
        
    # Format profile info for display
    name = context.bot_data.get('manager_name', 'Frankie Rhodes')
    
    # Create dashboard message
    dashboard_text = (
        f"👋 Welcome back! I'm {name}, your artist manager.\n\n"
        f"Artist: {profile.name}\n"
        f"Genre: {profile.genre}\n"
        f"Career Stage: {profile.career_stage}\n\n"
        "What would you like to work on today?"
    )
    
    # Create keyboard with main actions
    keyboard = [
        [
            InlineKeyboardButton("Goals 🎯", callback_data="goal_view"),
            InlineKeyboardButton("Tasks 📝", callback_data="task_view")
        ],
        [
            InlineKeyboardButton("Projects 🚀", callback_data="project_view"),
            InlineKeyboardButton("Music 🎵", callback_data="music_view")
        ],
        [
            InlineKeyboardButton("Team 👥", callback_data="team_view"),
            InlineKeyboardButton("Auto Mode ⚙️", callback_data="auto_view")
        ],
        [
            InlineKeyboardButton("Blockchain 🔗", callback_data="blockchain_view"),
            InlineKeyboardButton("Profile 👤", callback_data="profile_view")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(
                dashboard_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                dashboard_text,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error showing dashboard: {str(e)}")
        error_message = "Sorry, there was an error loading the dashboard. Please try again."
        if update.callback_query:
            await update.callback_query.message.edit_text(error_message)
        else:
            await update.message.reply_text(error_message) 