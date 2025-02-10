"""Dashboard management for the Artist Manager Bot."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

class Dashboard:
    """Manages command organization and state."""
    
    def __init__(self, bot):
        self.bot = bot
        self.command_categories = {
            "profile": ["view", "edit"],
            "management": ["goals", "tasks", "events", "contracts"],
            "settings": ["auto", "help"],
            "projects": ["newproject"]
        }
        
    def get_dashboard_markup(self) -> InlineKeyboardMarkup:
        """Create dashboard markup with organized commands."""
        keyboard = []
        for category, commands in self.command_categories.items():
            row = []
            for cmd in commands:
                callback_data = f"{category}_{cmd}"
                button_text = cmd.capitalize()
                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            keyboard.append(row)
        return InlineKeyboardMarkup(keyboard)
        
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline buttons."""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Log callback data for debugging
            logger.info(f"Callback received from user {user_id}: {query.data}")
            
            # Ensure user has a profile
            if not context.user_data.get("profile_data"):
                await query.answer("Please complete your profile setup first with /start")
                return
                
            # Handle different button callbacks
            if query.data.startswith("goal_"):
                await self.bot.goal_handlers.handle_goal_callback(update, context)
            elif query.data.startswith("auto_"):
                await self.bot.handle_auto_callback(update, context)
            elif query.data.startswith("profile_"):
                await self.handle_profile_callback(query)
            else:
                logger.warning(f"Unknown callback data received: {query.data}")
                await query.answer("This feature is not implemented yet")
                
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
            await query.answer("Sorry, an error occurred. Please try again or use commands instead.")
            
    async def handle_profile_callback(self, query: CallbackQuery) -> None:
        """Handle profile-related button callbacks."""
        try:
            action = query.data.replace("profile_", "")
            if action == "view":
                await self.bot.view_profile(query.message, query.message.bot_data)
            elif action == "edit":
                # Show edit options with inline buttons
                keyboard = [
                    [
                        InlineKeyboardButton("Basic Info", callback_data="profile_edit_basic"),
                        InlineKeyboardButton("Goals", callback_data="profile_edit_goals")
                    ],
                    [
                        InlineKeyboardButton("Social Media", callback_data="profile_edit_social"),
                        InlineKeyboardButton("Streaming", callback_data="profile_edit_streaming")
                    ],
                    [
                        InlineKeyboardButton("« Back to Menu", callback_data="menu_main")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "What would you like to edit?\n\n"
                    "Choose a section to edit, or use /update for the full edit menu.",
                    reply_markup=reply_markup
                )
            elif action.startswith("edit_"):
                section = action.replace("edit_", "")
                await query.edit_message_text(
                    f"To edit your {section}, use:\n"
                    f"/update {section} <new value>\n\n"
                    "Example:\n"
                    f"/update {section} My new {section}"
                )
        except Exception as e:
            logger.error(f"Error in profile callback: {str(e)}")
            await query.answer("Error processing profile action") 