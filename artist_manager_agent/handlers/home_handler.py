"""Handler for home command and returning user functionality."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..utils.logger import get_logger
from ..models.artist_profile import ArtistProfile

logger = get_logger(__name__)

async def handle_dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks from dashboard buttons."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "view_progress":
        # Show progress view
        await query.message.edit_text(
            "📊 Here's your current progress:\n\n"
            "Goals in Progress: 0\n"
            "Completed Goals: 0\n"
            "Tasks Due Soon: 0",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="back_to_dashboard")
            ]])
        )
    elif action == "set_goals":
        # Redirect to goals interface
        await query.message.edit_text(
            "🎯 Let's work on your goals!\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Create New Goal", callback_data="goal_create")],
                [InlineKeyboardButton("View Current Goals", callback_data="goal_view")],
                [InlineKeyboardButton("« Back", callback_data="back_to_dashboard")]
            ])
        )
    elif action == "update_profile":
        # Show profile update options
        await query.message.edit_text(
            "📝 Update your profile:\n\n"
            "What would you like to update?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Basic Info", callback_data="profile_edit_basic"),
                    InlineKeyboardButton("Genre", callback_data="profile_edit_genre")
                ],
                [
                    InlineKeyboardButton("Career Stage", callback_data="profile_edit_stage"),
                    InlineKeyboardButton("Social Media", callback_data="profile_edit_social")
                ],
                [InlineKeyboardButton("« Back", callback_data="back_to_dashboard")]
            ])
        )
    elif action == "view_analytics":
        # Show analytics dashboard
        await query.message.edit_text(
            "📈 Analytics Dashboard\n\n"
            "Here's your current performance:\n"
            "• Social Growth: +0%\n"
            "• Streaming Growth: +0%\n"
            "• Goal Completion Rate: 0%",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="back_to_dashboard")
            ]])
        )
    elif action == "settings":
        # Show settings menu
        await query.message.edit_text(
            "⚙️ Settings\n\n"
            "What would you like to configure?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Notifications", callback_data="settings_notifications"),
                    InlineKeyboardButton("Privacy", callback_data="settings_privacy")
                ],
                [
                    InlineKeyboardButton("Preferences", callback_data="settings_preferences"),
                    InlineKeyboardButton("Integrations", callback_data="settings_integrations")
                ],
                [InlineKeyboardButton("« Back", callback_data="back_to_dashboard")]
            ])
        )
    elif action == "help":
        # Show help menu
        await query.message.edit_text(
            "❓ Help & Support\n\n"
            "Here are some resources to help you:\n\n"
            "• Use /start to begin setup\n"
            "• Use /help to see all commands\n"
            "• Use /home to return to dashboard",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="back_to_dashboard")
            ]])
        )
    elif action == "back_to_dashboard":
        # Return to main dashboard
        await show_dashboard(update, context)

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

def get_home_handlers() -> list:
    """Create and return the home command handlers."""
    return [
        CommandHandler('home', show_dashboard),
        CallbackQueryHandler(handle_dashboard_callback, pattern="^(view_progress|set_goals|update_profile|view_analytics|settings|help|back_to_dashboard)$")
    ] 