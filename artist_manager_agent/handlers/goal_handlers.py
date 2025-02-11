"""Goal management handlers for the Artist Manager Bot."""
from datetime import datetime
import uuid
import logging
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    BaseHandler
)
from ..models import Goal
from .base_handler import BaseBotHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
AWAITING_GOAL_TITLE = "AWAITING_GOAL_TITLE"
AWAITING_GOAL_DESCRIPTION = "AWAITING_GOAL_DESCRIPTION"
AWAITING_GOAL_PRIORITY = "AWAITING_GOAL_PRIORITY"
AWAITING_GOAL_DATE = "AWAITING_GOAL_DATE"

class GoalHandlers(BaseBotHandler):
    """Handlers for goal-related functionality."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 2  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get goal-related handlers."""
        return [
            CommandHandler("goals", self.show_menu),
            CallbackQueryHandler(self.handle_callback, pattern="^(menu_goals|goal_.*|goal_menu)$"),
            self.get_conversation_handler()
        ]

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle goal-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            action = query.data.replace("menu_goals", "").replace("goal_", "").strip("_")
            
            if action == "menu" or action == "":
                await self.show_menu(update, context)
            elif action == "create":
                await self.start_goal_creation(update, context)
            elif action == "list":
                await self.list_goals(update, context)
            elif action == "complete":
                await self.mark_goal_complete(update, context)
            else:
                logger.warning(f"Unknown goal action: {action}")
                await self.show_menu(update, context)
            
        except Exception as e:
            logger.error(f"Error handling goal callback: {str(e)}")
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="menu_goals")
                ]])
            )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the goals menu."""
        keyboard = [
            [
                InlineKeyboardButton("Create Goal", callback_data="goal_add"),
                InlineKeyboardButton("View Goals", callback_data="goal_view_all")
            ],
            [
                InlineKeyboardButton("Goal Analytics", callback_data="goal_analytics"),
                InlineKeyboardButton("Archive Goals", callback_data="goal_archive")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            "🎯 *Goals Management*\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def _show_add_goal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show goal creation interface."""
        keyboard = [
            [
                InlineKeyboardButton("Quick Goal", callback_data="goal_quick"),
                InlineKeyboardButton("Detailed Goal", callback_data="goal_detailed")
            ],
            [InlineKeyboardButton("« Back", callback_data="goal_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "How would you like to create your goal?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_all_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all user goals."""
        # Get user's goals
        user_id = update.effective_user.id
        goals = await self.bot.task_manager_integration.get_goals(user_id)
        
        if not goals:
            keyboard = [
                [InlineKeyboardButton("Create Goal", callback_data="goal_add")],
                [InlineKeyboardButton("« Back", callback_data="goal_menu")]
            ]
            await self._send_or_edit_message(
                update,
                "You don't have any goals yet. Would you like to create one?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        # Format goals message
        message = "🎯 Your Goals:\n\n"
        keyboard = []
        
        for goal in goals:
            progress = goal.get_progress()
            status = "✅" if progress == 100 else "🔄"
            message += f"{status} {goal.title}\n"
            message += f"Progress: {progress}%\n"
            if goal.due_date:
                message += f"Due: {goal.due_date.strftime('%Y-%m-%d')}\n"
            message += "\n"
            
            keyboard.append([
                InlineKeyboardButton(f"Manage: {goal.title[:20]}...", callback_data=f"goal_manage_{goal.id}")
            ])
            
        keyboard.append([InlineKeyboardButton("« Back", callback_data="goal_menu")])
        
        await self._send_or_edit_message(
            update,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for goal creation."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_goal_creation, pattern="^goal_create$")
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
            persistent=True,
            per_message=True,
            per_chat=False,
            per_user=True,
            allow_reentry=True
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
                "🎯 *Goal Analytics*\n\n"
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

    async def show_goals_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the goals menu."""
        keyboard = [
            [
                InlineKeyboardButton("Create Goal", callback_data="goal_add"),
                InlineKeyboardButton("View Goals", callback_data="goal_view_all")
            ],
            [
                InlineKeyboardButton("Goal Analytics", callback_data="goal_analytics"),
                InlineKeyboardButton("Archive Goals", callback_data="goal_archive")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await update.callback_query.edit_message_text(
            "🎯 *Goals Management*\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        ) 