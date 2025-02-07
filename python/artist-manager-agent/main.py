import os
import logging
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from artist_manager_agent.bot_commands import BotCommandHandler
from artist_manager_agent.health_tracking import HealthTracker
from artist_manager_agent.music_services import MusicServices
from artist_manager_agent.release_planning import ReleasePlan
from artist_manager_agent.schedule import Schedule
from artist_manager_agent.social_media import SocialMediaManager
from artist_manager_agent.team_management import TeamManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ArtistManagerBot:
    """Main bot class coordinating all services."""
    
    def __init__(self):
        self.command_handler = BotCommandHandler()
        self.health_tracker = HealthTracker()
        self.music_services = MusicServices()
        self.release_plan = ReleasePlan()
        self.schedule = Schedule()
        self.social_media = SocialMediaManager()
        self.team_manager = TeamManager()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        welcome_message = f"""
👋 Hi {user.first_name}! I'm your AI Artist Manager.

I'm here to help you manage your music career with:
🎵 Release Planning
👥 Team Management
📅 Scheduling
🎯 Health Tracking
📱 Social Media
🎚️ Music Distribution

Use /help to see all available commands.
        """.strip()
        
        await update.message.reply_text(welcome_message)
        
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = """
Available Commands:

📋 General
/start - Start interaction
/help - Show this help message

🎵 Release Management
/release - Plan and track releases
/master - Submit tracks for AI mastering
/distribute - Manage music distribution

👥 Team Management
/team - Manage team members
/payments - Handle payments
/projects - Manage projects

📅 Schedule
/schedule - View and manage calendar
/availability - Check team availability
/events - Manage events

🎯 Health
/health - Track health metrics
/wellness - Daily wellness check
/vocal - Monitor vocal health

📱 Social Media
/social - Manage social media
/campaign - Create campaigns
/analytics - View performance metrics

Need help with anything specific? Just ask!
        """.strip()
        
        await update.message.reply_text(help_message)
        
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")
        
        error_message = """
😕 Oops! Something went wrong.

I've logged the error and will look into it. 
Please try again or use /help to see available commands.
        """.strip()
        
        if update.effective_message:
            await update.effective_message.reply_text(error_message)

def main():
    """Initialize and start the bot."""
    # Create bot instance
    bot = ArtistManagerBot()
    
    # Get bot token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No bot token found! Set TELEGRAM_BOT_TOKEN in .env")
        return
        
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    
    # Add release planning handlers
    application.add_handler(CommandHandler("release", bot.command_handler.handle_release))
    application.add_handler(CommandHandler("master", bot.command_handler.handle_master))
    application.add_handler(CommandHandler("distribute", bot.command_handler.handle_distribute))
    
    # Add team management handlers
    application.add_handler(CommandHandler("team", bot.command_handler.handle_team))
    application.add_handler(CommandHandler("payments", bot.command_handler.handle_payments))
    application.add_handler(CommandHandler("projects", bot.command_handler.handle_projects))
    
    # Add schedule handlers
    application.add_handler(CommandHandler("schedule", bot.command_handler.handle_schedule))
    application.add_handler(CommandHandler("availability", bot.command_handler.handle_availability))
    application.add_handler(CommandHandler("events", bot.command_handler.handle_events))
    
    # Add health tracking handlers
    application.add_handler(CommandHandler("health", bot.command_handler.handle_health))
    application.add_handler(CommandHandler("wellness", bot.command_handler.handle_wellness))
    application.add_handler(CommandHandler("vocal", bot.command_handler.handle_vocal))
    
    # Add social media handlers
    application.add_handler(CommandHandler("social", bot.command_handler.handle_social))
    application.add_handler(CommandHandler("campaign", bot.command_handler.handle_campaign))
    application.add_handler(CommandHandler("analytics", bot.command_handler.handle_analytics))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(bot.command_handler.handle_callback))
    
    # Add error handler
    application.add_error_handler(bot.error_handler)
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 