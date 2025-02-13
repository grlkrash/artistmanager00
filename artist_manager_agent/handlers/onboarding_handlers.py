"""Onboarding handlers for the Artist Manager Bot."""
from typing import Dict, Any, List, Optional
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
AWAITING_STREAMING_PROFILES = "AWAITING_STREAMING_PROFILES"

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
        logger.debug("Creating onboarding conversation handler")
        handler = ConversationHandler(
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
                ],
                AWAITING_STREAMING_PROFILES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_streaming_profiles)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_onboarding),
                MessageHandler(filters.Regex("^(c|y|n|continue|yes|no|skip)$"), self.handle_shortcut_commands)
            ],
            name="onboarding",
            persistent=True,
            per_chat=True,
            per_user=True,
            per_message=False,
            allow_reentry=True
        )
        logger.debug(f"Onboarding handler created with entry points: {[type(h).__name__ for h in handler.entry_points]}")
        logger.debug(f"Onboarding handler states: {list(handler.states.keys())}")
        return handler

    async def start_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start the onboarding process."""
            user_id = str(update.effective_user.id)
            logger.info(f"Starting onboarding for user {user_id}")
        logger.debug(f"Update type: {type(update)}")
        logger.debug(f"Update content: {update.to_dict()}")
        logger.debug(f"Context user data: {context.user_data}")
        logger.debug(f"Context bot data: {context.bot_data}")
            
        try:
            # Clear any existing state
            context.user_data.clear()
            logger.debug("Cleared user data")
            
            # Get or generate manager name
            manager_name = context.bot_data.get('manager_name', 'Avery Rhodes')
            logger.debug(f"Using manager name: {manager_name}")
            
            # If this is a button response, proceed directly to artist name input
                if update.callback_query:
                logger.debug("Processing callback query")
                await update.callback_query.answer()
                if update.callback_query.data == "onboard_start":
                    logger.info("Starting artist name input")
                    await self._send_or_edit_message(
                        update,
                        "What's your artist name?",
                        reply_markup=None
                    )
                    return AWAITING_NAME
                return
                
            # Initial welcome message with button
            keyboard = [
                [InlineKeyboardButton("Start", callback_data="onboard_start")],
                [InlineKeyboardButton("Settings", callback_data="settings_menu")]
            ]
            
            logger.info("Sending welcome message")
            await self._send_or_edit_message(
                update,
                f"👋 I'm {manager_name}\n\n"
                "I help artists with:\n"
                "🎯 Strategy & Planning\n"
                "📈 Marketing\n"
                "👥 Team Management\n"
                "📊 Analytics",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            logger.debug("Welcome message sent")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error in start_onboarding: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try /start again.",
                reply_markup=None
                )
            return ConversationHandler.END

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle onboarding callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == "onboard_start":
                await self._send_or_edit_message(
                    update,
                    "What's your artist name?",
                    reply_markup=None
                )
                return AWAITING_NAME
                
            elif query.data.startswith("platform_"):
                action = query.data.replace("platform_", "")
                
                if action == "skip" or action == "done":
                    return await self.finalize_onboarding(update, context)
                    
                elif action == "add":
                    keyboard = [
                        [
                            InlineKeyboardButton("🎧 Spotify", callback_data="platform_spotify"),
                            InlineKeyboardButton("🎵 Apple Music", callback_data="platform_apple")
                        ],
                        [
                            InlineKeyboardButton("☁️ SoundCloud", callback_data="platform_soundcloud"),
                            InlineKeyboardButton("Skip", callback_data="platform_skip")
                        ]
                    ]
                    await self._send_or_edit_message(
                        update,
                        "Select a platform to add:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return AWAITING_STREAMING_PROFILES
                    
                else:  # Platform selected
                    context.user_data['current_platform'] = action
                    platform_examples = {
                        'spotify': 'spotify.com/artist/...',
                        'apple_music': 'music.apple.com/...',
                        'soundcloud': 'soundcloud.com/...'
                    }
                    await self._send_or_edit_message(
                        update,
                        f"Enter your {action} profile link:\n"
                        f"Example: {platform_examples[action]}\n\n"
                        "Or type 'c' to skip, 'n' to choose different platform",
                        reply_markup=None
                    )
                    return AWAITING_STREAMING_PROFILES
                    
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
            ["Emerging", "Developing"],
            ["Established", "Professional"]
        ]
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=f"stage_{text}") for text in row] for row in keyboard])
        
        await self._send_or_edit_message(
            update,
            "What's your current career stage?",
            reply_markup=reply_markup
            )
            return AWAITING_CAREER_STAGE
            
    async def handle_career_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
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

    async def handle_streaming_profiles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle streaming profile input."""
        text = update.message.text.strip().lower()
        
        # Handle shortcuts
        if text in ['c', 'y', 'n', 'continue', 'yes', 'no', 'skip']:
            return await self.handle_shortcut_commands(update, context)
        
        # Parse profile links
        try:
            # Initialize profiles if not exists
            if 'streaming_profiles' not in context.user_data:
                context.user_data['streaming_profiles'] = {}
            
            # Handle platform selection first
            if 'current_platform' not in context.user_data:
                keyboard = [
                    [
                        InlineKeyboardButton("🎧 Spotify", callback_data="platform_spotify"),
                        InlineKeyboardButton("🎵 Apple Music", callback_data="platform_apple")
                    ],
                    [
                        InlineKeyboardButton("☁️ SoundCloud", callback_data="platform_soundcloud"),
                        InlineKeyboardButton("Skip", callback_data="platform_skip")
                    ]
                ]
                await self._send_or_edit_message(
                    update,
                    "Select a platform to add:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return AWAITING_STREAMING_PROFILES
            
            # Parse profile link for current platform
            platform = context.user_data['current_platform']
            username = self._parse_profile_link(text, platform)
            
            if not username:
                platform_examples = {
                    'spotify': 'spotify.com/artist/...',
                    'apple_music': 'music.apple.com/...',
                    'soundcloud': 'soundcloud.com/...'
                }
                await self._send_or_edit_message(
                    update,
                    f"Please enter a valid {platform} link:\n"
                    f"Example: {platform_examples[platform]}\n\n"
                    "Or type 'c' to continue, 'n' to try a different platform"
                )
                return AWAITING_STREAMING_PROFILES
            
            # Store profile
            context.user_data['streaming_profiles'][platform] = username
            context.user_data.pop('current_platform')
            
            # Ask for next platform
            keyboard = [
                [
                    InlineKeyboardButton("Add Another", callback_data="platform_add"),
                    InlineKeyboardButton("Continue", callback_data="platform_done")
                ]
            ]
            await self._send_or_edit_message(
                update,
                f"✅ Added {platform} profile!\n"
                "Would you like to add another platform?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_STREAMING_PROFILES
            
        except Exception as e:
            logger.error(f"Error handling streaming profile: {str(e)}")
            await self._send_or_edit_message(
                update,
                "Sorry, I couldn't process that. Please try again or type 'c' to continue."
        )
        return AWAITING_STREAMING_PROFILES

    def _parse_profile_link(self, text: str, platform: str) -> Optional[str]:
        """Parse a streaming profile link for a specific platform."""
        text = text.lower().strip()
        
        # Platform-specific parsing
        if platform == 'spotify' and 'spotify.com/artist/' in text:
            return text.split('spotify.com/artist/')[-1].split('/')[0]
        elif platform == 'apple_music' and 'music.apple.com' in text:
            return text.split('music.apple.com/')[-1].split('?')[0]
        elif platform == 'soundcloud' and 'soundcloud.com/' in text:
            return text.split('soundcloud.com/')[-1].split('/')[0]
        
        return None

    async def finalize_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Finalize the onboarding process."""
        try:
            # Create profile
            profile_data = {
                'id': str(uuid.uuid4()),
                'name': context.user_data.get('name', ''),
                'genre': context.user_data.get('genre', ''),
                'career_stage': context.user_data.get('career_stage', ''),
                'streaming_profiles': context.user_data.get('streaming_profiles', {}),
                'goals': [],
                'strengths': [],
                'areas_for_improvement': [],
                'achievements': [],
                'social_media': context.user_data.get('social_media', {}),
                'brand_guidelines': {
                    "description": "",
                    "colors": [],
                    "fonts": [],
                    "tone": "professional"
                }
            }
            
            profile = ArtistProfile(**profile_data)
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
            
        except Exception as e:
            logger.error(f"Error finalizing onboarding: {str(e)}")
            await self._send_or_edit_message(
                update,
                "Sorry, there was an error creating your profile. Please try again."
            )
            return ConversationHandler.END

    async def cancel_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the onboarding process."""
        context.user_data.clear()
        await self._send_or_edit_message(
            update,
            "Onboarding cancelled. Use /start to begin again."
        )
        return ConversationHandler.END

    async def handle_shortcut_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle shortcut commands."""
        command = update.message.text.lower()
        
        # Map shortcuts to full commands
        command_map = {
            'c': 'continue',
            'y': 'yes',
            'n': 'no'
        }
        
        # Convert shortcut to full command if needed
        command = command_map.get(command, command)
        
        if command in ['continue', 'yes', 'skip']:
            return await self.finalize_onboarding(update, context)
        elif command == 'no':
            return await self.cancel_onboarding(update, context)
        
        return ConversationHandler.END

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show onboarding menu."""
        # This is not used but required by BaseBotHandler
        pass 