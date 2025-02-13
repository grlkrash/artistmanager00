"""Dashboard functionality for the Artist Manager Bot."""
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from ..models import ArtistProfile
from ..utils.logger import get_logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes

logger = get_logger(__name__)

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
            elif query.data.startswith("project_"):
                await self.bot.project_handlers.handle_project_callback(update, context)
            elif query.data.startswith("task_"):
                await self.bot.task_handlers.handle_task_callback(update, context)
            elif query.data.startswith("team_"):
                await self.bot.team_handlers.handle_team_callback(update, context)
            elif query.data.startswith("auto_"):
                await self.bot.auto_handlers.handle_auto_callback(update, context)
            elif query.data.startswith("blockchain_"):
                await self.bot.blockchain_handlers.handle_blockchain_callback(update, context)
            elif query.data.startswith("music_"):
                await self.bot.music_handlers.handle_music_callback(update, context)
            elif query.data.startswith("profile_"):
                await self.handle_profile_callback(query)
            elif query.data.startswith("dashboard_"):
                await self._handle_dashboard_action(update, context, query.data)
            elif query.data.startswith("menu_"):
                await self._handle_menu_action(update, context, query.data)
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

    def get_quick_action_buttons(self, profile: ArtistProfile) -> List[List[InlineKeyboardButton]]:
        """Get quick action buttons based on profile."""
        buttons = []
        
        # Core actions
        buttons.append([
            InlineKeyboardButton("Create Goal", callback_data="goal_create"),
            InlineKeyboardButton("New Project", callback_data="project_create")
        ])
        
        # Music actions
        buttons.append([
            InlineKeyboardButton("Release Music", callback_data="music_release"),
            InlineKeyboardButton("Team", callback_data="team_view")
        ])
        
        # Analytics and settings
        buttons.append([
            InlineKeyboardButton("Analytics", callback_data="auto_analytics"),
            InlineKeyboardButton("Settings", callback_data="profile_settings")
        ])
        
        return buttons

    def get_navigation_buttons(self) -> List[List[InlineKeyboardButton]]:
        """Get navigation buttons."""
        return [
            [InlineKeyboardButton("Back to Menu", callback_data="dashboard_back")],
            [InlineKeyboardButton("Help", callback_data="onboard_help")]
        ] 