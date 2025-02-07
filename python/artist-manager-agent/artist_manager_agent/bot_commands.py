from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import json

# Conversation states
(
    AWAITING_GOAL,
    AWAITING_GOAL_DEADLINE,
    AWAITING_TASK_TITLE,
    AWAITING_TASK_DESCRIPTION,
    AWAITING_TASK_ASSIGNEE,
    AWAITING_TASK_DEADLINE,
    AWAITING_TEAM_ROLE,
    AWAITING_TEAM_SKILLS,
    AWAITING_RELEASE_TITLE,
    AWAITING_RELEASE_DATE,
    AWAITING_RELEASE_TYPE,
    AWAITING_HEALTH_NOTE,
) = range(12)

class BotCommandHandler:
    def __init__(self, agent: Any):
        self.agent = agent
        self.conversation_state: Dict[str, Dict[str, Any]] = {}

    def _get_user_state(self, user_id: str) -> Dict[str, Any]:
        """Get or create user state."""
        if user_id not in self.conversation_state:
            self.conversation_state[user_id] = {}
        return self.conversation_state[user_id]

    def _clear_user_state(self, user_id: str) -> None:
        """Clear user state."""
        if user_id in self.conversation_state:
            del self.conversation_state[user_id]

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        welcome_message = f"""
🎵 Welcome to your AI Artist Manager!
I'm here to help manage {self.agent.artist.name}'s career.

Quick Stats:
- Genre: {self.agent.artist.genre}
- Stage: {self.agent.artist.career_stage}
- Active Tasks: {len(self.agent.tasks)}
- Team Size: {len(self.agent.team)}

Use /help to see available commands.
        """
        await update.message.reply_text(welcome_message)

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        commands = """
🎯 Available Commands:

Career Management:
/goals - View and update career goals
/strategy - Get career strategy
/progress - Check progress on goals

Task Management:
/tasks - View and manage tasks
/schedule - View and manage schedule
/deadline - Set or view deadlines

Team Management:
/team - View team members
/assign - Assign tasks to team members
/hire - Scout new team members

Content & Production:
/master - AI master a track
/release - Plan release strategy
/content - Plan content strategy

Business:
/finance - Financial management
/deals - View and evaluate deals
/stats - View performance stats

Support:
/guidance - Get career guidance
/crisis - Get crisis management help
/health - Track artist wellbeing

Use /help <command> for detailed info about any command.
        """
        await update.message.reply_text(commands)

    async def handle_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tasks command with inline keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("View Tasks", callback_data="tasks_view"),
                InlineKeyboardButton("Add Task", callback_data="tasks_add")
            ],
            [
                InlineKeyboardButton("By Priority", callback_data="tasks_priority"),
                InlineKeyboardButton("By Deadline", callback_data="tasks_deadline")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Task Management:", reply_markup=reply_markup)

    async def handle_master(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /master command for AI mastering."""
        if not context.args:
            await update.message.reply_text(
                "Please provide the track URL:\n/master <track_url> [options]\n\n"
                "Options:\n"
                "- loudness=<value> (default: -14.0)\n"
                "- dynamics=<value> (default: 8.0)\n"
                "- quality=<high|medium|low> (default: high)"
            )
            return

        track_url = context.args[0]
        options = {}
        for arg in context.args[1:]:
            if "=" in arg:
                key, value = arg.split("=")
                options[f"target_{key}"] = float(value) if value.replace(".", "").isdigit() else value

        mastering = self.agent.services.get("mastering")
        if not mastering:
            await update.message.reply_text("AI mastering service not available.")
            return

        try:
            # Start mastering job
            job = await mastering.start_mastering(track_url, options)
            await update.message.reply_text(f"Mastering job started. ID: {job['id']}")

            # Poll for completion
            while True:
                status = await mastering.get_mastering_status(job['id'])
                if status['status'] == 'completed':
                    download_url = await mastering.get_mastered_track(job['id'])
                    comparison = await mastering.compare_versions(track_url, download_url)
                    
                    report = f"""
✨ Mastering Complete!

Download: {download_url}

Improvements:
- Loudness: {comparison['loudness_improvement']}dB
- Clarity: {comparison['clarity_improvement']}%
- Dynamic Range: {comparison['dynamics_improvement']}dB

Quality Score: {comparison['quality_score']}/10
                    """
                    await update.message.reply_text(report)
                    break
                elif status['status'] == 'failed':
                    await update.message.reply_text("❌ Mastering failed. Please try again.")
                    break
                
                await asyncio.sleep(5)
        except Exception as e:
            await update.message.reply_text(f"Error during mastering: {str(e)}")

    async def handle_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /schedule command with calendar view."""
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        
        # Generate week view
        week_view = "📅 This Week's Schedule:\n\n"
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_tasks = [
                task for task in self.agent.tasks 
                if task.deadline.date() == day.date()
            ]
            
            week_view += f"{day.strftime('%A (%m/%d)')}:\n"
            if day_tasks:
                for task in sorted(day_tasks, key=lambda x: x.priority):
                    week_view += f"- {task.title} ({task.assigned_to})\n"
            else:
                week_view += "- No tasks scheduled\n"
            week_view += "\n"

        keyboard = [
            [
                InlineKeyboardButton("Previous Week", callback_data="schedule_prev"),
                InlineKeyboardButton("Next Week", callback_data="schedule_next")
            ],
            [
                InlineKeyboardButton("Add Event", callback_data="schedule_add"),
                InlineKeyboardButton("View All", callback_data="schedule_all")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(week_view, reply_markup=reply_markup)

    async def handle_guidance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /guidance command."""
        if not context.args:
            await update.message.reply_text(
                "Please describe the situation you need guidance with:\n"
                "/guidance <your situation>"
            )
            return

        situation = " ".join(context.args)
        guidance = await self.agent.provide_guidance(situation)
        await update.message.reply_text(f"🤔 Here's my advice:\n\n{guidance}")

    async def handle_crisis(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /crisis command."""
        if not context.args:
            await update.message.reply_text(
                "Please describe the crisis situation:\n"
                "/crisis <situation description>"
            )
            return

        situation = " ".join(context.args)
        response = await self.agent.manage_crisis(situation)
        await update.message.reply_text(
            f"🚨 Crisis Management Plan:\n\n{response['strategy']}"
        )

    async def handle_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /goals command."""
        keyboard = [
            [
                InlineKeyboardButton("View Goals", callback_data="goals_view"),
                InlineKeyboardButton("Add Goal", callback_data="goals_add")
            ],
            [
                InlineKeyboardButton("Track Progress", callback_data="goals_progress"),
                InlineKeyboardButton("Edit Goals", callback_data="goals_edit")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        goals_text = "🎯 Current Goals:\n\n"
        for goal in self.agent.artist.goals:
            goals_text += f"• {goal}\n"
        
        await update.message.reply_text(goals_text, reply_markup=reply_markup)
        return ConversationHandler.END

    async def handle_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /strategy command."""
        strategy = await self.agent.create_strategy()
        
        # Format strategy nicely
        strategy_text = "📋 Strategic Plan:\n\n"
        for i, step in enumerate(strategy["strategy"], 1):
            if step.strip():  # Skip empty lines
                strategy_text += f"{i}. {step.strip()}\n"
        
        keyboard = [
            [
                InlineKeyboardButton("Convert to Tasks", callback_data="strategy_tasks"),
                InlineKeyboardButton("Share with Team", callback_data="strategy_share")
            ],
            [
                InlineKeyboardButton("Export Plan", callback_data="strategy_export"),
                InlineKeyboardButton("Track Progress", callback_data="strategy_track")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(strategy_text, reply_markup=reply_markup)

    async def handle_team(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /team command."""
        keyboard = [
            [
                InlineKeyboardButton("View Team", callback_data="team_view"),
                InlineKeyboardButton("Add Member", callback_data="team_add")
            ],
            [
                InlineKeyboardButton("Performance", callback_data="team_performance"),
                InlineKeyboardButton("Schedule", callback_data="team_schedule")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        team_text = "👥 Current Team:\n\n"
        for member in self.agent.team:
            team_text += f"• {member.name} - {member.role}\n"
            team_text += f"  Skills: {', '.join(member.skills)}\n"
            if member.availability:
                team_text += f"  Available: {next(iter(member.availability.items()))[0]}\n"
            team_text += "\n"
        
        await update.message.reply_text(team_text, reply_markup=reply_markup)

    async def handle_release(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /release command."""
        keyboard = [
            [
                InlineKeyboardButton("Plan Release", callback_data="release_plan"),
                InlineKeyboardButton("Track Progress", callback_data="release_track")
            ],
            [
                InlineKeyboardButton("Marketing Plan", callback_data="release_marketing"),
                InlineKeyboardButton("Budget", callback_data="release_budget")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🎵 Release Management\nWhat would you like to do?",
            reply_markup=reply_markup
        )

    async def handle_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /health command."""
        keyboard = [
            ["😊 Feeling Great", "😐 Okay", "😔 Not Great"],
            ["😴 Tired", "😤 Stressed", "🤒 Unwell"],
            ["📝 Custom Note"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "How are you feeling today?",
            reply_markup=reply_markup
        )
        return AWAITING_HEALTH_NOTE

    async def handle_health_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle health note input."""
        note = update.message.text
        await self.agent.update_health_notes(note)
        
        response = await self.agent.provide_guidance(
            f"The artist reported feeling {note.lower()}. Provide supportive guidance."
        )
        
        await update.message.reply_text(
            f"Thank you for sharing. I've noted that you're feeling {note}.\n\n"
            f"💭 Here's some guidance:\n{response}"
        )
        return ConversationHandler.END

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()

        action, subaction = query.data.split("_") if "_" in query.data else (query.data, None)

        handlers = {
            "tasks": self._handle_tasks_callback,
            "schedule": self._handle_schedule_callback,
            "goals": self._handle_goals_callback,
            "team": self._handle_team_callback,
            "release": self._handle_release_callback,
            "strategy": self._handle_strategy_callback
        }

        if action in handlers:
            await handlers[action](query, subaction)

    async def _handle_tasks_callback(self, query: Any, subaction: str) -> None:
        """Handle tasks-related callbacks."""
        if subaction == "view":
            tasks_view = "📋 Current Tasks:\n\n"
            for task in sorted(self.agent.tasks, key=lambda x: x.priority):
                tasks_view += f"• {task.title}\n"
                tasks_view += f"  Assigned to: {task.assigned_to}\n"
                tasks_view += f"  Deadline: {task.deadline.strftime('%Y-%m-%d')}\n"
                tasks_view += f"  Status: {task.status}\n\n"
            
            await query.edit_message_text(tasks_view)

    async def _handle_schedule_callback(self, query: Any, subaction: str) -> None:
        """Handle schedule-related callbacks."""
        # Implementation similar to handle_schedule but with week navigation
        pass

    async def _handle_goals_callback(self, query: Any, subaction: str) -> None:
        """Handle goals-related callbacks."""
        if subaction == "view":
            goals_text = "🎯 Current Goals:\n\n"
            for goal in self.agent.artist.goals:
                goals_text += f"• {goal}\n"
            await query.edit_message_text(goals_text)
        elif subaction == "progress":
            # Calculate progress based on tasks and achievements
            progress_text = "📊 Goals Progress:\n\n"
            for goal in self.agent.artist.goals:
                # Simplified progress calculation
                related_tasks = [t for t in self.agent.tasks if goal.lower() in t.title.lower()]
                completed = len([t for t in related_tasks if t.status == "completed"])
                total = len(related_tasks) or 1
                progress = (completed / total) * 100
                progress_text += f"• {goal}\n"
                progress_text += f"  Progress: {progress:.1f}%\n"
                progress_text += f"  Tasks: {completed}/{total} completed\n\n"
            await query.edit_message_text(progress_text)

    async def _handle_team_callback(self, query: Any, subaction: str) -> None:
        """Handle team-related callbacks."""
        if subaction == "performance":
            perf_text = "📊 Team Performance:\n\n"
            for member in self.agent.team:
                perf_text += f"• {member.name} ({member.role})\n"
                for metric, value in member.performance_metrics.items():
                    perf_text += f"  {metric}: {value}\n"
                completed_tasks = len([
                    t for t in self.agent.tasks 
                    if t.assigned_to == member.name and t.status == "completed"
                ])
                perf_text += f"  Completed Tasks: {completed_tasks}\n\n"
            await query.edit_message_text(perf_text)

    async def _handle_release_callback(self, query: Any, subaction: str) -> None:
        """Handle release-related callbacks."""
        # Implementation similar to handle_release but with subaction handling
        pass

    async def _handle_strategy_callback(self, query: Any, subaction: str) -> None:
        """Handle strategy-related callbacks."""
        # Implementation similar to handle_strategy but with subaction handling
        pass 