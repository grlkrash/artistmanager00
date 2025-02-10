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
from .base_handler import BaseHandlerMixin

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_PROJECT_TITLE = "AWAITING_PROJECT_TITLE"
AWAITING_PROJECT_DESCRIPTION = "AWAITING_PROJECT_DESCRIPTION"
AWAITING_PROJECT_BUDGET = "AWAITING_PROJECT_BUDGET"
AWAITING_PROJECT_TIMELINE = "AWAITING_PROJECT_TIMELINE"
AWAITING_PROJECT_TEAM = "AWAITING_PROJECT_TEAM"
AWAITING_PROJECT_MILESTONES = "AWAITING_PROJECT_MILESTONES"

class ProjectHandlers(BaseHandlerMixin):
    """Project management handlers."""
    
    group = 2  # Handler group for registration
    
    def __init__(self, bot):
        self.bot = bot

    def get_handlers(self) -> List[BaseHandler]:
        """Get project-related handlers."""
        return [
            CommandHandler("projects", self.show_projects),
            CommandHandler("newproject", self.start_project_creation),
            self.get_conversation_handler(),
            CallbackQueryHandler(self.handle_project_callback, pattern="^project_")
        ]

    def get_conversation_handler(self) -> ConversationHandler:
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
                await update.message.reply_text(
                    "Please complete your profile setup first using /me"
                )
                return

            # Get all projects
            projects = list(self.bot.project_manager.projects.values())
            
            if not projects:
                keyboard = [[InlineKeyboardButton("Create New Project", callback_data="project_create")]]
                await update.message.reply_text(
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
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
                
        except Exception as e:
            logger.error(f"Error showing projects: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error loading your projects. Please try again."
            )

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

    async def handle_project_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle project-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("project_", "")
        
        if action.startswith("type_"):
            project_type = action.replace("type_", "")
            await self._create_project_from_template(update, context, project_type)
            
        elif action.startswith("manage_"):
            project_id = action.replace("manage_", "")
            await self._show_project_management(update, context, project_id)
            
        elif action == "create":
            await self.start_project_creation(update, context)
            
        elif action.startswith("milestone_"):
            project_id = action.split("_")[1]
            milestone_action = action.split("_")[2]
            await self._handle_milestone_action(update, context, project_id, milestone_action)
            
        elif action.startswith("team_"):
            project_id = action.split("_")[1]
            team_action = action.split("_")[2]
            await self._handle_team_action(update, context, project_id, team_action)

    async def _create_project_from_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_type: str) -> None:
        """Create a project from a template."""
        try:
            templates = {
                "album": {
                    "title": "New Album Project",
                    "description": "Record and release a new album",
                    "milestones": [
                        "Song Selection",
                        "Pre-production",
                        "Recording",
                        "Mixing",
                        "Mastering",
                        "Release Planning",
                        "Distribution"
                    ],
                    "roles": [
                        "Producer",
                        "Engineer",
                        "Session Musicians",
                        "Mixing Engineer",
                        "Mastering Engineer"
                    ]
                },
                "tour": {
                    "title": "Tour Project",
                    "description": "Plan and execute a tour",
                    "milestones": [
                        "Route Planning",
                        "Venue Booking",
                        "Budget Planning",
                        "Promotion",
                        "Rehearsals",
                        "Tour Execution",
                        "Post-tour Analysis"
                    ],
                    "roles": [
                        "Tour Manager",
                        "Sound Engineer",
                        "Road Crew",
                        "Merchandise Manager",
                        "Promoter"
                    ]
                },
                "marketing": {
                    "title": "Marketing Campaign",
                    "description": "Promote your music",
                    "milestones": [
                        "Strategy Development",
                        "Content Creation",
                        "Social Media Planning",
                        "Ad Campaign Setup",
                        "Influencer Outreach",
                        "Campaign Launch",
                        "Performance Analysis"
                    ],
                    "roles": [
                        "Marketing Manager",
                        "Content Creator",
                        "Social Media Manager",
                        "PR Specialist",
                        "Analytics Expert"
                    ]
                }
            }
            
            if project_type not in templates:
                # Handle custom project
                context.user_data["creating_project"] = True
                await update.callback_query.edit_message_text(
                    "Please enter your project title:",
                    reply_markup=ForceReply(selective=True)
                )
                return AWAITING_PROJECT_TITLE

            template = templates[project_type]
            project_id = str(uuid.uuid4())
            
            # Create project
            project = Project(
                id=project_id,
                title=template["title"],
                description=template["description"],
                start_date=datetime.now(),
                end_date=None,
                status="planning",
                team_members=[],
                budget=0,
                milestones=template["milestones"],
                required_roles=template["roles"]
            )
            
            self.bot.project_manager.projects[project_id] = project
            
            # Show project setup
            keyboard = [
                [
                    InlineKeyboardButton("Set Budget", callback_data=f"project_budget_{project_id}"),
                    InlineKeyboardButton("Add Team", callback_data=f"project_team_{project_id}")
                ],
                [
                    InlineKeyboardButton("Edit Milestones", callback_data=f"project_milestones_{project_id}"),
                    InlineKeyboardButton("Set Timeline", callback_data=f"project_timeline_{project_id}")
                ],
                [InlineKeyboardButton("Start Project", callback_data=f"project_start_{project_id}")]
            ]
            
            await update.callback_query.edit_message_text(
                f"🎵 Project Created: {template['title']}\n\n"
                f"Description: {template['description']}\n\n"
                "Default milestones:\n" +
                "\n".join(f"• {m}" for m in template["milestones"]) + "\n\n"
                "Required roles:\n" +
                "\n".join(f"• {r}" for r in template["roles"]) + "\n\n"
                "Please complete the project setup:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error creating project from template: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error creating your project. Please try again."
            )

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