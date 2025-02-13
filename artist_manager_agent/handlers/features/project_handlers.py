"""Project management handlers for the Artist Manager Bot."""
from datetime import datetime
import uuid
import logging
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, ForceReply
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    BaseHandler
)
from ...models import Project
from ..core.base_handler import BaseBotHandler
from ...utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
AWAITING_PROJECT_TITLE = "AWAITING_PROJECT_TITLE"
AWAITING_PROJECT_DESCRIPTION = "AWAITING_PROJECT_DESCRIPTION"
AWAITING_PROJECT_BUDGET = "AWAITING_PROJECT_BUDGET"
AWAITING_PROJECT_TIMELINE = "AWAITING_PROJECT_TIMELINE"
AWAITING_PROJECT_TEAM = "AWAITING_PROJECT_TEAM"
AWAITING_PROJECT_MILESTONES = "AWAITING_PROJECT_MILESTONES"

class ProjectHandlers(BaseBotHandler):
    """Handlers for project-related functionality."""
    
    def __init__(self, bot):
        """Initialize project handlers."""
        super().__init__(bot)
        self.group = 4  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get project-related handlers."""
        return [
            CommandHandler("projects", self.show_menu),
            CallbackQueryHandler(self.handle_callback, pattern="^(menu_projects|project_.*|project_menu)$")
        ]

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle project-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both project_ and menu_projects patterns
            action = query.data.replace("menu_projects", "menu").replace("project_", "").strip("_")
            logger.info(f"Project handler processing callback: {query.data} -> {action}")
            
            if action == "menu" or action == "":
                await self.show_menu(update, context)
            elif action == "add":
                await self._show_add_project(update, context)
            elif action == "view_all":
                await self._show_all_projects(update, context)
            elif action == "analytics":
                await self._show_project_analytics(update, context)
            elif action == "archive":
                await self._show_archived_projects(update, context)
            elif action.startswith("manage_"):
                project_id = action.replace("manage_", "")
                await self._show_project_management(update, context, project_id)
            else:
                logger.warning(f"Unknown project action: {action}")
                await self.show_menu(update, context)
                
        except Exception as e:
            logger.error(f"Error in project callback handler: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="project_menu")
                ]])
            )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the projects menu."""
        keyboard = [
            [
                InlineKeyboardButton("Create Project", callback_data="project_add"),
                InlineKeyboardButton("View Projects", callback_data="project_view_all")
            ],
            [
                InlineKeyboardButton("Project Analytics", callback_data="project_analytics"),
                InlineKeyboardButton("Archive Projects", callback_data="project_archive")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            "🚀 *Project Management*\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def _show_add_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show project creation interface."""
        keyboard = [
            [
                InlineKeyboardButton("Quick Project", callback_data="project_quick"),
                InlineKeyboardButton("Detailed Project", callback_data="project_detailed")
            ],
            [InlineKeyboardButton("« Back", callback_data="project_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "How would you like to create your project?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_all_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all user projects."""
        # Get user's projects
        user_id = update.effective_user.id
        projects = await self.bot.task_manager_integration.get_projects(user_id)
        
        if not projects:
            keyboard = [
                [InlineKeyboardButton("Create Project", callback_data="project_add")],
                [InlineKeyboardButton("« Back", callback_data="project_menu")]
            ]
            await self._send_or_edit_message(
                update,
                "You don't have any projects yet. Would you like to create one?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        # Format projects message
        message = "🚀 Your Projects:\n\n"
        keyboard = []
        
        for project in projects:
            status = "✅" if project.completed else "🔄"
            message += f"{status} {project.title}\n"
            if project.due_date:
                message += f"Due: {project.due_date.strftime('%Y-%m-%d')}\n"
            message += f"Progress: {project.get_progress()}%\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"Manage: {project.title[:20]}...", callback_data=f"project_manage_{project.id}")
            ])
            
        keyboard.append([InlineKeyboardButton("« Back", callback_data="project_menu")])
        
        await self._send_or_edit_message(
            update,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_project_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show project analytics."""
        try:
            analytics = await self.bot.task_manager_integration.get_project_analytics()
            
            message = (
                "📊 *Project Analytics*\n\n"
                f"Total Projects: {analytics['total_projects']}\n"
                f"Completed: {analytics['completed_projects']}\n"
                f"In Progress: {analytics['in_progress_projects']}\n"
                f"Overdue: {analytics['overdue_projects']}\n\n"
                "*Projects by Status:*\n"
                f"🟢 On Track: {analytics['projects_by_status']['on_track']}\n"
                f"🟡 At Risk: {analytics['projects_by_status']['at_risk']}\n"
                f"🔴 Behind: {analytics['projects_by_status']['behind']}\n\n"
                "*Projects by Type:*\n"
            )
            
            for project_type, count in analytics['projects_by_type'].items():
                message += f"{project_type}: {count}\n"
                
            keyboard = [[InlineKeyboardButton("« Back", callback_data="project_menu")]]
            
            await self._send_or_edit_message(
                update,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error showing project analytics: {str(e)}")
            await self._handle_error(update)

    async def _show_archived_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show archived projects."""
        # Get user's archived projects
        user_id = update.effective_user.id
        projects = await self.bot.task_manager_integration.get_projects(user_id, archived=True)
        
        if not projects:
            keyboard = [[InlineKeyboardButton("« Back", callback_data="project_menu")]]
            await self._send_or_edit_message(
                update,
                "You don't have any archived projects.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        # Format projects message
        message = "📁 Archived Projects:\n\n"
        keyboard = []
        
        for project in projects:
            message += f"🔒 {project.title}\n"
            if project.completion_date:
                message += f"Completed: {project.completion_date.strftime('%Y-%m-%d')}\n"
            message += "\n"
            
            keyboard.append([
                InlineKeyboardButton(f"Restore: {project.title[:20]}...", callback_data=f"project_restore_{project.id}")
            ])
            
        keyboard.append([InlineKeyboardButton("« Back", callback_data="project_menu")])
        
        await self._send_or_edit_message(
            update,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_project_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str) -> None:
        """Show management options for a specific project."""
        try:
            project = await self.bot.task_manager_integration.get_project(project_id)
            if not project:
                await self._send_or_edit_message(
                    update,
                    "Project not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="project_menu")
                    ]])
                )
                return
                
            # Format project details
            message = (
                f"🚀 {project.title}\n\n"
                f"Description: {project.description}\n"
                f"Status: {project.status}\n"
                f"Progress: {project.get_progress()}%\n"
            )
            if project.due_date:
                message += f"Due: {project.due_date.strftime('%Y-%m-%d')}\n"
                
            keyboard = [
                [
                    InlineKeyboardButton("Update Progress", callback_data=f"project_progress_{project.id}"),
                    InlineKeyboardButton("Edit Project", callback_data=f"project_edit_{project.id}")
                ],
                [
                    InlineKeyboardButton("View Tasks", callback_data=f"project_tasks_{project.id}"),
                    InlineKeyboardButton("Add Task", callback_data=f"project_add_task_{project.id}")
                ],
                [
                    InlineKeyboardButton("Archive Project", callback_data=f"project_archive_{project.id}"),
                    InlineKeyboardButton("Delete Project", callback_data=f"project_delete_{project.id}")
                ],
                [InlineKeyboardButton("« Back", callback_data="project_menu")]
            ]
            
            await self._send_or_edit_message(
                update,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing project management: {str(e)}")
            await self._handle_error(update)

    async def _handle_error(self, update: Update) -> None:
        """Handle general error."""
        await update.message.reply_text(
            "Sorry, there was an error processing your request. Please try again later."
        ) 