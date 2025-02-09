from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
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
    PaymentStatus
)
from artist_manager_agent.log import logger, log_event
import uuid
import logging
import asyncio
from functools import partial
import psutil
import sys

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
        """Initialize the bot with either an existing agent or create a new one."""
        if agent:
            self.agent = agent
        elif artist_profile and openai_api_key:
            self.agent = ArtistManagerAgent(
                artist_profile=artist_profile,
                openai_api_key=openai_api_key,
                model=model,
                db_url=db_url,
                telegram_token=telegram_token or token,
                ai_mastering_key=ai_mastering_key
            )
        else:
            raise ValueError("Either agent or (artist_profile and openai_api_key) must be provided")
            
        self.team_manager = self.agent  # For compatibility with tests
        
        # Initialize application with job queue
        builder = Application.builder()
        builder.token(telegram_token or token)
        builder.job_queue(None)  # This enables the job queue with default settings
        self.app = builder.build()
        
        self.start_time = datetime.now()
        self._setup_handlers()
        self._is_running = False

    def _setup_handlers(self):
        """Set up command handlers and background jobs."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("goals", self.goals))
        self.app.add_handler(CommandHandler("tasks", self.tasks))
        self.app.add_handler(CommandHandler("events", self.events))
        self.app.add_handler(CommandHandler("contracts", self.contracts))
        self.app.add_handler(CommandHandler("finances", self.finances))
        self.app.add_handler(CommandHandler("health", self.health))
        self.app.add_handler(CommandHandler("request_payment", self.request_payment))
        self.app.add_handler(CommandHandler("check_payment", self.check_payment))
        self.app.add_handler(CommandHandler("list_payments", self.list_payments))
        
        # Add monitoring job after application is initialized
        if self.app.job_queue:
            self.app.job_queue.run_repeating(
                self._monitor_metrics,
                interval=60,
                first=0
            )

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
        welcome_message = (
            f"👋 Welcome to your Artist Manager Bot!\n\n"
            f"I'm here to help manage {self.agent.artist_profile.name}'s career.\n\n"
            f"Use /help to see available commands."
        )
        await update.message.reply_text(welcome_message)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        help_message = (
            "Available commands:\n\n"
            "/goals - View career goals\n"
            "/tasks - Manage tasks\n"
            "/events - View upcoming events\n"
            "/contracts - View contracts\n"
            "/finances - View financial records\n"
            "/health - Check artist health status\n"
            "/request_payment - Request a payment\n"
            "/check_payment - Check payment status\n"
            "/list_payments - List all payments"
        )
        await update.message.reply_text(help_message)

    async def goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /goals command."""
        goals = self.agent.artist_profile.goals
        goals_message = "🎯 Career Goals:\n\n" + "\n".join(f"• {goal}" for goal in goals)
        await update.message.reply_text(goals_message)

    async def tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /tasks command."""
        tasks = await self.agent.get_tasks()
        if not tasks:
            await update.message.reply_text("No tasks found.")
            return
        
        tasks_message = "📋 Tasks:\n\n"
        for task in tasks:
            tasks_message += (
                f"• {task.title}\n"
                f"  Status: {task.status}\n"
                f"  Deadline: {task.deadline.strftime('%Y-%m-%d')}\n"
                f"  Assigned to: {task.assigned_to}\n\n"
            )
        await update.message.reply_text(tasks_message)

    async def events(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /events command."""
        events = await self.agent.get_events()
        if not events:
            await update.message.reply_text("No events found.")
            return
        
        events_message = "📅 Events:\n\n"
        for event in events:
            events_message += (
                f"• {event.title}\n"
                f"  Type: {event.type}\n"
                f"  Venue: {event.venue}\n"
                f"  Date: {event.date.strftime('%Y-%m-%d %H:%M')}\n"
                f"  Status: {event.status}\n\n"
            )
        await update.message.reply_text(events_message)

    async def contracts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /contracts command."""
        contracts = await self.agent.get_contracts()
        if not contracts:
            await update.message.reply_text("No contracts found.")
            return
        
        contracts_message = "📄 Contracts:\n\n"
        for contract in contracts:
            contracts_message += (
                f"• {contract.title}\n"
                f"  Status: {contract.status}\n"
                f"  Value: ${contract.value:,.2f}\n"
                f"  Expiration: {contract.expiration.strftime('%Y-%m-%d')}\n\n"
            )
        await update.message.reply_text(contracts_message)

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
                "Usage: /request_payment <amount> <currency> <description>"
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
            await update.message.reply_text("Usage: /check_payment <payment_id>")
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

    async def run(self):
        """Start the bot."""
        try:
            # Log startup
            log_event("startup", {
                "config": {
                    "model": self.agent.model,
                    "db_url": self.agent.db_url,
                    "log_level": logger.level
                },
                "pid": psutil.Process().pid,
                "python_version": sys.version
            })
            
            # Initialize the application
            await self.app.initialize()
            await self.app.start()
            self._is_running = True
            
            # Start polling
            await self.app.updater.start_polling(drop_pending_updates=True)
            
            # Keep the bot running
            while self._is_running:
                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    logger.info("Received cancellation signal")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    break
                
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            raise
        finally:
            self._is_running = False
            try:
                if hasattr(self.app, 'updater') and self.app.updater:
                    await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
            except Exception as e:
                logger.error(f"Error during bot shutdown: {str(e)}")
                # Don't re-raise here to ensure cleanup continues

    async def stop(self):
        """Stop the bot gracefully."""
        self._is_running = False 