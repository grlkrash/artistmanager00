from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)
from .log import logger

class CommandHandlers:
    """Handles command registration and callback routing."""
    
    def __init__(self, bot):
        self.bot = bot

    def register_handlers(self, application: Application) -> None:
        """Register command handlers."""
        # Register onboarding handler first
        application.add_handler(self.bot.onboarding.get_conversation_handler(), group=0)
        
        # Core commands
        core_handlers = [
            CommandHandler("help", self.bot.help),
            CommandHandler("home", self.bot.show_menu),
            CommandHandler("me", self.bot.view_profile),
            CommandHandler("update", self.bot.edit_profile)
        ]
        
        # Project management
        project_handlers = [
            CommandHandler("projects", self.bot.project_manager.show_projects),
            CommandHandler("project_new", self.bot.project_manager.create_project),
            CommandHandler("project_milestone", self.bot.project_manager.handle_milestone_action),
            CommandHandler("project_team", self.bot.project_manager.handle_team_action)
        ]
        
        # Music services
        music_handlers = [
            CommandHandler("music", self.bot.show_music_options),
            CommandHandler("release", self.bot.manage_release),
            CommandHandler("master", self.bot.manage_mastering),
            CommandHandler("distribute", self.bot.manage_distribution)
        ]
        
        # Team management
        team_handlers = [
            CommandHandler("team", self.bot.show_team_options),
            CommandHandler("team_add", self.bot.add_team_member),
            CommandHandler("team_schedule", self.bot.team_schedule),
            CommandHandler("team_pay", self.bot.team_payments)
        ]
        
        # Blockchain features
        blockchain_handlers = [
            CommandHandler("blockchain", self.bot.show_blockchain_options),
            CommandHandler("wallet", self.bot.blockchain.handle_wallet),
            CommandHandler("nft", self.bot.blockchain.handle_deploy_nft),
            CommandHandler("token", self.bot.blockchain.handle_deploy_token)
        ]
        
        # Auto mode
        auto_handlers = [
            CommandHandler("auto", self.bot.auto_mode.show_options),
            CommandHandler("auto_setup", self.bot.auto_mode.setup),
            CommandHandler("auto_goals", self.bot.auto_mode.handle_goals),
            CommandHandler("auto_schedule", self.bot.auto_mode.handle_schedule)
        ]
        
        # Register all handlers
        all_handlers = (
            core_handlers + 
            project_handlers + 
            music_handlers + 
            team_handlers + 
            blockchain_handlers + 
            auto_handlers
        )
        
        for handler in all_handlers:
            application.add_handler(handler, group=2)
            
        # Add callback query handler for interactive menus
        application.add_handler(
            CallbackQueryHandler(self.handle_callback),
            group=1
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline buttons."""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Log callback data for debugging
            logger.info(f"Callback received from user {user_id}: {query.data}")
            
            # Ensure user has a profile
            if not context.user_data.get("profile_data"):
                await query.answer("Please complete your profile setup first with /start")
                return
                
            # Handle different button callbacks
            if query.data.startswith("goals_"):
                await self.bot.handle_goals_callback(query)
            elif query.data.startswith("auto_"):
                await self.bot.auto_mode.handle_callback(update, context)
            elif query.data.startswith("project_"):
                await self.bot.project_manager.handle_project_callback(update, context)
            elif query.data.startswith("team_"):
                await self.bot.handle_team_callback(query)
            elif query.data.startswith("music_"):
                await self.bot.handle_music_callback(query)
            else:
                logger.warning(f"Unknown callback data received: {query.data}")
                await query.answer("This feature is not implemented yet")
                
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
            await query.answer("Sorry, an error occurred. Please try again or use commands instead.") 