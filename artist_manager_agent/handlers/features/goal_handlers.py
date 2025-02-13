"""Goal management handlers for the Artist Manager Bot."""
from datetime import datetime
import uuid
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, ForceReply
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from ...models import Goal
from ..core.base_handler import BaseBotHandler
from ...utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
AWAITING_GOAL_TITLE = "AWAITING_GOAL_TITLE"
AWAITING_GOAL_DESCRIPTION = "AWAITING_GOAL_DESCRIPTION"
AWAITING_GOAL_PRIORITY = "AWAITING_GOAL_PRIORITY"
AWAITING_GOAL_DATE = "AWAITING_GOAL_DATE"

class GoalHandlers(BaseBotHandler):
    """Goal management handlers."""
    
    def __init__(self, bot):
        super().__init__(bot)

    async def start_goal_creation(self, message: Message, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start the goal creation process."""
        try:
            # Initialize goal creation state
            context.user_data["creating_goal"] = {
                "step": "title",
                "data": {}
            }
            
            await message.reply_text(
                "Let's create a new goal! 🎯\n\n"
                "First, what's the title of your goal?\n"
                "Example: 'Release new album' or 'Reach 1M streams'",
                reply_markup=ForceReply(selective=True)
            )
            
            return AWAITING_GOAL_TITLE
            
        except Exception as e:
            logger.error(f"Error starting goal creation: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error starting goal creation. Please try again later."
            )
            return ConversationHandler.END

    async def handle_goal_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle goal title input."""
        try:
            title = update.message.text
            context.user_data["creating_goal"]["data"]["title"] = title
            
            # Ask for description
            await update.message.reply_text(
                "Great! Now provide a description for your goal.\n"
                "This helps track progress and stay motivated.\n\n"
                "Example: 'Complete album recording and release on major platforms'",
                reply_markup=ForceReply(selective=True)
            )
            
            context.user_data["creating_goal"]["step"] = "description"
            return AWAITING_GOAL_DESCRIPTION
            
        except Exception as e:
            logger.error(f"Error handling goal title: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your input. Please try again."
            )
            return ConversationHandler.END

    async def handle_goal_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle goal description input."""
        try:
            description = update.message.text
            context.user_data["creating_goal"]["data"]["description"] = description
            
            # Ask for priority
            keyboard = [
                [
                    InlineKeyboardButton("🔴 High", callback_data="goal_priority_high"),
                    InlineKeyboardButton("🟡 Medium", callback_data="goal_priority_medium"),
                    InlineKeyboardButton("🟢 Low", callback_data="goal_priority_low")
                ]
            ]
            
            await update.message.reply_text(
                "What's the priority level for this goal?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data["creating_goal"]["step"] = "priority"
            return AWAITING_GOAL_PRIORITY
            
        except Exception as e:
            logger.error(f"Error handling goal description: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your input. Please try again."
            )
            return ConversationHandler.END

    async def handle_goal_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle goal priority selection."""
        try:
            query = update.callback_query
            await query.answer()
            
            priority = query.data.replace("goal_priority_", "")
            context.user_data["creating_goal"]["data"]["priority"] = priority
            
            # Ask for target date
            await query.message.reply_text(
                "When do you want to achieve this goal?\n"
                "Enter the target date in YYYY-MM-DD format.\n"
                "Example: 2024-12-31\n\n"
                "Or type 'skip' if you don't want to set a target date.",
                reply_markup=ForceReply(selective=True)
            )
            
            context.user_data["creating_goal"]["step"] = "target_date"
            return AWAITING_GOAL_DATE
            
        except Exception as e:
            logger.error(f"Error handling goal priority: {str(e)}")
            await update.effective_message.reply_text(
                "Sorry, there was an error processing your selection. Please try again."
            )
            return ConversationHandler.END

    async def handle_goal_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle goal target date input."""
        try:
            date_text = update.message.text
            
            if date_text.lower() != "skip":
                try:
                    target_date = datetime.strptime(date_text, "%Y-%m-%d")
                    context.user_data["creating_goal"]["data"]["target_date"] = target_date
                except ValueError:
                    await update.message.reply_text(
                        "Invalid date format. Please use YYYY-MM-DD format or type 'skip'.",
                        reply_markup=ForceReply(selective=True)
                    )
                    return AWAITING_GOAL_DATE
            
            # Create the goal
            goal_data = context.user_data["creating_goal"]["data"]
            goal_data["id"] = str(uuid.uuid4())
            goal_data["user_id"] = update.effective_user.id
            goal_data["status"] = "not_started"
            goal_data["progress"] = 0
            
            goal = Goal(**goal_data)
            await self.bot.task_manager_integration.create_goal(goal)
            
            # Clear creation state
            del context.user_data["creating_goal"]
            
            # Show success message with options
            keyboard = [
                [
                    InlineKeyboardButton("Add Tasks", callback_data=f"goal_add_task_{goal.id}"),
                    InlineKeyboardButton("View Goal", callback_data=f"goal_view_{goal.id}")
                ],
                [InlineKeyboardButton("Back to Goals", callback_data="goals")]
            ]
            
            await update.message.reply_text(
                "✅ Goal created successfully!\n\n"
                f"Title: {goal.title}\n"
                f"Priority: {goal.priority}\n"
                f"Target Date: {goal.target_date.strftime('%Y-%m-%d') if goal.target_date else 'Not set'}\n\n"
                "What would you like to do next?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error handling goal date: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error creating your goal. Please try again later."
            )
            return ConversationHandler.END

    async def cancel_goal_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel goal creation process."""
        if "creating_goal" in context.user_data:
            del context.user_data["creating_goal"]
            
        await update.message.reply_text(
            "Goal creation cancelled. Use /goals to manage your goals."
        )
        return ConversationHandler.END

    def get_conversation_handler(self):
        """Get the conversation handler for goal creation."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    self.start_goal_creation,
                    pattern="^goal_create$"
                )
            ],
            states={
                AWAITING_GOAL_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_goal_title)
                ],
                AWAITING_GOAL_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_goal_description)
                ],
                AWAITING_GOAL_PRIORITY: [
                    CallbackQueryHandler(self.handle_goal_priority, pattern="^goal_priority_")
                ],
                AWAITING_GOAL_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_goal_date)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_goal_creation)
            ],
            name="goal_creation",
            persistent=True
        )

    async def show_goal_analytics(self, message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show analytics for all goals."""
        try:
            analytics = await self.bot.task_manager_integration.get_goal_analytics()
            
            if not analytics:
                await message.reply_text("No goal data available for analysis.")
                return
                
            # Format analytics message
            message_text = (
                "📊 *Goal Analytics*\n\n"
                f"Total Goals: {analytics['total_goals']}\n"
                f"Completed: {analytics['completed_goals']}\n"
                f"In Progress: {analytics['in_progress_goals']}\n"
                f"Not Started: {analytics['not_started_goals']}\n\n"
                f"Average Progress: {analytics['average_goal_progress']}%\n\n"
                "*Goals by Priority:*\n"
                f"🔴 High: {analytics['goals_by_priority']['high']}\n"
                f"🟡 Medium: {analytics['goals_by_priority']['medium']}\n"
                f"🟢 Low: {analytics['goals_by_priority']['low']}\n\n"
                "*Task Statistics:*\n"
                f"Total Tasks: {analytics['total_tasks']}\n"
                f"Completed: {analytics['completed_tasks']}\n"
                f"Overdue: {analytics['overdue_tasks']}\n"
                f"Blocked: {analytics['blocked_tasks']}\n"
            )
            
            keyboard = [[InlineKeyboardButton("Back to Goals", callback_data="goals")]]
            
            await message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing goal analytics: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving goal analytics. Please try again later."
            )

    async def show_goal_details(self, message: Message, context: ContextTypes.DEFAULT_TYPE, goal_id: str) -> None:
        """Show detailed view of a specific goal."""
        try:
            goal = await self.bot.task_manager_integration.get_goal(goal_id)
            if not goal:
                await message.reply_text("Goal not found.")
                return
                
            # Get goal analytics
            analytics = await self.bot.task_manager_integration.analyze_goal_progress(goal_id)
            
            # Get associated tasks
            tasks = await self.bot.task_manager_integration.get_tasks_by_goal(goal_id)
            
            # Format progress bar
            progress_bar = "▓" * (goal.progress // 10) + "░" * (10 - goal.progress // 10)
            
            # Create detailed message
            message_text = (
                f"🎯 *{goal.title}*\n\n"
                f"Status: {goal.status}\n"
                f"Priority: {goal.priority}\n"
                f"Progress: [{progress_bar}] {goal.progress}%\n\n"
            )
            
            if goal.description:
                message_text += f"Description:\n{goal.description}\n\n"
                
            if goal.target_date:
                message_text += f"Target Date: {goal.target_date.strftime('%Y-%m-%d')}\n"
                
            if analytics['estimated_completion']:
                message_text += f"Est. Completion: {analytics['estimated_completion'].strftime('%Y-%m-%d')}\n"
                
            message_text += f"\nTasks ({analytics['completed_tasks']}/{analytics['total_tasks']}):\n"
            
            for task in tasks:
                status_emoji = "✅" if task.status == "completed" else "⏳"
                message_text += f"{status_emoji} {task.title}\n"
            
            # Create keyboard with actions
            keyboard = [
                [
                    InlineKeyboardButton("Add Task", callback_data=f"goal_add_task_{goal_id}"),
                    InlineKeyboardButton("Edit Goal", callback_data=f"goal_edit_{goal_id}")
                ],
                [
                    InlineKeyboardButton("Delete Goal", callback_data=f"goal_delete_{goal_id}"),
                    InlineKeyboardButton("Back to Goals", callback_data="goals")
                ]
            ]
            
            await message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing goal details: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving the goal details. Please try again later."
            ) 