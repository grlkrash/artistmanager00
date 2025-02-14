"""Task management handlers for the Artist Manager Bot."""
from datetime import datetime
import uuid
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, ForceReply, ReplyKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    BaseHandler
)
from ...models import Task
from ..core.base_handler import BaseBotHandler
from ...utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
AWAITING_TASK_TITLE = "AWAITING_TASK_TITLE"
AWAITING_TASK_DESCRIPTION = "AWAITING_TASK_DESCRIPTION"
AWAITING_TASK_PRIORITY = "AWAITING_TASK_PRIORITY"
AWAITING_TASK_DUE_DATE = "AWAITING_TASK_DUE_DATE"

class TaskHandlers(BaseBotHandler):
    """Task management handlers."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.conversation_handler = self.get_conversation_handler()

    def get_handlers(self) -> List[BaseHandler]:
        """Get all handlers for this module."""
        return [
            self.conversation_handler,
            CommandHandler("tasks", self.show_menu),
            CallbackQueryHandler(self.handle_callback, pattern="^task_")
        ]

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("task_", "")
        
        if action == "create":
            await self.start_task_creation(query.message, context)
        elif action == "complete":
            await self.show_task_completion_options(query.message, context)
        elif action == "view":
            await self.show_task_details(query.message, context)
        elif action == "edit":
            await self.show_task_edit_options(query.message, context)
        elif action.startswith("view_"):
            task_id = action.replace("view_", "")
            await self.show_specific_task(query.message, context, task_id)
        elif action.startswith("complete_"):
            task_id = action.replace("complete_", "")
            await self.complete_task(query.message, context, task_id)
        elif action.startswith("edit_"):
            task_id = action.replace("edit_", "")
            await self.edit_task(query.message, context, task_id)
        elif action == "menu":
            await self.show_menu(update, context)

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the main menu for tasks."""
        keyboard = [
            [InlineKeyboardButton("➕ Create Task", callback_data="task_create")],
            [
                InlineKeyboardButton("📋 View Tasks", callback_data="task_view"),
                InlineKeyboardButton("✅ Complete Tasks", callback_data="task_complete")
            ],
            [InlineKeyboardButton("« Back to Main Menu", callback_data="main_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "📝 *Task Management*\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for task creation."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_task_creation, pattern="^task_create$"),
                CommandHandler("task", self.start_task_creation)
            ],
            states={
                AWAITING_TASK_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_title)
                ],
                AWAITING_TASK_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_description)
                ],
                AWAITING_TASK_PRIORITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_priority)
                ],
                AWAITING_TASK_DUE_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_due_date)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_task_creation),
                CallbackQueryHandler(self.cancel_task_creation, pattern="^task_cancel$")
            ],
            name="task_creation",
            persistent=True
        )

    async def cancel_task_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel task creation process."""
        if "creating_task" in context.user_data:
            del context.user_data["creating_task"]
            
        await self._send_or_edit_message(
            update,
            "Task creation cancelled. Use /tasks to manage your tasks.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Tasks", callback_data="task_menu")
            ]])
        )
        return ConversationHandler.END

    async def start_task_creation(self, message: Message, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start the task creation process."""
        context.user_data["creating_task"] = {}
        await message.reply_text(
            "Let's create a new task. First, what's the title of the task?"
        )
        return AWAITING_TASK_TITLE

    async def handle_task_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle task title input."""
        context.user_data["creating_task"]["title"] = update.message.text
        
        keyboard = [
            ["High", "Medium", "Low"]
        ]
        await update.message.reply_text(
            "What's the priority level for this task?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_TASK_PRIORITY

    async def handle_task_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle task priority input."""
        priority = update.message.text.lower()
        if priority not in ["high", "medium", "low"]:
            await update.message.reply_text(
                "Please select a valid priority level: High, Medium, or Low"
            )
            return AWAITING_TASK_PRIORITY
            
        context.user_data["creating_task"]["priority"] = priority
        
        await update.message.reply_text(
            "Enter a description for the task (or type 'skip' to skip):"
        )
        return AWAITING_TASK_DESCRIPTION

    async def handle_task_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle task description input."""
        description = update.message.text
        if description.lower() != "skip":
            context.user_data["creating_task"]["description"] = description
            
        await update.message.reply_text(
            "When is this task due? Enter the date in YYYY-MM-DD format (or type 'skip' to skip):"
        )
        return AWAITING_TASK_DUE_DATE

    async def handle_task_due_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle task due date input and create task."""
        date_str = update.message.text
        if date_str.lower() != "skip":
            try:
                due_date = datetime.strptime(date_str, "%Y-%m-%d")
                context.user_data["creating_task"]["due_date"] = due_date
            except ValueError:
                await update.message.reply_text(
                    "Invalid date format. Please use YYYY-MM-DD format or type 'skip':"
                )
                return AWAITING_TASK_DUE_DATE
        
        # Create the task
        task_data = context.user_data["creating_task"]
        task = Task(
            id=str(uuid.uuid4()),
            title=task_data["title"],
            description=task_data.get("description", ""),
            priority=task_data["priority"],
            status="pending",
            due_date=task_data.get("due_date"),
            created_at=datetime.now()
        )
        
        try:
            await self.bot.task_manager_integration.create_task(task)
            
            # Clear the creation data
            del context.user_data["creating_task"]
            
            keyboard = [
                [
                    InlineKeyboardButton("View Tasks", callback_data="task_list"),
                    InlineKeyboardButton("Create Another", callback_data="task_create")
                ]
            ]
            
            await update.message.reply_text(
                f"✅ Task created successfully!\n\n"
                f"Title: {task.title}\n"
                f"Priority: {task.priority}\n"
                f"Due: {task.due_date.strftime('%Y-%m-%d') if task.due_date else 'Not set'}\n\n"
                "What would you like to do next?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error creating your task. Please try again."
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
                await message.reply_text("No incomplete tasks found.")
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
            
            await message.reply_text(
                "Select a task to mark as complete:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing task completion options: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving tasks. Please try again."
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
                await message.reply_text(
                    f"✅ Task completed: {task.title}\n\n"
                    f"Great job! Keep up the momentum!"
                )
            else:
                await message.reply_text("Task not found.")
                
        except Exception as e:
            logger.error(f"Error completing task: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error completing the task. Please try again."
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
                await message.reply_text("No tasks found.")
                return
                
            keyboard.append([InlineKeyboardButton("Create New Task", callback_data="task_create")])
            
            await message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing task details: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving task details. Please try again."
            )

    async def show_specific_task(self, message: Message, context: ContextTypes.DEFAULT_TYPE, task_id: str) -> None:
        """Show details for a specific task."""
        try:
            task = await self.bot.task_manager_integration.get_task(task_id)
            if not task:
                await message.reply_text("Task not found.")
                return
                
            # Format task details
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅"
            }.get(task.status, "❓")
            
            priority_color = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(task.priority, "⚪")
            
            details = (
                f"{status_emoji} Task Details:\n\n"
                f"Title: {task.title}\n"
                f"Priority: {priority_color} {task.priority}\n"
                f"Status: {task.status}\n"
            )
            
            if task.description:
                details += f"\nDescription:\n{task.description}\n"
                
            if task.due_date:
                details += f"\nDue: {task.due_date.strftime('%Y-%m-%d')}"
                
            if task.created_at:
                details += f"\nCreated: {task.created_at.strftime('%Y-%m-%d')}"
                
            if task.completed_at:
                details += f"\nCompleted: {task.completed_at.strftime('%Y-%m-%d')}"
            
            # Create action buttons
            keyboard = []
            if task.status != "completed":
                keyboard.append([
                    InlineKeyboardButton("Complete Task", callback_data=f"task_complete_{task.id}"),
                    InlineKeyboardButton("Edit Task", callback_data=f"task_edit_{task.id}")
                ])
            
            keyboard.append([InlineKeyboardButton("Back to Tasks", callback_data="task_view")])
            
            await message.reply_text(
                details,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing task details: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving the task details. Please try again."
            )

    async def show_task_edit_options(self, message: Message, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Show options for editing a task."""
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
            
            message_text = "Select a task to edit:\n\n"
            keyboard = []
            
            for status, tasks in sections.items():
                if tasks:
                    message_text += f"{status}:\n"
                    for task in tasks:
                        message_text += f"• {task.title}\n"
                        keyboard.append([
                            InlineKeyboardButton(
                                f"Edit {task.title[:20]}...",
                                callback_data=f"task_edit_{task.id}"
                            )
                        ])
                    message_text += "\n"
            
            if not keyboard:
                await message.reply_text("No tasks found.")
                return ConversationHandler.END
                
            keyboard.append([InlineKeyboardButton("Back to Tasks", callback_data="task_view")])
            
            await message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return AWAITING_TASK_EDIT
            
        except Exception as e:
            logger.error(f"Error showing task edit options: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving tasks. Please try again."
            )
            return ConversationHandler.END

    async def edit_task(self, message: Message, context: ContextTypes.DEFAULT_TYPE, task_id: str) -> str:
        """Handle task editing."""
        try:
            # Get task details
            task = await self.bot.task_manager_integration.get_task(task_id)
            if not task:
                await message.reply_text("Task not found.")
                return ConversationHandler.END
                
            # Show task details for confirmation
            await message.reply_text(
                f"Current task details:\n\n"
                f"Title: {task.title}\n"
                f"Priority: {task.priority}\n"
                f"Status: {task.status}\n"
                f"Due: {task.due_date.strftime('%Y-%m-%d') if task.due_date else 'Not set'}\n\n"
                "Enter new details (or type 'skip' to keep current):"
            )
            return AWAITING_TASK_TITLE
            
        except Exception as e:
            logger.error(f"Error editing task: {str(e)}")
            await message.reply_text(
                "Sorry, there was an error retrieving the task details. Please try again."
            )
            return ConversationHandler.END 