"""Task management handlers for the Artist Manager Bot."""
from datetime import datetime
import uuid
import logging
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Message, ForceReply
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    BaseHandler
)
from ..models import Task
from .base_handler import BaseBotHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
AWAITING_TASK_TITLE = "AWAITING_TASK_TITLE"
AWAITING_TASK_PRIORITY = "AWAITING_TASK_PRIORITY"
AWAITING_TASK_DESCRIPTION = "AWAITING_TASK_DESCRIPTION"
AWAITING_TASK_DUE_DATE = "AWAITING_TASK_DUE_DATE"

class TaskHandlers(BaseBotHandler):
    """Task management handlers."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 3  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get task-related handlers."""
        return [
            CommandHandler("tasks", self.show_menu),
            CallbackQueryHandler(self.handle_task_callback, pattern="^(menu_tasks|task_.*|task_menu)$"),
            self.get_conversation_handler()
        ]

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for task creation."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_task_creation, pattern="^task_create$"),
                CommandHandler("newtask", self.start_task_creation)
            ],
            states={
                AWAITING_TASK_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_title)
                ],
                AWAITING_TASK_PRIORITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_priority)
                ],
                AWAITING_TASK_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_description)
                ],
                AWAITING_TASK_DUE_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_due_date)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_task_creation)
            ],
            name="task_creation",
            persistent=True,
            per_message=True,
            per_chat=False,
            per_user=True,
            allow_reentry=True
        )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the main task management menu."""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("Create Task", callback_data="task_create"),
                    InlineKeyboardButton("View Tasks", callback_data="task_view")
                ],
                [
                    InlineKeyboardButton("Complete Task", callback_data="task_complete"),
                    InlineKeyboardButton("Task Analytics", callback_data="task_analytics")
                ],
                [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
            ]
            
            await self._send_or_edit_message(
                update,
                "📋 Task Management:\n\n"
                "• Create new tasks\n"
                "• View and manage tasks\n"
                "• Mark tasks complete\n"
                "• View task analytics",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing task menu: {str(e)}")
            await self._handle_error(update)

    async def handle_task_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle task-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both task_ and menu_tasks patterns
            original_data = query.data
            action = query.data.replace("task_", "").replace("menu_tasks", "menu")
            logger.info(f"Task handler processing callback: {original_data} -> {action}")
            
            if action == "menu":
                logger.info("Showing tasks menu")
                await self.show_menu(update, context)
            elif action == "add" or action == "create":
                logger.info("Starting task creation")
                await self.start_task_creation(update, context)
            elif action == "view_all" or action == "view":
                logger.info("Showing task details")
                await self.show_task_details(update, context)
            elif action == "back":
                logger.info("Returning to main menu")
                await self.bot.show_menu(update, context)
            elif action.startswith("manage_"):
                task_id = action.replace("manage_", "")
                logger.info(f"Managing task: {task_id}")
                await self._show_task_management(update, context, task_id)
            else:
                logger.warning(f"Unknown action in task handler: {action}")
                await self._handle_error(update)
        except Exception as e:
            logger.error(f"Error in task callback handler: {str(e)}", exc_info=True)
            await self._handle_error(update)

    async def start_task_creation(self, message: Message, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start the task creation process."""
        try:
            context.user_data["creating_task"] = {
                "step": "title",
                "data": {}
            }
            
            await message.reply_text(
                "📝 Let's create a new task!\n\n"
                "What's the title of the task?\n"
                "Example: 'Record vocals for new track'",
                reply_markup=ForceReply(selective=True)
            )
            
            return AWAITING_TASK_TITLE
            
        except Exception as e:
            logger.error(f"Error starting task creation: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error starting task creation. Please try again later."
            )
            return ConversationHandler.END

    async def handle_task_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle task title input."""
        try:
            title = update.message.text
            context.user_data["creating_task"]["data"]["title"] = title
            
            keyboard = [
                ["🔴 High", "🟡 Medium", "🟢 Low"]
            ]
            await update.message.reply_text(
                "What's the priority level for this task?",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            
            context.user_data["creating_task"]["step"] = "priority"
            return AWAITING_TASK_PRIORITY
            
        except Exception as e:
            logger.error(f"Error handling task title: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your input. Please try again."
            )
            return ConversationHandler.END

    async def handle_task_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle task priority input."""
        try:
            priority = update.message.text.lower().replace("🔴 ", "").replace("🟡 ", "").replace("🟢 ", "")
            if priority not in ["high", "medium", "low"]:
                await update.message.reply_text(
                    "Please select a valid priority level: High, Medium, or Low"
                )
                return AWAITING_TASK_PRIORITY
                
            context.user_data["creating_task"]["data"]["priority"] = priority
            
            await update.message.reply_text(
                "Enter a description for the task (or type 'skip' to skip):\n\n"
                "This helps track progress and provide context.",
                reply_markup=ForceReply(selective=True)
            )
            
            context.user_data["creating_task"]["step"] = "description"
            return AWAITING_TASK_DESCRIPTION
            
        except Exception as e:
            logger.error(f"Error handling task priority: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your input. Please try again."
            )
            return ConversationHandler.END

    async def handle_task_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle task description input."""
        try:
            description = update.message.text
            if description.lower() != "skip":
                context.user_data["creating_task"]["data"]["description"] = description
                
            await update.message.reply_text(
                "When is this task due?\n"
                "Enter the date in YYYY-MM-DD format\n"
                "Example: 2024-12-31\n\n"
                "Or type 'skip' to skip setting a due date.",
                reply_markup=ForceReply(selective=True)
            )
            
            context.user_data["creating_task"]["step"] = "due_date"
            return AWAITING_TASK_DUE_DATE
            
        except Exception as e:
            logger.error(f"Error handling task description: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your input. Please try again."
            )
            return ConversationHandler.END

    async def handle_task_due_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle task due date input and create task."""
        try:
            date_str = update.message.text
            if date_str.lower() != "skip":
                try:
                    due_date = datetime.strptime(date_str, "%Y-%m-%d")
                    context.user_data["creating_task"]["data"]["due_date"] = due_date
                except ValueError:
                    await update.message.reply_text(
                        "Invalid date format. Please use YYYY-MM-DD format or type 'skip':"
                    )
                    return AWAITING_TASK_DUE_DATE
            
            # Create the task
            task_data = context.user_data["creating_task"]["data"]
            task_data["id"] = str(uuid.uuid4())
            task_data["status"] = "pending"
            task_data["created_at"] = datetime.now()
            
            task = Task(**task_data)
            await self.bot.task_manager_integration.create_task(task)
            
            # Clear creation state
            del context.user_data["creating_task"]
            
            # Show success message with options
            keyboard = [
                [
                    InlineKeyboardButton("Add Another Task", callback_data="task_create"),
                    InlineKeyboardButton("View Tasks", callback_data="task_view")
                ],
                [InlineKeyboardButton("Back to Menu", callback_data="task_menu")]
            ]
            
            await update.message.reply_text(
                "✅ Task created successfully!\n\n"
                f"Title: {task.title}\n"
                f"Priority: {task.priority}\n"
                f"Due: {task.due_date.strftime('%Y-%m-%d') if task.due_date else 'Not set'}\n\n"
                "What would you like to do next?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error handling task due date: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error creating your task. Please try again later."
            )
            return ConversationHandler.END

    async def cancel_task_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel task creation process."""
        if "creating_task" in context.user_data:
            del context.user_data["creating_task"]
            
        await update.message.reply_text(
            "Task creation cancelled. Use /tasks to manage your tasks."
        )
        return ConversationHandler.END

    async def show_task_completion_options(self, message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show options for completing tasks."""
        try:
            # Get incomplete tasks
            pending_tasks = await self.bot.task_manager_integration.get_tasks_by_status("pending")
            in_progress_tasks = await self.bot.task_manager_integration.get_tasks_by_status("in_progress")
            tasks = pending_tasks + in_progress_tasks
            
            if not tasks:
                await message.reply_text(
                    "No incomplete tasks found.\n"
                    "Use /newtask to create a task."
                )
                return
            
            # Create keyboard with task options
            keyboard = []
            for task in tasks:
                keyboard.append([
                    InlineKeyboardButton(
                        f"✓ {task.title[:30]}...",
                        callback_data=f"task_complete_{task.id}"
                    )
                ])
            
            # Add menu option
            keyboard.append([InlineKeyboardButton("Back to Menu", callback_data="task_menu")])
            
            await message.reply_text(
                "Select a task to mark as complete:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing task completion options: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving tasks. Please try again later."
            )

    async def complete_task(self, message: Message, context: ContextTypes.DEFAULT_TYPE, task_id: str) -> None:
        """Mark a task as complete."""
        try:
            # Update task status
            updates = {
                "status": "completed",
                "completed_at": datetime.now()
            }
            task = await self.bot.task_manager_integration.update_task(task_id, updates)
            
            if task:
                # Show success message with options
                keyboard = [
                    [
                        InlineKeyboardButton("Complete Another", callback_data="task_complete"),
                        InlineKeyboardButton("View Tasks", callback_data="task_view")
                    ],
                    [InlineKeyboardButton("Back to Menu", callback_data="task_menu")]
                ]
                
                await message.reply_text(
                    f"✅ Task completed: {task.title}\n\n"
                    "Great job! Keep up the momentum!",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await message.reply_text("Task not found.")
                
        except Exception as e:
            logger.error(f"Error completing task: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error completing the task. Please try again later."
            )

    async def show_task_details(self, message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show detailed task list with options."""
        try:
            # Get all tasks
            pending = await self.bot.task_manager_integration.get_tasks_by_status("pending")
            in_progress = await self.bot.task_manager_integration.get_tasks_by_status("in_progress")
            completed = await self.bot.task_manager_integration.get_tasks_by_status("completed")
            
            # Create task list by status
            sections = {
                "📋 Pending": pending,
                "🔄 In Progress": in_progress,
                "✅ Completed": completed
            }
            
            message_text = "Task Details:\n\n"
            keyboard = []
            
            for status, tasks in sections.items():
                if tasks:
                    message_text += f"{status}:\n"
                    for task in tasks:
                        message_text += f"• {task.title}\n"
                        keyboard.append([
                            InlineKeyboardButton(
                                f"View {task.title[:20]}...",
                                callback_data=f"task_view_{task.id}"
                            )
                        ])
                    message_text += "\n"
            
            if not keyboard:
                keyboard = [[InlineKeyboardButton("Create Task", callback_data="task_create")]]
                await message.reply_text(
                    "No tasks found. Would you like to create one?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
                
            # Add menu options
            keyboard.append([
                InlineKeyboardButton("Create New Task", callback_data="task_create"),
                InlineKeyboardButton("Back to Menu", callback_data="task_menu")
            ])
            
            await message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing task details: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving tasks. Please try again later."
            )

    async def show_task_analytics(self, message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show task analytics and insights."""
        try:
            # Get task statistics
            pending = await self.bot.task_manager_integration.get_tasks_by_status("pending")
            in_progress = await self.bot.task_manager_integration.get_tasks_by_status("in_progress")
            completed = await self.bot.task_manager_integration.get_tasks_by_status("completed")
            overdue = await self.bot.task_manager_integration.get_overdue_tasks()
            upcoming = await self.bot.task_manager_integration.get_upcoming_tasks(7)  # Next 7 days
            
            # Calculate completion rate
            total_tasks = len(pending) + len(in_progress) + len(completed)
            completion_rate = (len(completed) / total_tasks * 100) if total_tasks > 0 else 0
            
            # Format analytics message
            message_text = (
                "📊 Task Analytics\n\n"
                f"Total Tasks: {total_tasks}\n"
                f"Completion Rate: {completion_rate:.1f}%\n\n"
                "Status Breakdown:\n"
                f"• Pending: {len(pending)}\n"
                f"• In Progress: {len(in_progress)}\n"
                f"• Completed: {len(completed)}\n\n"
                "Time Analysis:\n"
                f"• Overdue: {len(overdue)}\n"
                f"• Due Soon: {len(upcoming)}\n"
            )
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("View Tasks", callback_data="task_view"),
                    InlineKeyboardButton("Create Task", callback_data="task_create")
                ],
                [InlineKeyboardButton("Back to Menu", callback_data="task_menu")]
            ]
            
            await message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing task analytics: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving task analytics. Please try again later."
            ) 