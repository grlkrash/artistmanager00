"""Handler for home command and returning user functionality."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from ..utils.logger import get_logger
from ..models.artist_profile import ArtistProfile

logger = get_logger(__name__)

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main dashboard for returning users."""
    logger.info("Showing dashboard for returning user")
    
    # Get user profile
    user_id = str(update.effective_user.id)
    profile = context.bot_data.get('profiles', {}).get(user_id)
    
    if not profile:
        # No profile found, redirect to start
        await update.message.reply_text(
            "I don't see an existing profile for you. Let's create one!\n\n"
            "Use /start to begin the setup process."
        )
        return
        
    # Format profile info for display
    name = context.bot_data.get('manager_name', 'Kennedy Young')
    
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
            InlineKeyboardButton("📊 View Progress", callback_data="view_progress"),
            InlineKeyboardButton("🎯 Set New Goals", callback_data="set_goals")
        ],
        [
            InlineKeyboardButton("📝 Update Profile", callback_data="update_profile"),
            InlineKeyboardButton("📈 Analytics", callback_data="view_analytics")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        dashboard_text,
        reply_markup=reply_markup
    )

def get_home_handler() -> CommandHandler:
    """Create and return the home command handler."""
    return CommandHandler('home', show_dashboard) 