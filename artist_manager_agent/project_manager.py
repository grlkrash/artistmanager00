from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import uuid
from .models import Project, Task, CollaboratorProfile
from .log import logger, log_error

class ProjectManager:
    """Handles project management functionality."""
    
    def __init__(self, bot):
        self.bot = bot
        self.projects = {}
        self.tasks = {}
        self.team_members = {}

    async def show_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all projects."""
        try:
            user_id = update.effective_user.id
            profile = self.bot.get_user_profile(user_id)
            
            if not profile:
                await update.message.reply_text(
                    "Please complete your profile setup first with /start"
                )
                return

            # Get all projects
            projects = list(self.projects.values())
            
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

    async def create_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                "• Custom Project - Create your own project type\n\n"
                "Or use the command format:\n"
                "/project_new <title> <description> <budget>",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error creating your project. Please try again."
            )

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
            await self.create_project(update, context)
            
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
                    "Please enter your project details in this format:\n"
                    "<title> | <description> | <budget>\n\n"
                    "Example:\n"
                    "Music Video | Create a professional music video | 5000"
                )
                return
            
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
            
            self.projects[project_id] = project
            
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

    async def _show_project_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str) -> None:
        """Show project management options."""
        try:
            project = self.projects.get(project_id)
            if not project:
                await update.callback_query.edit_message_text(
                    "Project not found. Please try again."
                )
                return
            
            # Create progress bar
            total_milestones = len(project.milestones)
            completed_milestones = len([m for m in project.milestones if m.get("completed")])
            progress = (completed_milestones / total_milestones) * 100 if total_milestones > 0 else 0
            progress_bar = "█" * int(progress/10) + "░" * (10 - int(progress/10))
            
            message = (
                f"🎵 Project: {project.title}\n\n"
                f"Status: {project.status.title()}\n"
                f"Progress: {progress_bar} {progress:.1f}%\n"
                f"Budget: ${project.budget:,.2f}\n"
                f"Team: {len(project.team_members)} members\n\n"
                "Milestones:\n"
            )
            
            for milestone in project.milestones:
                status = "✅" if milestone.get("completed") else "⏳"
                message += f"{status} {milestone['title']}\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("Update Status", callback_data=f"project_status_{project_id}"),
                    InlineKeyboardButton("Edit Budget", callback_data=f"project_budget_{project_id}")
                ],
                [
                    InlineKeyboardButton("Manage Team", callback_data=f"project_team_{project_id}"),
                    InlineKeyboardButton("Milestones", callback_data=f"project_milestones_{project_id}")
                ],
                [
                    InlineKeyboardButton("View Analytics", callback_data=f"project_analytics_{project_id}"),
                    InlineKeyboardButton("« Back to Projects", callback_data="projects_list")
                ]
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
            project = self.projects.get(project_id)
            if not project:
                await update.callback_query.edit_message_text(
                    "Project not found. Please try again."
                )
                return
            
            if action == "view":
                message = f"🎯 Milestones for {project.title}:\n\n"
                keyboard = []
                
                for i, milestone in enumerate(project.milestones):
                    status = "✅" if milestone.get("completed") else "⏳"
                    message += f"{status} {milestone['title']}\n"
                    if not milestone.get("completed"):
                        keyboard.append([
                            InlineKeyboardButton(
                                f"Complete: {milestone['title']}",
                                callback_data=f"project_milestone_complete_{project_id}_{i}"
                            )
                        ])
                
                keyboard.append([InlineKeyboardButton("Add Milestone", callback_data=f"project_milestone_add_{project_id}")])
                keyboard.append([InlineKeyboardButton("« Back", callback_data=f"project_manage_{project_id}")])
                
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            elif action == "add":
                context.user_data["adding_milestone"] = project_id
                await update.callback_query.edit_message_text(
                    "Please enter the milestone title and due date in this format:\n"
                    "<title> | <due_date>\n\n"
                    "Example:\n"
                    "Complete Recording | 2024-03-01"
                )
                
            elif action.startswith("complete_"):
                index = int(action.split("_")[1])
                project.milestones[index]["completed"] = True
                project.milestones[index]["completed_date"] = datetime.now()
                
                # Check if all milestones are completed
                if all(m.get("completed") for m in project.milestones):
                    project.status = "completed"
                
                await self._show_project_management(update, context, project_id)
                
        except Exception as e:
            logger.error(f"Error handling milestone action: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error managing milestones. Please try again."
            )

    async def _handle_team_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: str, action: str) -> None:
        """Handle team-related actions."""
        try:
            project = self.projects.get(project_id)
            if not project:
                await update.callback_query.edit_message_text(
                    "Project not found. Please try again."
                )
                return
            
            if action == "view":
                message = f"👥 Team for {project.title}:\n\n"
                keyboard = []
                
                if project.team_members:
                    for member in project.team_members:
                        message += (
                            f"• {member['name']}\n"
                            f"  Role: {member['role']}\n"
                            f"  Status: {member['status']}\n\n"
                        )
                        keyboard.append([
                            InlineKeyboardButton(
                                f"Manage {member['name']}",
                                callback_data=f"project_team_manage_{project_id}_{member['id']}"
                            )
                        ])
                else:
                    message += "No team members yet.\n\n"
                
                keyboard.append([InlineKeyboardButton("Add Member", callback_data=f"project_team_add_{project_id}")])
                keyboard.append([InlineKeyboardButton("« Back", callback_data=f"project_manage_{project_id}")])
                
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            elif action == "add":
                # Show available roles
                keyboard = []
                for role in project.required_roles:
                    if not any(m["role"] == role for m in project.team_members):
                        keyboard.append([
                            InlineKeyboardButton(
                                f"Add {role}",
                                callback_data=f"project_team_add_role_{project_id}_{role}"
                            )
                        ])
                
                keyboard.append([InlineKeyboardButton("Custom Role", callback_data=f"project_team_add_custom_{project_id}")])
                keyboard.append([InlineKeyboardButton("« Back", callback_data=f"project_team_view_{project_id}")])
                
                await update.callback_query.edit_message_text(
                    f"Select a role to add to {project.title}:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            elif action.startswith("add_role_"):
                role = action.replace("add_role_", "")
                context.user_data["adding_team_member"] = {
                    "project_id": project_id,
                    "role": role
                }
                await update.callback_query.edit_message_text(
                    f"Please enter the team member details for {role}:\n"
                    "<name> | <email> | <rate>\n\n"
                    "Example:\n"
                    "John Smith | john@example.com | 50"
                )
                
            elif action.startswith("manage_"):
                member_id = action.split("_")[1]
                member = next((m for m in project.team_members if m["id"] == member_id), None)
                
                if member:
                    keyboard = [
                        [
                            InlineKeyboardButton("Update Rate", callback_data=f"project_team_rate_{project_id}_{member_id}"),
                            InlineKeyboardButton("Change Role", callback_data=f"project_team_role_{project_id}_{member_id}")
                        ],
                        [
                            InlineKeyboardButton("Remove Member", callback_data=f"project_team_remove_{project_id}_{member_id}"),
                            InlineKeyboardButton("« Back", callback_data=f"project_team_view_{project_id}")
                        ]
                    ]
                    
                    await update.callback_query.edit_message_text(
                        f"Manage team member: {member['name']}\n\n"
                        f"Role: {member['role']}\n"
                        f"Rate: ${member['rate']}/hour\n"
                        f"Status: {member['status']}\n\n"
                        "Choose an action:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                
        except Exception as e:
            logger.error(f"Error handling team action: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error managing team members. Please try again."
            ) 