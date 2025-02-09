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

class ArtistManagerBot:
    def __init__(
        self,
        token: str = None,
        agent: ArtistManagerAgent = None,
        artist_profile: ArtistProfile = None,
        openai_api_key: str = None,
        model: str = "gpt-3.5-turbo",
        db_url: str = "sqlite:///artist_manager.db",
        telegram_token: str = None,
        ai_mastering_key: str = None
    ):
        """Initialize the bot."""
        logger.info("Initializing ArtistManagerBot")
        logger.info(f"Bot token present: {bool(telegram_token or token)}")
        
        self.token = telegram_token or token
        if not self.token:
            raise ValueError("No Telegram token provided")

        if agent:
            self.agent = agent
        else:
            if not artist_profile or not openai_api_key:
                raise ValueError("Either agent or (artist_profile and openai_api_key) must be provided")
            self.agent = ArtistManagerAgent(
                artist_profile=artist_profile,
                openai_api_key=openai_api_key,
                model=model,
                db_url=db_url
            )

        self.team_manager = self.agent  # For compatibility with tests
        self.start_time = datetime.now()
        self._is_running = False
        
        # Initialize onboarding wizard
        self.onboarding = OnboardingWizard(self)
        logger.info("Bot initialization completed")

    @property
    def artist_profile(self) -> ArtistProfile:
        """Access the artist profile from the agent."""
        return self.agent.artist_profile
    
    @artist_profile.setter
    def artist_profile(self, profile: ArtistProfile):
        """Update the artist profile in the agent."""
        self.agent.artist_profile = profile

    async def _monitor_metrics(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Monitor process metrics as a background job."""
        try:
            # Collect metrics
            cpu_percent = psutil.Process().cpu_percent()
            memory_info = psutil.Process().memory_info()
            
            # Log metrics
            log_event("process_metrics", {
                "cpu_percent": cpu_percent,
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
            })
            
            # Check thresholds
            if cpu_percent > 80:
                logger.warning(f"High CPU usage: {cpu_percent}%")
            if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
                logger.warning("High memory usage")
                
        except Exception as e:
            logger.error(f"Error in process monitoring: {str(e)}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        
        # Check if user has a confirmed profile
        if (hasattr(self.agent, 'artist_profile') and 
            self.agent.artist_profile and 
            self.agent.artist_profile.name):  # Basic check if profile exists
            
            # Show dashboard with available commands
            dashboard_message = (
                f"👋 Welcome back, {self.agent.artist_profile.name}!\n\n"
                "Here's your Artist Manager Dashboard:\n\n"
                "🎵 Music Services:\n"
                "/releases - Manage releases\n"
                "/master - Submit track for mastering\n"
                "/stats - View platform statistics\n\n"
                "👥 Team Management:\n"
                "/team - View team members\n"
                "/addmember - Add team member\n"
                "/avail - Check availability\n\n"
                "📋 Project Management:\n"
                "/projects - View all projects\n"
                "/newproject - Create new project\n"
                "/milestones - View milestones\n\n"
                "✅ Task Management:\n"
                "/tasks - View tasks\n"
                "/newtask - Create new task\n\n"
                "💰 Financial Management:\n"
                "/finances - View finances\n"
                "/pay - Request payment\n"
                "/checkpay - Check payment status\n"
                "/payments - List all payments\n\n"
                "📅 Event Management:\n"
                "/events - View events\n"
                "/newevent - Create new event\n\n"
                "📄 Contract Management:\n"
                "/contracts - View contracts\n"
                "/newcontract - Create new contract\n\n"
                "🤖 AI Features:\n"
                "/auto - Toggle autonomous mode\n"
                "/suggest - Get AI suggestion\n\n"
                "📊 Analytics:\n"
                "/analytics - View analytics\n"
                "/health - Check health status\n\n"
                "Use /help to see this menu again."
            )
            await update.message.reply_text(dashboard_message)
            return
            
        # If no profile exists, start the onboarding wizard
        return await self.onboarding.start_onboarding(update, context)

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

    async def finances(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /finances command."""
        records = await self.agent.get_financial_records()
        if not records:
            await update.message.reply_text("No financial records found.")
            return
        
        finances_message = "💰 Financial Records:\n\n"
        total_income = sum(r.amount for r in records if r.type == "income")
        total_expenses = sum(r.amount for r in records if r.type == "expense")
        net_income = total_income - total_expenses
        
        finances_message += (
            f"Total Income: ${total_income:,.2f}\n"
            f"Total Expenses: ${total_expenses:,.2f}\n"
            f"Net Income: ${net_income:,.2f}\n\n"
            "Recent Transactions:\n"
        )
        
        for record in sorted(records, key=lambda x: x.date, reverse=True)[:5]:
            finances_message += (
                f"• {record.description}\n"
                f"  Type: {record.type}\n"
                f"  Amount: ${record.amount:,.2f}\n"
                f"  Date: {record.date.strftime('%Y-%m-%d')}\n\n"
            )
        await update.message.reply_text(finances_message)

    async def health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /health command."""
        notes = self.agent.artist_profile.health_notes
        if not notes:
            await update.message.reply_text("No health notes found.")
            return
        
        health_message = "🏥 Health Status:\n\n"
        for note in notes:
            health_message += f"• {note}\n"
        await update.message.reply_text(health_message)

    async def request_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request a payment from a collaborator."""
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "Usage: /pay <amount> <currency> <description>"
            )
            return

        try:
            amount = float(context.args[0])
            if amount <= 0:
                await update.message.reply_text(
                    "Error creating payment request: Amount must be positive"
                )
                return

            currency = context.args[1].upper()
            if currency not in ["USD", "EUR", "GBP"]:
                await update.message.reply_text(
                    "Error creating payment request: Invalid currency"
                )
                return

            description = " ".join(context.args[2:])
            payment_method = context.user_data.get("payment_method")
            
            if not payment_method:
                await update.message.reply_text(
                    "Please set up your payment method first using /setup_payment"
                )
                return

            payment = PaymentRequest(
                id=str(uuid.uuid4()),
                collaborator_id=str(update.effective_user.id),
                amount=amount,
                currency=currency,
                description=description,
                due_date=datetime.now() + timedelta(days=7),
                payment_method=payment_method,
                status=PaymentStatus.PENDING
            )

            await self.agent.add_payment_request(payment)
            await update.message.reply_text(
                f"Payment request created:\n"
                f"Amount: {amount} {currency}\n"
                f"Description: {description}\n"
                f"Payment ID: {payment.id}"
            )

        except ValueError as e:
            await update.message.reply_text(f"Error creating payment request: {str(e)}")

    async def check_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check the status of a payment."""
        if not context.args:
            await update.message.reply_text("Usage: /checkpay <payment_id>")
            return

        payment_id = context.args[0]
        try:
            status = await self.agent.check_payment_status(payment_id)
            if status:
                await update.message.reply_text(
                    f"Payment Status:\n"
                    f"Status: {status['status']}\n"
                    f"Paid: {'Yes' if status.get('paid', False) else 'No'}\n"
                    f"Amount Paid: {status.get('amount_paid', 0)} {status.get('currency', 'USD')}"
                )
            else:
                await update.message.reply_text("Error checking payment status: Payment not found")
        except Exception as e:
            await update.message.reply_text(f"Error checking payment status: {str(e)}")

    async def list_payments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all payment requests."""
        payments = await self.agent.get_payment_requests()
        if not payments:
            await update.message.reply_text("No payment requests found.")
            return
        
        payments_message = "💳 Payment Requests:\n\n"
        for payment in sorted(payments, key=lambda x: x.created_at, reverse=True):
            payments_message += (
                f"• ID: {payment.id}\n"
                f"  Amount: {payment.amount} {payment.currency}\n"
                f"  Status: {payment.status.value}\n"
                f"  Description: {payment.description}\n"
                f"  Created: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
        await update.message.reply_text(payments_message)

    async def handle_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /projects command."""
        await self.projects(update, context)

    async def handle_team(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /team command."""
        team = await self.team_manager.get_team()
        if not team:
            await update.message.reply_text("No team members found.")
            return
        
        team_message = "👥 Team Members:\n\n"
        for member in team:
            team_message += (
                f"• {member.name}\n"
                f"  Role: {member.role}\n"
                f"  Projects: {len(await self.team_manager.get_member_projects(member.id))}\n\n"
            )
        await update.message.reply_text(team_message)

    async def handle_releases(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /releases command."""
        try:
            releases = await self.agent.get_releases()
            if not releases:
                await update.message.reply_text("No releases found.")
                return

            response = "🎵 Releases:\n\n"
            for release in releases:
                response += (
                    f"📀 {release.title}\n"
                    f"Type: {release.type.value}\n"
                    f"Artist: {release.artist}\n"
                    f"Release Date: {release.release_date.strftime('%Y-%m-%d')}\n"
                    f"Tracks: {len(release.tracks)}\n\n"
                )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error retrieving releases: {str(e)}")

    async def handle_mastering(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /master command."""
        try:
            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "Usage: /master <track_name> <preset>\n"
                    "Example: /master 'My Song' balanced\n"
                    f"Available presets: {', '.join(p.value for p in MasteringPreset)}"
                )
                return

            track_name = context.args[0]
            preset = context.args[1].upper()

            # Validate preset
            try:
                preset = MasteringPreset[preset]
            except KeyError:
                await update.message.reply_text(f"Invalid preset. Available presets: {', '.join(p.value for p in MasteringPreset)}")
                return

            # Create track object
            track = Track(
                title=track_name,
                artist=self.agent.artist_profile.name,
                duration=0,  # Will be set when file is uploaded
                genre=self.agent.artist_profile.genre,
                release_date=datetime.now()
            )

            # Submit for mastering
            result = await self.agent.master_track(track, {"preset": preset})
            await update.message.reply_text(
                f"✅ Track submitted for mastering!\n"
                f"Track: {track_name}\n"
                f"Preset: {preset.value}\n"
                f"Status: {result['status']}"
            )
        except Exception as e:
            await update.message.reply_text(f"Error submitting track for mastering: {str(e)}")

    async def view_platform_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /stats command."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Usage: /stats <platform> [release_id]\n"
                    "Example: /stats spotify\n"
                    f"Available platforms: {', '.join(p.value for p in DistributionPlatform)}"
                )
                return

            platform = context.args[0].upper()
            release_id = context.args[1] if len(context.args) > 1 else None

            # Validate platform
            try:
                platform = DistributionPlatform[platform]
            except KeyError:
                await update.message.reply_text(f"Invalid platform. Available platforms: {', '.join(p.value for p in DistributionPlatform)}")
                return

            stats = await self.agent.get_platform_stats(platform, release_id)
            response = f"📊 {platform.value.title()} Statistics:\n\n"
            response += (
                f"Streams: {stats['streams']:,}\n"
                f"Listeners: {stats['listeners']:,}\n"
                f"Saves: {stats['saves']:,}\n"
            )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error retrieving statistics: {str(e)}")

    async def toggle_auto_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /auto command."""
        if not hasattr(self, '_auto_mode'):
            self._auto_mode = False
        
        self._auto_mode = not self._auto_mode
        status = "enabled" if self._auto_mode else "disabled"
        
        await update.message.reply_text(
            f"🤖 Autonomous mode {status}!\n\n"
            f"The bot will {'now' if self._auto_mode else 'no longer'} "
            f"automatically take actions toward your goals."
        )
        
        if self._auto_mode:
            # Start autonomous loop in background
            context.application.create_task(
                self.agent.autonomous_mode(
                    self.agent.artist_profile.goals,
                    max_actions=5,
                    delay=60
                )
            )

    async def suggest_next_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /suggest command."""
        try:
            action = await self.agent.suggest_action(
                current_state=await self.agent.get_current_state(),
                goals=self.agent.artist_profile.goals,
                previous_actions=[]
            )
            
            await update.message.reply_text(
                f"🤔 Suggested Action:\n\n"
                f"Action: {action.action}\n"
                f"Priority: {action.priority}/5\n"
                f"Reasoning: {action.reasoning}\n\n"
                f"Would you like me to execute this action?"
            )
        except Exception as e:
            await update.message.reply_text(f"Error suggesting action: {str(e)}")

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

            project_id = await self.team_manager.create_project(project)
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

    async def projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for viewing all projects."""
        try:
            projects = self.team_manager.projects.values()
            if not projects:
                await update.message.reply_text("No projects found.")
                return

            response = "📂 Projects:\n\n"
            for project in projects:
                team = await self.team_manager.get_project_team(project.id)
                response += (
                    f"📌 {project.name}\n"
                    f"Status: {project.status}\n"
                    f"Team: {len(team)} members\n"
                    f"Budget: ${project.budget:,.2f}\n"
                    f"Start Date: {project.start_date.strftime('%Y-%m-%d')}\n"
                    f"Description: {project.description}\n\n"
                )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error retrieving projects: {str(e)}")

    async def milestones(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for viewing project milestones."""
        try:
            if not context.args:
                await update.message.reply_text("Usage: /milestones <project_id>")
                return

            project_id = context.args[0]
            project = self.team_manager.projects.get(project_id)
            if not project:
                await update.message.reply_text("Project not found.")
                return

            if not project.milestones:
                await update.message.reply_text("No milestones found for this project.")
                return

            response = f"🎯 Milestones for {project.name}:\n\n"
            for milestone in project.milestones:
                response += (
                    f"• {milestone.get('title', 'Untitled')}\n"
                    f"  Status: {milestone.get('status', 'pending')}\n"
                    f"  Created: {milestone.get('created_at', 'N/A')}\n\n"
                )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error retrieving milestones: {str(e)}")

    async def team(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for viewing team members."""
        await self.handle_team(update, context)

    async def add_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for adding a team member."""
        try:
            if not context.args or len(context.args) < 3:
                await update.message.reply_text(
                    "Usage: /addmember <name> <role> <expertise>\n"
                    "Example: /addmember 'John Doe' producer 'mixing,mastering'\n"
                    "Available roles: artist, producer, manager, songwriter, engineer"
                )
                return

            name = context.args[0]
            role = context.args[1].upper()
            expertise = context.args[2].split(',')

            # Validate role
            try:
                role = CollaboratorRole[role]
            except KeyError:
                await update.message.reply_text(f"Invalid role. Available roles: {', '.join(r.value for r in CollaboratorRole)}")
                return

            profile = CollaboratorProfile(
                name=name,
                role=role,
                expertise=expertise,
                created_at=datetime.now()
            )

            collaborator_id = await self.team_manager.add_collaborator(profile)
            await update.message.reply_text(
                f"✅ Team member added successfully!\n"
                f"Name: {name}\n"
                f"Role: {role.value}\n"
                f"Expertise: {', '.join(expertise)}\n"
                f"ID: {collaborator_id}"
            )
        except Exception as e:
            await update.message.reply_text(f"Error adding team member: {str(e)}")

    async def availability(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for checking team availability."""
        try:
            # If no date provided, use today
            target_date = datetime.now()
            if context.args:
                try:
                    target_date = datetime.strptime(context.args[0], '%Y-%m-%d')
                except ValueError:
                    await update.message.reply_text("Invalid date format. Use YYYY-MM-DD")
                    return

            # Get availability for all roles
            availability = await self.team_manager.get_team_availability(target_date)
            if not availability:
                await update.message.reply_text("No availability information found.")
                return

            response = f"👥 Team Availability for {target_date.strftime('%Y-%m-%d')}:\n\n"
            for collaborator_id, time_slots in availability.items():
                collaborator = self.team_manager.collaborators.get(collaborator_id)
                if collaborator:
                    response += (
                        f"• {collaborator.name} ({collaborator.role.value})\n"
                        f"  Available: {', '.join(time_slots)}\n\n"
                    )

            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error checking availability: {str(e)}")

    async def releases(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for managing releases."""
        await self.handle_releases(update, context)

    async def master_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for submitting tracks for mastering."""
        await self.handle_mastering(update, context)

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for viewing platform statistics."""
        await self.view_platform_stats(update, context)

    async def create_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for creating a new task."""
        try:
            if not context.args or len(context.args) < 4:
                await update.message.reply_text(
                    "Usage: /newtask <title> <assigned_to> <priority> <deadline> <description>\n"
                    "Example: /newtask 'Record vocals' @john 1 2024-03-01 'Record vocals for track 1'\n"
                    "Priority levels: 1 (highest) to 5 (lowest)"
                )
                return

            title = context.args[0]
            assigned_to = context.args[1]
            priority = int(context.args[2])
            deadline = datetime.strptime(context.args[3], '%Y-%m-%d')
            description = " ".join(context.args[4:])

            if not 1 <= priority <= 5:
                await update.message.reply_text("Priority must be between 1 and 5")
                return

            task = Task(
                title=title,
                description=description,
                deadline=deadline,
                assigned_to=assigned_to,
                status="pending",
                priority=priority
            )

            task_id = await self.agent.add_task(task)
            await update.message.reply_text(
                f"✅ Task created successfully!\n"
                f"Title: {title}\n"
                f"Assigned to: {assigned_to}\n"
                f"Priority: {'❗' * priority}\n"
                f"Deadline: {deadline.strftime('%Y-%m-%d')}\n"
                f"ID: {task_id}"
            )
        except ValueError as e:
            await update.message.reply_text(f"Error: {str(e)}")
        except Exception as e:
            await update.message.reply_text(f"An error occurred: {str(e)}")

    async def create_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for creating a new event."""
        try:
            if not context.args or len(context.args) < 5:
                await update.message.reply_text(
                    "Usage: /newevent <title> <type> <date> <venue> <capacity> <budget>\n"
                    "Example: /newevent 'Album Launch' concert '2024-03-01 20:00' 'The Venue' 500 5000\n"
                    "Event types: concert, rehearsal, meeting, recording, promotion"
                )
                return

            title = context.args[0]
            event_type = context.args[1]
            try:
                date = datetime.strptime(" ".join(context.args[2:4]), '%Y-%m-%d %H:%M')
            except ValueError:
                await update.message.reply_text("Invalid date format. Use 'YYYY-MM-DD HH:MM'")
                return

            venue = context.args[4]
            capacity = int(context.args[5])
            budget = float(context.args[6])

            event = Event(
                title=title,
                type=event_type,
                date=date,
                venue=venue,
                capacity=capacity,
                budget=budget,
                status="scheduled"
            )

            event_id = await self.agent.add_event(event)
            await update.message.reply_text(
                f"✅ Event created successfully!\n"
                f"Title: {title}\n"
                f"Type: {event_type}\n"
                f"Date: {date.strftime('%Y-%m-%d %H:%M')}\n"
                f"Venue: {venue}\n"
                f"Capacity: {capacity}\n"
                f"Budget: ${budget:,.2f}\n"
                f"ID: {event_id}"
            )
        except ValueError as e:
            await update.message.reply_text(f"Error: {str(e)}")
        except Exception as e:
            await update.message.reply_text(f"An error occurred: {str(e)}")

    async def create_contract(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for creating a new contract."""
        try:
            if not context.args or len(context.args) < 4:
                await update.message.reply_text(
                    "Usage: /newcontract <title> <parties> <value> <expiration> <terms>\n"
                    "Example: /newcontract 'Recording Agreement' 'Artist,Producer' 5000 2024-12-31 'Recording of 10 tracks'\n"
                    "Separate multiple parties with commas"
                )
                return

            title = context.args[0]
            parties = context.args[1].split(',')
            value = float(context.args[2])
            expiration = datetime.strptime(context.args[3], '%Y-%m-%d')
            terms = {
                "description": " ".join(context.args[4:]),
                "created_at": datetime.now().isoformat()
            }

            contract = Contract(
                title=title,
                parties=parties,
                value=value,
                expiration=expiration,
                terms=terms,
                status="draft"
            )

            contract_id = await self.agent.add_contract(contract)
            await update.message.reply_text(
                f"✅ Contract created successfully!\n"
                f"Title: {title}\n"
                f"Parties: {', '.join(parties)}\n"
                f"Value: ${value:,.2f}\n"
                f"Expiration: {expiration.strftime('%Y-%m-%d')}\n"
                f"Status: draft\n"
                f"ID: {contract_id}"
            )
        except ValueError as e:
            await update.message.reply_text(f"Error: {str(e)}")
        except Exception as e:
            await update.message.reply_text(f"An error occurred: {str(e)}")

    def run(self):
        """Start the bot."""
        try:
            logger.info("Starting bot initialization")
            if not self.token:
                logger.error("No token provided")
                raise ValueError("No token provided")
            
            # Log startup with token validation
            logger.info("Validating token format...")
            if not self.token.count(":") == 1:
                logger.error("Invalid token format")
                raise ValueError("Invalid token format")
            
            # Ensure persistence directory exists
            persistence_dir = os.path.dirname("bot_persistence")
            if persistence_dir:
                os.makedirs(persistence_dir, exist_ok=True)
            
            # Set up persistence with enhanced error handling
            persistence = None
            try:
                # First try to load existing persistence file
                if os.path.exists("bot_persistence"):
                    logger.info("Found existing persistence file")
                
                persistence = PicklePersistence(
                    filepath="bot_persistence",
                    single_file=True,
                    on_flush=True,
                    update_interval=60
                )
                # Validate persistence by attempting to access key methods
                if not hasattr(persistence, 'get_user_data') or not hasattr(persistence, 'get_chat_data'):
                    raise ValueError("Invalid persistence object")
                
                logger.info("Persistence initialized and validated successfully")
            except Exception as e:
                logger.error(f"Failed to initialize persistence: {e}", exc_info=True)
                # Create a new persistence file if loading failed
                try:
                    if os.path.exists("bot_persistence"):
                        backup_path = f"bot_persistence.bak.{int(datetime.now().timestamp())}"
                        os.rename("bot_persistence", backup_path)
                        logger.info(f"Backed up corrupted persistence file to {backup_path}")
                    
                    persistence = PicklePersistence(
                        filepath="bot_persistence",
                        single_file=True,
                        on_flush=True,
                        update_interval=60
                    )
                    logger.info("Created new persistence file successfully")
                except Exception as e2:
                    logger.error(f"Failed to create new persistence file: {e2}", exc_info=True)
                    raise ValueError(f"Could not initialize persistence: {e2}")
            
            if not persistence:
                raise ValueError("Failed to initialize persistence")
            
            # Initialize application with detailed logging
            logger.info("Building application...")
            application = (
                Application.builder()
                .token(self.token)
                .persistence(persistence)
                .build()
            )
            logger.info("Application built successfully")
            
            # Set up handlers with logging
            logger.info("Setting up command handlers...")
            
            # Add onboarding conversation handler first
            logger.info("Setting up onboarding conversation handler...")
            onboarding_handler = ConversationHandler(
                entry_points=[CommandHandler("start", self.onboarding.start_onboarding)],
                states={
                    AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_name)],
                    AWAITING_MANAGER_NAME: [
                        CallbackQueryHandler(self.onboarding.handle_manager_name_callback),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_custom_manager_name)
                    ],
                    AWAITING_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_genre)],
                    AWAITING_SUBGENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_subgenre)],
                    AWAITING_STYLE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_style)],
                    AWAITING_INFLUENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_influences)],
                    AWAITING_CAREER_STAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_career_stage)],
                    AWAITING_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_goals)],
                    AWAITING_GOAL_TIMELINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_goal_timeline)],
                    AWAITING_STRENGTHS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_strengths)],
                    AWAITING_IMPROVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_improvements)],
                    AWAITING_ACHIEVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_achievements)],
                    AWAITING_SOCIAL_MEDIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_social_media)],
                    AWAITING_STREAMING_PROFILES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_streaming)],
                    CONFIRM_PROFILE: [
                        CallbackQueryHandler(self.onboarding.handle_callback_query),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_streaming)
                    ],
                    EDIT_SECTION: [
                        CallbackQueryHandler(self.onboarding.handle_callback_query),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.onboarding.handle_edit_section)
                    ]
                },
                fallbacks=[CommandHandler("cancel", self.onboarding.cancel)],
                name="onboarding_conversation",
                persistent=True,
                per_message=False  # Track per chat instead of per message
            )
            
            # Add handlers in order of priority
            application.add_handler(onboarding_handler)
            logger.info("Added onboarding handler")
            
            # Add other command handlers
            self.register_handlers(application)
            
            # Enhanced error handler
            async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
                """Handle errors with detailed logging."""
                logger.error("Exception while handling an update:", exc_info=context.error)
                error_details = {
                    "update": str(update),
                    "error": str(context.error),
                    "trace": str(context.error.__traceback__)
                }
                log_event("error", error_details)
                
                if update and isinstance(update, Update) and update.message:
                    await update.message.reply_text(
                        "Sorry, something went wrong. Please try again later."
                    )
            
            application.add_error_handler(error_handler)
            logger.info("Added error handler")
            
            # Start polling with detailed logging
            logger.info("Starting bot polling...")
            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
                pool_timeout=30
            )
            
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}", exc_info=True)
            raise

    async def stop(self):
        """Stop the bot gracefully."""
        self._is_running = False 

    def register_handlers(self, application: Application) -> None:
        """Register all command and conversation handlers."""
        # Core commands
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("goals", self.goals))
        
        # Project Management
        application.add_handler(CommandHandler("projects", self.handle_projects))
        application.add_handler(CommandHandler("newproject", self.create_project))
        application.add_handler(CommandHandler("milestones", self.milestones))
        
        # Team Management
        application.add_handler(CommandHandler("team", self.team))
        application.add_handler(CommandHandler("addmember", self.add_member))
        application.add_handler(CommandHandler("avail", self.availability))
        
        # Music Services
        application.add_handler(CommandHandler("releases", self.handle_releases))
        application.add_handler(CommandHandler("master", self.handle_mastering))
        application.add_handler(CommandHandler("stats", self.view_platform_stats))
        
        # Task Management
        application.add_handler(CommandHandler("tasks", self.tasks))
        application.add_handler(CommandHandler("newtask", self.create_task))
        
        # Financial Management
        application.add_handler(CommandHandler("finances", self.finances))
        application.add_handler(CommandHandler("pay", self.request_payment))
        application.add_handler(CommandHandler("checkpay", self.check_payment))
        application.add_handler(CommandHandler("payments", self.list_payments))
        
        # Event Management
        application.add_handler(CommandHandler("events", self.events))
        application.add_handler(CommandHandler("newevent", self.create_event))
        
        # Contract Management
        application.add_handler(CommandHandler("contracts", self.contracts))
        application.add_handler(CommandHandler("newcontract", self.create_contract))
        
        # AI Features
        application.add_handler(CommandHandler("auto", self.toggle_auto_mode))
        application.add_handler(CommandHandler("suggest", self.suggest_next_action))
        
        # Analytics
        application.add_handler(CommandHandler("analytics", self.view_analytics))
        application.add_handler(CommandHandler("health", self.health)) 