from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    PicklePersistence,
    BasePersistence
)
from artist_manager_agent.agent import ArtistManagerAgent
from artist_manager_agent.models import (
    ArtistProfile,
    Task,
    Event,
    Contract,
    FinancialRecord,
    PaymentRequest,
    PaymentMethod,
    PaymentStatus,
    Project,
    CollaboratorProfile,
    CollaboratorRole,
    Track,
    MasteringPreset,
    DistributionPlatform
)
from artist_manager_agent.onboarding import (
    OnboardingWizard,
    AWAITING_NAME,
    AWAITING_MANAGER_NAME,
    AWAITING_GENRE,
    AWAITING_SUBGENRE,
    AWAITING_STYLE_DESCRIPTION,
    AWAITING_INFLUENCES,
    AWAITING_CAREER_STAGE,
    AWAITING_GOALS,
    AWAITING_GOAL_TIMELINE,
    AWAITING_STRENGTHS,
    AWAITING_IMPROVEMENTS,
    AWAITING_ACHIEVEMENTS,
    AWAITING_SOCIAL_MEDIA,
    AWAITING_STREAMING_PROFILES,
    CONFIRM_PROFILE,
    EDIT_CHOICE,
    EDIT_SECTION
)
from artist_manager_agent.log import logger, log_event
import uuid
import logging
import asyncio
from functools import partial
import psutil
import sys
import os
import json
import shutil
import pickle
from pathlib import Path

class RobustPersistence(PicklePersistence):
    """Custom persistence handler with backup and recovery mechanisms."""
    
    def __init__(self, filepath: str, backup_count: int = 3):
        super().__init__(filepath)
        self.backup_count = backup_count
        self.backup_dir = Path(filepath).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    async def _backup_data(self):
        """Create a backup of the current persistence file."""
        try:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"persistence_backup_{current_time}.pickle"
            
            # Create new backup
            shutil.copy2(self.filepath, backup_path)
            
            # Remove old backups if we exceed backup_count
            backups = sorted(self.backup_dir.glob("persistence_backup_*.pickle"))
            while len(backups) > self.backup_count:
                backups[0].unlink()
                backups = backups[1:]
                
            logger.info(f"Created persistence backup: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create persistence backup: {str(e)}")
    
    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Override to add backup after update."""
        await super().update_user_data(user_id, data)
        await self._backup_data()
        
    async def _load_fallback(self) -> Optional[Dict]:
        """Try to load from the most recent backup if main file fails."""
        try:
            backups = sorted(self.backup_dir.glob("persistence_backup_*.pickle"), reverse=True)
            for backup in backups:
                try:
                    with open(backup, "rb") as f:
                        data = pickle.load(f)
                    logger.info(f"Successfully loaded data from backup: {backup}")
                    return data
                except:
                    continue
        except Exception as e:
            logger.error(f"Failed to load from backups: {str(e)}")
        return None
        
    async def load_data(self) -> None:
        """Override to add fallback loading."""
        try:
            await super().load_data()
        except Exception as e:
            logger.error(f"Failed to load persistence data: {str(e)}")
            # Try loading from backup
            data = await self._load_fallback()
            if data:
                self.user_data = data.get("user_data", {})
                self.chat_data = data.get("chat_data", {})
                self.bot_data = data.get("bot_data", {})
                self.callback_data = data.get("callback_data", {})
                self.conversations = data.get("conversations", {})
            else:
                logger.warning("Could not load data from main file or backups. Starting fresh.")
                self.user_data = {}
                self.chat_data = {}
                self.bot_data = {}
                self.callback_data = {}
                self.conversations = {}

class ArtistManagerBot:
    def __init__(
        self,
        telegram_token: str = None,
        artist_profile: ArtistProfile = None,
        openai_api_key: str = None,
        model: str = "gpt-3.5-turbo",
        db_url: str = "sqlite:///artist_manager.db"
    ):
        """Initialize the bot."""
        self.token = telegram_token
        self.persistence = RobustPersistence(
            filepath="data/bot_persistence/persistence.pickle",
            backup_count=3
        )
        
        # Initialize agent and onboarding wizard
        self.agent = ArtistManagerAgent(
            artist_profile=artist_profile,
            openai_api_key=openai_api_key,
            model=model,
            db_url=db_url
        ) if artist_profile and openai_api_key else None
        
        self.onboarding = OnboardingWizard(self)
        self._is_running = False
        self._auto_mode = False
        
    def register_handlers(self, application: Application) -> None:
        """Register all command handlers."""
        # Onboarding conversation handler must be registered first
        application.add_handler(self.onboarding.get_conversation_handler())
        
        # Core commands
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("goals", self.goals))
        application.add_handler(CommandHandler("tasks", self.tasks))
        application.add_handler(CommandHandler("events", self.events))
        application.add_handler(CommandHandler("contracts", self.contracts))
        
        # Auto mode and project handlers
        application.add_handler(CommandHandler("auto", self.toggle_auto_mode))
        application.add_handler(CommandHandler("newproject", self.create_project))
        
        # Error handler
        application.add_error_handler(self.error_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        try:
            user_id = update.effective_user.id
            if not context.user_data.get("profile_confirmed"):
                # Start onboarding if no confirmed profile
                await update.message.reply_text(
                    "Welcome! Let's set up your artist profile. "
                    "I'll ask you a series of questions to get to know you better."
                )
                return await self.onboarding.start_onboarding(update, context)
            else:
                # Show dashboard for existing users
                await update.message.reply_text(
                    f"Welcome back! Here are your available commands:\n"
                    f"/goals - View and manage your goals\n"
                    f"/tasks - View and manage your tasks\n"
                    f"/events - View and manage your events\n"
                    f"/contracts - View and manage your contracts\n"
                    f"/auto - Toggle autonomous mode\n"
                    f"/help - Show all available commands"
                )
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}")
            await update.message.reply_text(
                "Sorry, I encountered an error. Please try again."
            )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        help_message = (
            "🎵 Available Commands:\n\n"
            "Project Management:\n"
            "/projects - View all projects\n"
            "/newproject - Create new project\n"
            "/milestones - View project milestones\n\n"
            "Team Management:\n"
            "/team - View team members\n"
            "/addmember - Add team member\n"
            "/avail - Check team availability\n\n"
            "Music Services:\n"
            "/releases - Manage releases\n"
            "/master - Submit track for mastering\n"
            "/stats - View platform statistics\n\n"
            "Task Management:\n"
            "/tasks - View tasks\n"
            "/newtask - Create new task\n\n"
            "Financial Management:\n"
            "/finances - View finances\n"
            "/pay - Request payment\n"
            "/checkpay - Check payment status\n"
            "/payments - List all payments\n\n"
            "Event Management:\n"
            "/events - View events\n"
            "/newevent - Create new event\n\n"
            "Contract Management:\n"
            "/contracts - View contracts\n"
            "/newcontract - Create new contract\n\n"
            "AI Features:\n"
            "/auto - Toggle autonomous mode\n"
            "/suggest - Get AI suggestion\n\n"
            "Other:\n"
            "/goals - View career goals\n"
            "/health - Check health status\n"
            "/analytics - View analytics"
        )
        await update.message.reply_text(help_message)

    async def goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /goals command."""
        goals = self.agent.artist_profile.goals
        goals_message = "🎯 Career Goals:\n\n" + "\n".join(f"• {goal}" for goal in goals)
        await update.message.reply_text(goals_message)

    async def tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for viewing tasks."""
        try:
            tasks = await self.agent.get_tasks()
            if not tasks:
                await update.message.reply_text("No tasks found.")
                return

            response = "✅ Tasks:\n\n"
            for task in sorted(tasks, key=lambda t: t.priority):
                response += (
                    f"📌 {task.title}\n"
                    f"Priority: {'❗' * task.priority}\n"
                    f"Status: {task.status}\n"
                    f"Assigned to: {task.assigned_to}\n"
                    f"Deadline: {task.deadline.strftime('%Y-%m-%d')}\n"
                    f"Description: {task.description}\n\n"
                )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error retrieving tasks: {str(e)}")

    async def events(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for viewing events."""
        try:
            # Get date range from arguments or default to next 30 days
            start_date = datetime.now()
            end_date = start_date + timedelta(days=30)
            if context.args:
                try:
                    if len(context.args) >= 2:
                        start_date = datetime.strptime(context.args[0], '%Y-%m-%d')
                        end_date = datetime.strptime(context.args[1], '%Y-%m-%d')
                    else:
                        end_date = datetime.strptime(context.args[0], '%Y-%m-%d')
                except ValueError:
                    await update.message.reply_text("Invalid date format. Use YYYY-MM-DD")
                    return

            events = await self.agent.get_events_in_range(start_date, end_date)
            if not events:
                await update.message.reply_text("No events found in the specified date range.")
                return

            response = f"📅 Events ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}):\n\n"
            for event in sorted(events, key=lambda e: e.date):
                response += (
                    f"🎯 {event.title}\n"
                    f"Type: {event.type}\n"
                    f"Date: {event.date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Venue: {event.venue}\n"
                    f"Capacity: {event.capacity}\n"
                    f"Budget: ${event.budget:,.2f}\n"
                    f"Status: {event.status}\n\n"
                )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error retrieving events: {str(e)}")

    async def contracts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for viewing contracts."""
        try:
            contracts = await self.agent.get_contracts()
            if not contracts:
                await update.message.reply_text("No contracts found.")
                return

            response = "📄 Contracts:\n\n"
            for contract in sorted(contracts, key=lambda c: c.expiration):
                response += (
                    f"📝 {contract.title}\n"
                    f"Status: {contract.status}\n"
                    f"Parties: {', '.join(contract.parties)}\n"
                    f"Value: ${contract.value:,.2f}\n"
                    f"Expiration: {contract.expiration.strftime('%Y-%m-%d')}\n\n"
                )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error retrieving contracts: {str(e)}")

    async def toggle_auto_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /auto command."""
        if not hasattr(self, '_auto_mode'):
            self._auto_mode = False
        
        self._auto_mode = not self._auto_mode
        status = "enabled" if self._auto_mode else "disabled"
        
        if self._auto_mode:
            # Get current goals and state
            goals = self.agent.artist_profile.goals if self.agent else []
            current_state = await self.agent.get_current_state() if self.agent else {}
            
            await update.message.reply_text(
                f"🤖 Autonomous mode {status}\n\n"
                f"Current goals:\n" + 
                "\n".join([f"• {goal}" for goal in goals]) if goals else "No goals set yet."
            )
        else:
            await update.message.reply_text(f"🤖 Autonomous mode {status}")

    async def _run_autonomous_mode(
        self,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Run the autonomous mode loop."""
        try:
            while self._auto_mode:
                # Get current goals and state
                goals = self.agent.artist_profile.goals
                current_state = await self.agent.get_current_state()
                
                # Create plans for each goal if needed
                for goal in goals:
                    plan = await self.agent.ai_handler.create_goal_plan(
                        self.agent.artist_profile,
                        goal,
                        current_state
                    )
                    
                    # Get next step
                    step = await self.agent.ai_handler.get_next_step(
                        plan.id,
                        current_state
                    )
                    
                    if step:
                        # Notify user of planned action
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"🎯 Working on goal: {goal}\n\n"
                                f"Next action: {step.action}\n"
                                f"Priority: {'⭐' * step.priority}\n"
                                f"Estimated duration: {step.estimated_duration}\n\n"
                                "I'll keep you updated on the progress."
                        )
                        
                        # Execute step
                        result = await self.agent.ai_handler.execute_step(
                            step,
                            self.agent,
                            {
                                "profile": self.agent.artist_profile.dict(),
                                "goal": goal,
                                "plan": plan.dict()
                            }
                        )
                        
                        # Report result
                        if result.success:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"✅ Action completed successfully!\n\n"
                                    f"Action: {step.action}\n"
                                    f"Result: {result.output.get('message', 'Completed')}\n\n"
                                    "I'll continue working on the next steps."
                            )
                        else:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Action encountered an issue:\n\n"
                                    f"Action: {step.action}\n"
                                    f"Error: {result.output.get('error', 'Unknown error')}\n\n"
                                    "I'll adjust my approach and try alternative steps."
                            )
                        
                        # Check if goal is achieved
                        if await self.agent.ai_handler._check_goal_achieved(goal, current_state):
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"🎉 Goal achieved: {goal}\n\n"
                                    "I'll now focus on your other goals or maintaining this achievement."
                            )
                    
                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute
                
        except Exception as e:
            logger.error(f"Error in autonomous mode: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Autonomous mode encountered an error and has been disabled.\n\n"
                    f"Error: {str(e)}\n\n"
                    "You can try re-enabling it with /auto."
            )
            self._auto_mode = False

    async def suggest_next_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /suggest command."""
        try:
            # Get current state and goals
            current_state = await self.agent.get_current_state()
            goals = self.agent.artist_profile.goals
            
            # Create a plan for the most important goal
            plan = await self.agent.ai_handler.create_goal_plan(
                self.agent.artist_profile,
                goals[0],
                current_state
            )
            
            # Get next step
            step = await self.agent.ai_handler.get_next_step(
                plan.id,
                current_state
            )
            
            if step:
                # Create detailed suggestion message
                suggestion = (
                    f"🤔 Here's what I suggest:\n\n"
                    f"Goal: {goals[0]}\n\n"
                    f"Recommended action: {step.action}\n"
                    f"Priority: {'⭐' * step.priority}\n"
                    f"Estimated time: {step.estimated_duration}\n\n"
                    f"This will help by:\n"
                    f"• Moving us closer to your goal\n"
                    f"• {step.success_criteria.get('impact', 'Improving your career progress')}\n\n"
                    "Would you like me to execute this action? Use /auto to enable autonomous mode."
                )
                
                await update.message.reply_text(suggestion)
            else:
                await update.message.reply_text(
                    "I don't have any specific suggestions right now. "
                    "This usually means we're on track with your current goals."
                )
                
        except Exception as e:
            logger.error(f"Error suggesting action: {str(e)}")
            await update.message.reply_text(
                "Sorry, I encountered an error while generating suggestions. "
                "Please try again later."
            )

    async def view_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /analytics command."""
        try:
            team_analytics = await self.agent.get_team_analytics()
            project_analytics = await self.agent.get_project_analytics("all")
            payment_analytics = await self.agent.payment_manager.get_payment_analytics(None, None)
            
            analytics_message = (
                "📈 Analytics Overview:\n\n"
                f"Team Performance:\n"
                f"• Active Projects: {team_analytics['active_projects']}\n"
                f"• Completed Tasks: {team_analytics['completed_tasks']}\n"
                f"• Team Utilization: {team_analytics['utilization']}%\n\n"
                f"Financial Overview:\n"
                f"• Total Revenue: ${payment_analytics['total_volume']:,.2f}\n"
                f"• Success Rate: {(payment_analytics['successful_payments'] / (payment_analytics['successful_payments'] + payment_analytics['failed_payments'])) * 100:.1f}%\n"
                f"• Average Processing Time: {payment_analytics['average_processing_time'] / 60:.1f} minutes\n\n"
                f"Project Metrics:\n"
                f"• On-time Completion: {project_analytics['on_time_completion']}%\n"
                f"• Budget Adherence: {project_analytics['budget_adherence']}%\n"
                f"• Team Satisfaction: {project_analytics['team_satisfaction']}%"
            )
            
            await update.message.reply_text(analytics_message)
        except Exception as e:
            await update.message.reply_text(f"Error getting analytics: {str(e)}")

    async def create_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for creating a new project."""
        try:
            # Check if we have all required arguments
            if not context.args or len(context.args) < 3:
                await update.message.reply_text(
                    "Usage: /newproject <name> <description> <budget>\n"
                    "Example: /newproject 'Album Release' 'New album production' 10000"
                )
                return

            name = context.args[0]
            description = " ".join(context.args[1:-1])
            budget = float(context.args[-1])

            project = Project(
                name=name,
                description=description,
                start_date=datetime.now(),
                budget=budget,
                status="active"
            )

            project_id = await self.agent.add_project(project)
            await update.message.reply_text(
                f"✅ Project created successfully!\n"
                f"Name: {name}\n"
                f"Description: {description}\n"
                f"Budget: ${budget:,.2f}\n"
                f"ID: {project_id}"
            )
        except ValueError as e:
            await update.message.reply_text(f"Error: {str(e)}")
        except Exception as e:
            await update.message.reply_text(f"An error occurred: {str(e)}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the bot."""
        logger.error(f"Update {update} caused error: {context.error}")
        
        # Log the error
        error_msg = f"An error occurred: {str(context.error)}"
        
        try:
            # Notify user of error
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "Sorry, an error occurred while processing your request. Please try again later."
                )
                
            # Try to save current state if possible
            if hasattr(context, "application") and hasattr(context.application, "persistence"):
                try:
                    await context.application.persistence._backup_data()
                    logger.info("Successfully backed up data after error")
                except Exception as backup_error:
                    logger.error(f"Failed to backup data after error: {str(backup_error)}")
                    
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")
            
        # Re-raise the error for the application to handle
        raise context.error

    async def run(self):
        """Run the bot."""
        try:
            # Initialize application
            application = Application.builder().token(self.token).persistence(self.persistence).build()
            
            # Register handlers
            self.register_handlers(application)
            
            # Start the bot
            logger.info("Starting bot with polling...")
            await application.initialize()
            await application.start()
            await application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Error in bot.run: {str(e)}")
            raise
        finally:
            # Ensure proper cleanup
            if 'application' in locals():
                logger.info("Stopping application...")
                await application.stop()
                await application.shutdown()
            logger.info("Bot shutdown complete.")

    async def stop(self):
        """Stop the bot gracefully."""
        self._is_running = False
        logger.info("Bot stop requested.")

    async def run(self):
        """Run the bot."""
        if not self.token:
            raise ValueError("Bot token not provided")
            
        try:
            logger.info("Initializing ArtistManagerBot")
            self._is_running = True

            # Initialize application with our robust persistence
            application = Application.builder() \
                .token(self.token) \
                .persistence(self.persistence) \
                .build()

            # Add handlers
            self.register_handlers(application)
            
            # Add error handler
            application.add_error_handler(self.error_handler)
            
            logger.info("Bot initialization completed")
            logger.info("Starting polling...")
            
            # Start polling in non-blocking mode
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            
            # Keep the bot running
            while self._is_running:
                await asyncio.sleep(1)
                
            # Cleanup
            await application.stop()
            await application.shutdown()
            
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            self._is_running = False
            raise
        finally:
            logger.info("Shutdown complete.") 