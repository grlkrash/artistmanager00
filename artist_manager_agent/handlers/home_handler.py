"""Home handlers for the Artist Manager Bot."""
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    BaseHandler
)
from .base_handler import BaseBotHandler

from ..utils.logger import get_logger
from ..models import ArtistProfile

logger = get_logger(__name__)

class HomeHandlers(BaseBotHandler):
    """Handlers for home/main menu functionality."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 9  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get home-related handlers."""
        return [
            CommandHandler('start', self.start),
            CommandHandler('menu', self.show_menu),
            CallbackQueryHandler(self.show_menu, pattern="^menu_main$"),
            CallbackQueryHandler(self.handle_menu_callback, pattern="^(menu_.*|core_.*|feature_.*)$")
        ]

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start the bot and show welcome message."""
        # Get manager name from context or use default
        manager_name = context.bot_data.get('manager_name', 'Kennedy Young')
        
        # Welcome message
        welcome_text = (
            f"Hi! I'm {manager_name}, your AI Artist Manager. "
            "I'm here to help you manage your music career and creative projects.\n\n"
            "Here's what I can do for you:"
        )
        
        # Create menu keyboard
        keyboard = [
            [InlineKeyboardButton("🎯 Goals", callback_data="menu_goals")],
            [InlineKeyboardButton("📝 Tasks", callback_data="menu_tasks")],
            [InlineKeyboardButton("📂 Projects", callback_data="menu_projects")],
            [InlineKeyboardButton("🎵 Music", callback_data="menu_music")],
            [InlineKeyboardButton("⛓️ Blockchain", callback_data="menu_blockchain")],
            [InlineKeyboardButton("🤖 Auto", callback_data="menu_auto")],
            [InlineKeyboardButton("👥 Team", callback_data="menu_team")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")]
        ]
        
        await self._send_or_edit_message(
            update,
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the main menu."""
        # Get manager name from context or use default
        manager_name = context.bot_data.get('manager_name', 'Kennedy Young')
        
        # Menu message
        menu_text = f"Hi! I'm {manager_name}. What would you like to do?"
        
        # Create menu keyboard
        keyboard = [
            [InlineKeyboardButton("🎯 Goals", callback_data="menu_goals")],
            [InlineKeyboardButton("📝 Tasks", callback_data="menu_tasks")],
            [InlineKeyboardButton("📂 Projects", callback_data="menu_projects")],
            [InlineKeyboardButton("🎵 Music", callback_data="menu_music")],
            [InlineKeyboardButton("⛓️ Blockchain", callback_data="menu_blockchain")],
            [InlineKeyboardButton("🤖 Auto", callback_data="menu_auto")],
            [InlineKeyboardButton("👥 Team", callback_data="menu_team")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")]
        ]
        
        await self._send_or_edit_message(
            update,
            menu_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle menu callbacks by routing to appropriate handlers."""
        query = update.callback_query
        await query.answer()
        
        # Log the callback data for debugging
        logger.info(f"Menu callback received: {query.data}")
        
        # The actual handling of these callbacks is done by their respective handlers
        # This handler exists mainly for logging and debugging purposes
        pass

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