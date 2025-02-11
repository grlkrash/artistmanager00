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
from ..models import Project
from .base_handler import BaseBotHandler
from ..utils.logger import get_logger

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
        super().__init__(bot)
        self.group = 4  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get project-related handlers."""
        return [
            CommandHandler("projects", self.show_menu),
            CallbackQueryHandler(self.handle_project_callback, pattern="^(menu_projects|project_.*|project_menu)$"),
            self.get_conversation_handler()
        ]

    async def handle_project_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle project-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both project_ and menu_projects patterns
            original_data = query.data
            action = query.data.replace("project_", "").replace("menu_projects", "menu")
            logger.info(f"Project handler processing callback: {original_data} -> {action}")
            
            if action == "menu":
                logger.info("Showing projects menu")
                await self.show_menu(update, context)
            elif action == "create":
                logger.info("Showing create project interface")
                await self._show_create_project(update, context)
            elif action == "view_all":
                logger.info("Showing all projects")
                await self._show_all_projects(update, context)
            elif action == "back":
                logger.info("Returning to main menu")
                await self.bot.show_menu(update, context)
            elif action.startswith("manage_"):
                project_id = action.replace("manage_", "")
                logger.info(f"Managing project: {project_id}")
                await self._show_project_management(update, context, project_id)
            else:
                logger.warning(f"Unknown action in project handler: {action}")
                await self._handle_error(update)
        except Exception as e:
            logger.error(f"Error in project callback handler: {str(e)}", exc_info=True)
            await self._handle_error(update)

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the projects menu."""
        keyboard = [
            [
                InlineKeyboardButton("Create Project", callback_data="project_create"),
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

    async def _show_create_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show project creation interface."""
        keyboard = [
            [
                InlineKeyboardButton("Album Project", callback_data="project_type_album"),
                InlineKeyboardButton("Tour Project", callback_data="project_type_tour")
            ],
            [
                InlineKeyboardButton("Marketing Campaign", callback_data="project_type_marketing"),
                InlineKeyboardButton("Custom Project", callback_data="project_type_custom")
            ],
            [InlineKeyboardButton("« Back", callback_data="project_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "What type of project would you like to create?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_all_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all user projects."""
        keyboard = [[InlineKeyboardButton("« Back", callback_data="project_menu")]]
        
        await self._send_or_edit_message(
            update,
            "Your projects will appear here soon!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for project creation."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_project_creation, pattern="^project_create$"),
                CommandHandler("newproject", self.start_project_creation)
            ],
            states={
                AWAITING_PROJECT_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_project_title)
                ],
                AWAITING_PROJECT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_project_description)
                ],
                AWAITING_PROJECT_BUDGET: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_project_budget)
                ],
                AWAITING_PROJECT_TIMELINE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_project_timeline)
                ],
                AWAITING_PROJECT_TEAM: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_project_team)
                ],
                AWAITING_PROJECT_MILESTONES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_project_milestones)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_project_creation)
            ],
            name="project_creation",
            persistent=True
        )

    async def show_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all projects."""
        try:
            user_id = update.effective_user.id
            profile = self.bot.profiles.get(user_id)
            
            if not profile:
                await self._send_or_edit_message(
                    update,
                    "Please complete your profile setup first using /me"
                )
                return

            # Get all projects
            projects = list(self.bot.project_manager.projects.values())
            
            if not projects:
                keyboard = [[InlineKeyboardButton("Create New Project", callback_data="project_create")]]
                await self._send_or_edit_message(
                    update,
                    "No projects found. Would you like to create one?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            # Create project list with buttons
            message = "🎵 Your Projects:\n\n"
            keyboard = []
            
            for project in projects:
                status_emoji = {
                    "active": "🟢",
                    "completed": "✅",
                    "on_hold": "⏸️",
                    "cancelled": "❌"
                }.get(project.status, "❓")
                
                message += (
                    f"{status_emoji} {project.title}\n"
                    f"Budget: ${project.budget:,.2f}\n"
                    f"Status: {project.status.title()}\n"
                    f"Team: {len(project.team_members)} members\n\n"
                )
                
                keyboard.append([
                    InlineKeyboardButton(f"Manage {project.title}", callback_data=f"project_manage_{project.id}")
                ])

            keyboard.append([InlineKeyboardButton("➕ Create New Project", callback_data="project_create")])
            keyboard.append([InlineKeyboardButton("« Back", callback_data="project_menu")])
            
            await self._send_or_edit_message(
                update,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
                
        except Exception as e:
            logger.error(f"Error showing projects: {str(e)}")
            await self._handle_error(update)

    async def start_project_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start project creation flow."""
        try:
            keyboard = [
                [InlineKeyboardButton("Album Project", callback_data="project_type_album")],
                [InlineKeyboardButton("Tour Project", callback_data="project_type_tour")],
                [InlineKeyboardButton("Marketing Campaign", callback_data="project_type_marketing")],
                [InlineKeyboardButton("Custom Project", callback_data="project_type_custom")]
            ]
            
            await update.message.reply_text(
                "🎵 Create New Project\n\n"
                "Choose a project type:\n\n"
                "• Album Project - Record and release an album\n"
                "• Tour Project - Plan and execute a tour\n"
                "• Marketing Campaign - Promote your music\n"
                "• Custom Project - Create your own project type",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return AWAITING_PROJECT_TITLE
            
        except Exception as e:
            logger.error(f"Error starting project creation: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting project creation. Please try again."
            )
            return ConversationHandler.END

    async def handle_project_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle project title input."""
        title = update.message.text.strip()
        context.user_data["project_title"] = title
        
        await update.message.reply_text(
            "Great! Now please provide a description of your project:",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_PROJECT_DESCRIPTION

    async def handle_project_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle project description input."""
        description = update.message.text.strip()
        context.user_data["project_description"] = description
        
        await update.message.reply_text(
            "What's your budget for this project? (Enter a number in USD)",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_PROJECT_BUDGET

    async def handle_project_budget(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle project budget input."""
        try:
            budget = float(update.message.text.strip().replace("$", "").replace(",", ""))
            context.user_data["project_budget"] = budget
            
            await update.message.reply_text(
                "When do you want to complete this project?\n"
                "Please enter a target date (YYYY-MM-DD):",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_PROJECT_TIMELINE
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for the budget (e.g. 5000):"
            )
            return AWAITING_PROJECT_BUDGET

    async def handle_project_timeline(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle project timeline input."""
        try:
            end_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
            context.user_data["project_end_date"] = end_date
            
            await update.message.reply_text(
                "List the key milestones for this project, one per line:\n\n"
                "Example:\n"
                "Research phase\n"
                "Planning complete\n"
                "First draft\n"
                "Final delivery",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_PROJECT_MILESTONES
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid date in YYYY-MM-DD format:"
            )
            return AWAITING_PROJECT_TIMELINE

    async def handle_project_team(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle project team input."""
        team_members = update.message.text.split(',')
        team_members = [member.strip() for member in team_members]
        
        if not context.user_data.get('temp_project'):
            context.user_data['temp_project'] = {}
            
        context.user_data['temp_project']['team'] = team_members
        
        await update.message.reply_text(
            "Great! Now, let's set some milestones for the project.\n\n"
            "Please enter the key milestones for this project, one per line.\n"
            "For example:\n"
            "- Initial planning (2 weeks)\n"
            "- Development phase (1 month)\n"
            "- Testing (2 weeks)\n"
            "- Launch (1 week)"
        )
        
        return AWAITING_PROJECT_MILESTONES
        
    async def handle_project_milestones(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle project milestones input."""
        milestones = update.message.text.split('\n')
        milestones = [milestone.strip() for milestone in milestones if milestone.strip()]
        
        if not context.user_data.get('temp_project'):
            context.user_data['temp_project'] = {}
            
        context.user_data['temp_project']['milestones'] = milestones
        
        # Create the project
        project_data = context.user_data['temp_project']
        new_project = Project(
            id=str(uuid.uuid4()),
            title=project_data['title'],
            description=project_data['description'],
            budget=project_data['budget'],
            timeline=project_data['timeline'],
            team=project_data['team'],
            milestones=project_data['milestones'],
            status="planning",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save the project
        self.bot.project_manager.add_project(new_project)
        
        # Clear temporary data
        context.user_data.pop('temp_project', None)
        
        # Show confirmation
        await update.message.reply_text(
            f"✅ Project '{new_project.title}' has been created successfully!\n\n"
            f"Use /projects to view and manage your projects.",
            parse_mode="Markdown"
        )
        
        return ConversationHandler.END

    async def cancel_project_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel project creation."""
        context.user_data.clear()
        await update.message.reply_text(
            "Project creation cancelled. You can start over with /newproject"
        )
        return ConversationHandler.END

    async def _show_project_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str) -> None:
        """Show project management options."""
        try:
            project = self.bot.project_manager.projects.get(project_id)
            if not project:
                await update.callback_query.edit_message_text(
                    "Project not found. It may have been deleted."
                )
                return
                
            status_emoji = {
                "active": "🟢",
                "completed": "✅",
                "on_hold": "⏸️",
                "cancelled": "❌"
            }.get(project.status, "❓")
            
            message = (
                f"{status_emoji} Project: {project.title}\n\n"
                f"Description: {project.description}\n"
                f"Budget: ${project.budget:,.2f}\n"
                f"Status: {project.status.title()}\n"
                f"Timeline: {project.start_date.date()} to {project.end_date.date() if project.end_date else 'TBD'}\n\n"
                "Milestones:\n" +
                "\n".join(f"• {m}" for m in project.milestones) + "\n\n"
                f"Team Members: {len(project.team_members)}"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("Update Status", callback_data=f"project_status_{project_id}"),
                    InlineKeyboardButton("Edit Details", callback_data=f"project_edit_{project_id}")
                ],
                [
                    InlineKeyboardButton("Manage Team", callback_data=f"project_team_{project_id}"),
                    InlineKeyboardButton("View Tasks", callback_data=f"project_tasks_{project_id}")
                ],
                [
                    InlineKeyboardButton("Update Milestones", callback_data=f"project_milestones_{project_id}"),
                    InlineKeyboardButton("Project Analytics", callback_data=f"project_analytics_{project_id}")
                ],
                [InlineKeyboardButton("Back to Projects", callback_data="show_projects")]
            ]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing project management: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error loading the project. Please try again."
            )

    async def _handle_milestone_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str, action: str) -> None:
        """Handle milestone-related actions."""
        try:
            project = self.bot.project_manager.projects.get(project_id)
            if not project:
                await update.callback_query.edit_message_text(
                    "Project not found. It may have been deleted."
                )
                return
                
            if action == "view":
                message = f"Milestones for {project.title}:\n\n"
                for i, milestone in enumerate(project.milestones, 1):
                    message += f"{i}. {milestone}\n"
                    
                keyboard = [[InlineKeyboardButton("Back", callback_data=f"project_manage_{project_id}")]]
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            elif action == "add":
                context.user_data["editing_milestones"] = project_id
                await update.callback_query.edit_message_text(
                    "Please enter new milestones, one per line:",
                    reply_markup=ForceReply(selective=True)
                )
                
            elif action == "complete":
                milestone_index = int(context.user_data.get("milestone_index", 0))
                if 0 <= milestone_index < len(project.milestones):
                    # Mark milestone as complete (you might want to add a completion status to milestones)
                    await update.callback_query.edit_message_text(
                        f"Milestone '{project.milestones[milestone_index]}' marked as complete!"
                    )
                    
        except Exception as e:
            logger.error(f"Error handling milestone action: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error processing your request. Please try again."
            )

    async def _handle_team_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str, action: str) -> None:
        """Handle team-related actions."""
        try:
            project = self.bot.project_manager.projects.get(project_id)
            if not project:
                await update.callback_query.edit_message_text(
                    "Project not found. It may have been deleted."
                )
                return
                
            if action == "view":
                if not project.team_members:
                    message = "No team members assigned yet."
                else:
                    message = f"Team members for {project.title}:\n\n"
                    for member in project.team_members:
                        message += f"• {member.name} - {member.role}\n"
                        
                keyboard = [
                    [InlineKeyboardButton("Add Member", callback_data=f"project_team_add_{project_id}")],
                    [InlineKeyboardButton("Back", callback_data=f"project_manage_{project_id}")]
                ]
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            elif action == "add":
                context.user_data["adding_team_member"] = project_id
                await update.callback_query.edit_message_text(
                    "Please enter team member details in format:\n"
                    "name | role | email\n\n"
                    "Example:\n"
                    "John Smith | Producer | john@example.com",
                    reply_markup=ForceReply(selective=True)
                )
                
            elif action == "remove":
                member_id = context.user_data.get("member_id")
                if member_id and member_id in project.team_members:
                    project.team_members.remove(member_id)
                    await update.callback_query.edit_message_text(
                        "Team member removed successfully!"
                    )
                    
        except Exception as e:
            logger.error(f"Error handling team action: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error processing your request. Please try again."
            )

    async def _handle_error(self, update: Update) -> None:
        """Handle general error."""
        await update.message.reply_text(
            "Sorry, there was an error processing your request. Please try again later."
        ) 