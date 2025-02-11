"""Onboarding handlers for the Artist Manager Bot."""
from typing import Dict, Any, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters, CallbackQueryHandler, BaseHandler
)
import uuid
from ..models import ArtistProfile
from ..utils.logger import get_logger
from .base_handler import BaseBotHandler

logger = get_logger(__name__)

# States
AWAITING_NAME = "AWAITING_NAME"
AWAITING_GENRE = "AWAITING_GENRE"
AWAITING_CAREER_STAGE = "AWAITING_CAREER_STAGE"

class OnboardingHandlers(BaseBotHandler):
    """Handlers for onboarding process."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 0  # Highest priority
        self._load_name_data()

    def _load_name_data(self):
        """Load name components for generating manager names."""
        self.first_names = ["Alex", "Jordan", "Morgan", "Taylor", "Casey", "Sam", "Jamie"]
        self.last_names = ["Wright", "Reed", "Rivers", "Brooks", "Hayes", "Morgan", "Blake"]

    def get_handlers(self) -> List[BaseHandler]:
        """Get onboarding-related handlers."""
        return [self.get_conversation_handler()]

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for onboarding."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_onboarding),
                CallbackQueryHandler(self.handle_callback, pattern="^onboard_.*$")
            ],
            states={
                AWAITING_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_name)
                ],
                AWAITING_GENRE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_genre)
                ],
                AWAITING_CAREER_STAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_career_stage)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_onboarding)],
            name="onboarding",
            persistent=False
        )

    async def start_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start the onboarding process."""
        user_id = str(update.effective_user.id)
        logger.info(f"Starting onboarding for user {user_id}")
        
        # Clear any existing state
        context.user_data.clear()
        
        # Generate manager name if not set
        manager_name = context.bot_data.get('manager_name', 'Avery Rhodes')
        context.user_data['manager_name'] = manager_name
        
        # Send welcome message with single button
        keyboard = [[InlineKeyboardButton("Let's Get Started", callback_data="onboard_start")]]
        
        # Use _send_or_edit_message to handle both new messages and edits
        await self._send_or_edit_message(
            update,
            f"Hey! I'm {manager_name} 👋\n\n"
            "I specialize in helping artists succeed in today's music industry. I can help with:\n\n"
            "🎯 Release strategy & planning\n"
            "📈 Marketing & promotion\n"
            "👥 Team coordination\n"
            "📊 Performance tracking\n\n"
            "Ready to start building your success strategy?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ConversationHandler.END

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle onboarding callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == "onboard_start":
                # Don't send a new message, just edit the existing one
                await self._send_or_edit_message(
                    update,
                    "What's your artist name or stage name?",
                    reply_markup=None
                )
                return AWAITING_NAME
                
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error in onboarding callback: {str(e)}")
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="core_menu")
                ]])
            )
            return ConversationHandler.END

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle artist name input."""
        name = update.message.text.strip()
        context.user_data["name"] = name
        
        await self._send_or_edit_message(
            update,
            "What genre best describes your music?\n\n"
            "Examples: Pop, Rock, Hip Hop, Electronic, etc.",
            reply_markup=None
        )
        return AWAITING_GENRE

    async def handle_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle genre input."""
        genre = update.message.text.strip()
        context.user_data["genre"] = genre
        
        keyboard = [
            ["Just Starting 🌱", "Building Momentum 🚀"],
            ["Established Artist ⭐", "Professional 👑"]
        ]
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=f"stage_{text}") for text in row] for row in keyboard])
        
        await self._send_or_edit_message(
            update,
            "What's your current career stage?",
            reply_markup=reply_markup
        )
        return AWAITING_CAREER_STAGE

    async def handle_career_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle career stage input."""
        stage = update.message.text.strip()
        context.user_data["career_stage"] = stage
        
        # Create profile
        profile = ArtistProfile(
            id=str(uuid.uuid4()),
            name=context.user_data["name"],
            genre=context.user_data["genre"],
            career_stage=stage,
            goals=[],
            strengths=[],
            areas_for_improvement=[],
            achievements=[],
            social_media={},
            streaming_profiles={},
            brand_guidelines={"description": "", "colors": [], "fonts": [], "tone": "professional"}
        )
        
        # Save profile
        self.bot.profiles[str(profile.id)] = profile
        
        # Show success message
        keyboard = [[InlineKeyboardButton("View Dashboard", callback_data="dashboard_view")]]
        await self._send_or_edit_message(
            update,
            f"Welcome aboard, {profile.name}! Your profile has been created.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Clear conversation state
        context.user_data.clear()
        
        return ConversationHandler.END

    async def cancel_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the onboarding process."""
        context.user_data.clear()
        await self._send_or_edit_message(
            update,
            "Onboarding cancelled. Use /start to begin again."
        )
        return ConversationHandler.END

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show onboarding menu."""
        # This is not used but required by BaseBotHandler
        pass 