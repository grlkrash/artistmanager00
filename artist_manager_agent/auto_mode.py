from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio
import json
from .models import ArtistProfile, Task
from .log import logger, log_error

class AutoMode:
    """Handles auto mode functionality for the bot."""
    
    def __init__(self, bot):
        self.bot = bot
        self._auto_mode = False
        self._auto_task = None
        self._default_settings = {
            "frequency": 3600,  # 1 hour
            "ai_level": "balanced",
            "notifications": "important",
            "task_limit": 5,
            "goal_check_interval": 86400,  # 24 hours
            "analytics_interval": 604800  # 7 days
        }

    async def show_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show auto mode options."""
        user_id = update.effective_user.id
        
        if not self.bot.get_user_profile(user_id):
            await update.message.reply_text(
                "Please complete your profile setup first with /start"
            )
            return
            
        keyboard = [
            [
                InlineKeyboardButton("Enable Auto Mode", callback_data="auto_enable"),
                InlineKeyboardButton("Disable Auto Mode", callback_data="auto_disable")
            ],
            [
                InlineKeyboardButton("Configure Settings", callback_data="auto_settings"),
                InlineKeyboardButton("View Status", callback_data="auto_status")
            ]
        ]
        
        await update.message.reply_text(
            "🤖 Auto Mode Settings\n\n"
            "Auto mode uses AI to help manage your career:\n"
            "• Automated task scheduling\n"
            "• Smart goal tracking\n"
            "• Proactive suggestions\n"
            "• Performance analytics\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Configure auto mode settings."""
        settings = context.user_data.get("auto_settings", self._default_settings)
        
        keyboard = [
            [
                InlineKeyboardButton("Every 1h", callback_data="auto_freq_1"),
                InlineKeyboardButton("Every 3h", callback_data="auto_freq_3"),
                InlineKeyboardButton("Every 6h", callback_data="auto_freq_6")
            ],
            [
                InlineKeyboardButton("Conservative AI", callback_data="auto_ai_conservative"),
                InlineKeyboardButton("Balanced AI", callback_data="auto_ai_balanced"),
                InlineKeyboardButton("Proactive AI", callback_data="auto_ai_proactive")
            ],
            [
                InlineKeyboardButton("All Notifications", callback_data="auto_notif_all"),
                InlineKeyboardButton("Important Only", callback_data="auto_notif_important"),
                InlineKeyboardButton("Minimal", callback_data="auto_notif_minimal")
            ],
            [
                InlineKeyboardButton("« Back", callback_data="auto_back")
            ]
        ]
        
        await update.message.reply_text(
            "⚙️ Auto Mode Configuration\n\n"
            "Current settings:\n"
            f"• Check frequency: Every {settings['frequency']//3600}h\n"
            f"• AI proactiveness: {settings['ai_level'].title()}\n"
            f"• Notification level: {settings['notifications'].title()}\n\n"
            "Select new settings:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle auto mode callback queries."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("auto_", "")
        
        if action == "enable":
            # Save current settings or use defaults
            if "auto_settings" not in context.user_data:
                context.user_data["auto_settings"] = self._default_settings.copy()
            
            self._auto_mode = True
            
            # Start background task if not running
            if not self._auto_task or self._auto_task.done():
                self._auto_task = asyncio.create_task(
                    self._process_tasks(update, context)
                )
            
            await query.edit_message_text(
                "🤖 Auto Mode Enabled\n\n"
                "I will now:\n"
                "• Monitor your goals and suggest tasks\n"
                "• Track project deadlines\n"
                "• Analyze performance metrics\n"
                "• Provide AI-powered insights\n\n"
                "Use /auto to change settings or disable"
            )
            
        elif action == "disable":
            self._auto_mode = False
            if self._auto_task:
                self._auto_task.cancel()
            
            await query.edit_message_text(
                "Auto mode has been disabled. Use /auto to re-enable."
            )
            
        elif action == "settings":
            await self.setup(update, context)
            
        elif action.startswith("freq_"):
            hours = int(action.split("_")[1])
            context.user_data["auto_settings"]["frequency"] = hours * 3600
            await self.show_options(update, context)
            
        elif action.startswith("ai_"):
            level = action.split("_")[1]
            context.user_data["auto_settings"]["ai_level"] = level
            await self.show_options(update, context)
            
        elif action.startswith("notif_"):
            level = action.split("_")[1]
            context.user_data["auto_settings"]["notifications"] = level
            await self.show_options(update, context)

    async def _process_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Background task for auto mode processing."""
        user_id = update.effective_user.id
        
        while self._auto_mode:
            try:
                # Get user profile and settings
                profile = self.bot.get_user_profile(user_id)
                settings = context.user_data.get("auto_settings", self._default_settings)
                
                if profile:
                    # Process goals and create tasks
                    await self._process_goals(update, context, profile)
                    
                    # Check project deadlines
                    await self._check_deadlines(update, context)
                    
                    # Analyze performance metrics
                    await self._analyze_metrics(update, context, profile)
                    
                    # Generate insights and suggestions
                    await self._generate_insights(update, context, profile)
                
                # Wait before next check based on settings
                freq = settings.get("frequency", self._default_settings["frequency"])
                await asyncio.sleep(freq)
                
            except Exception as e:
                logger.error(f"Error in auto mode processing: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _process_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE, profile: ArtistProfile) -> None:
        """Process goals and generate tasks."""
        goals = profile.goals if hasattr(profile, "goals") else []
        settings = context.user_data.get("auto_settings", self._default_settings)
        
        for goal in goals:
            try:
                # Get current progress
                progress = await self.bot.ai_handler.analyze_goal_progress(goal, profile)
                
                if progress < 100:  # Goal not completed
                    # Generate task suggestions
                    tasks = await self.bot.ai_handler.suggest_tasks_for_goal(goal, profile)
                    
                    if tasks:
                        # Filter based on AI level setting
                        ai_level = settings.get("ai_level", "balanced")
                        if ai_level == "conservative":
                            tasks = tasks[:1]  # Only most important task
                        elif ai_level == "balanced":
                            tasks = tasks[:3]  # Top 3 tasks
                        
                        # Create task buttons
                        keyboard = []
                        for task in tasks:
                            keyboard.append([
                                InlineKeyboardButton(
                                    f"Add: {task.title[:30]}...",
                                    callback_data=f"auto_task_{task.id}"
                                )
                            ])
                        keyboard.append([InlineKeyboardButton("Skip All", callback_data="auto_skip")])
                        
                        # Send suggestion based on notification settings
                        notif_level = settings.get("notifications", "important")
                        if notif_level == "all" or (notif_level == "important" and task.priority == "high"):
                            await update.message.reply_text(
                                f"🎯 Goal Progress Update: {goal.title}\n"
                                f"Current Progress: {progress}%\n\n"
                                "Suggested tasks to move forward:\n" +
                                "\n".join(f"• {task.title}" for task in tasks),
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
            
            except Exception as e:
                logger.error(f"Error processing goal {goal.title}: {str(e)}")

    async def _check_deadlines(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check project and task deadlines."""
        try:
            settings = context.user_data.get("auto_settings", self._default_settings)
            notif_level = settings.get("notifications", "important")
            
            # Check projects
            projects = await self.bot.team_manager.get_projects()
            for project in projects:
                if project.end_date:
                    days_remaining = (project.end_date - datetime.now()).days
                    
                    if (days_remaining <= 7 and notif_level in ["all", "important"]) or \
                       (days_remaining <= 3 and notif_level == "minimal"):
                        await update.message.reply_text(
                            f"⚠️ Project Deadline Alert\n\n"
                            f"Project: {project.title}\n"
                            f"Deadline: {project.end_date.strftime('%Y-%m-%d')}\n"
                            f"Days remaining: {days_remaining}\n\n"
                            f"Use /projects to view details",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("View Project", callback_data=f"project_view_{project.id}")
                            ]])
                        )
            
            # Check tasks
            tasks = await self.bot.team_manager.get_tasks()
            for task in tasks:
                if task.due_date:
                    days_remaining = (task.due_date - datetime.now()).days
                    
                    if (days_remaining <= 3 and notif_level in ["all", "important"]) or \
                       (days_remaining <= 1 and notif_level == "minimal"):
                        await update.message.reply_text(
                            f"⏰ Task Due Soon\n\n"
                            f"Task: {task.title}\n"
                            f"Due: {task.due_date.strftime('%Y-%m-%d')}\n"
                            f"Days remaining: {days_remaining}\n\n"
                            f"Use /tasks to view details",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("View Task", callback_data=f"task_view_{task.id}")
                            ]])
                        )
                        
        except Exception as e:
            logger.error(f"Error checking deadlines: {str(e)}")

    async def _analyze_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, profile: ArtistProfile) -> None:
        """Analyze performance metrics and generate reports."""
        try:
            settings = context.user_data.get("auto_settings", self._default_settings)
            
            # Check if it's time for analytics
            last_analysis = context.user_data.get("last_analytics_time", 0)
            if (datetime.now().timestamp() - last_analysis) < settings["analytics_interval"]:
                return
                
            # Gather metrics
            metrics = await self.bot.ai_handler.analyze_metrics(profile)
            
            if metrics:
                # Generate report
                report = (
                    "📊 Weekly Performance Report\n\n"
                    f"Social Media Growth: {metrics['social_growth']}%\n"
                    f"Streaming Performance: {metrics['streaming_growth']}%\n"
                    f"Project Completion Rate: {metrics['project_completion']}%\n"
                    f"Goal Progress: {metrics['goal_progress']}%\n\n"
                    "Key Insights:\n"
                )
                
                for insight in metrics['insights'][:3]:
                    report += f"• {insight}\n"
                
                # Add action buttons
                keyboard = []
                for action in metrics['suggested_actions'][:2]:
                    keyboard.append([
                        InlineKeyboardButton(action['title'], callback_data=f"metric_action_{action['id']}")
                    ])
                
                await update.message.reply_text(
                    report,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                # Update last analysis time
                context.user_data["last_analytics_time"] = datetime.now().timestamp()
                
        except Exception as e:
            logger.error(f"Error analyzing metrics: {str(e)}")

    async def _generate_insights(self, update: Update, context: ContextTypes.DEFAULT_TYPE, profile: ArtistProfile) -> None:
        """Generate AI insights and suggestions."""
        try:
            settings = context.user_data.get("auto_settings", self._default_settings)
            
            # Generate insights based on recent activity
            insights = await self.bot.ai_handler.generate_insights(profile)
            
            if insights and settings.get("notifications") != "minimal":
                # Format insights message
                message = "🤖 AI Insights\n\n"
                for category, items in insights.items():
                    message += f"*{category}*:\n"
                    for item in items[:2]:  # Show top 2 insights per category
                        message += f"• {item}\n"
                    message += "\n"
                
                # Add action buttons
                keyboard = []
                if insights.get("suggestions"):
                    for suggestion in insights["suggestions"][:2]:
                        keyboard.append([
                            InlineKeyboardButton(
                                suggestion["title"],
                                callback_data=f"insight_action_{suggestion['id']}"
                            )
                        ])
                
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}") 