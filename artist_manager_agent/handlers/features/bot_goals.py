"""Goals functionality for the Artist Manager Bot."""
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .utils.logger import logger

class GoalsMixin:
    """Mixin class to handle goal-related functionality."""
    
    def __init__(self):
        self.goals = {}
        
    async def goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /goals command - show current goals and progress."""
        try:
            # Get user profile
            user_id = update.effective_user.id
            profile = self.profiles.get(user_id)
            if not profile:
                await update.message.reply_text(
                    "Please set up your profile first using /me"
                )
                return

            # Get goals from task manager
            goals = await self.task_manager_integration.get_goals(user_id)
            
            if not goals:
                # Show empty state with option to create goals
                keyboard = [
                    [InlineKeyboardButton("Create New Goal", callback_data="goal_create")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "You don't have any goals set up yet.\nWould you like to create one?",
                    reply_markup=reply_markup
                )
                return

            # Format goals message with progress bars
            message = "🎯 Your Goals:\n\n"
            for goal in goals:
                progress = goal.get_progress()
                progress_bar = "▓" * int(progress/10) + "░" * (10 - int(progress/10))
                status = "✅" if progress == 100 else "🔄"
                
                message += f"{status} {goal.title}\n"
                message += f"[{progress_bar}] {progress}%\n"
                message += f"Due: {goal.due_date.strftime('%Y-%m-%d')}\n\n"

            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("Create New Goal", callback_data="goal_create"),
                    InlineKeyboardButton("Edit Goals", callback_data="goal_edit")
                ],
                [
                    InlineKeyboardButton("View Details", callback_data="goal_details"),
                    InlineKeyboardButton("Archive", callback_data="goal_archive")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                message,
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in goals command: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error fetching your goals. Please try again later."
            ) 