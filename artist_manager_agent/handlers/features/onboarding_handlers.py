"""Onboarding handlers for the Artist Manager Bot."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters, CallbackQueryHandler, BaseHandler
)
import uuid
from ...models import ArtistProfile
from ...utils.logger import get_logger
from ..core.base_handler import BaseBotHandler

logger = get_logger(__name__)

# States
AWAITING_NAME = "AWAITING_NAME"
AWAITING_GENRE = "AWAITING_GENRE"
AWAITING_SUBGENRE = "AWAITING_SUBGENRE"
AWAITING_SIMILAR_ARTISTS = "AWAITING_SIMILAR_ARTISTS"
AWAITING_SOUND_DESCRIPTION = "AWAITING_SOUND_DESCRIPTION"
AWAITING_TARGET_AUDIENCE = "AWAITING_TARGET_AUDIENCE"
AWAITING_FANBASE_SIZE = "AWAITING_FANBASE_SIZE"
AWAITING_CAREER_STAGE = "AWAITING_CAREER_STAGE"
AWAITING_SOCIAL_MEDIA = "AWAITING_SOCIAL_MEDIA"
AWAITING_GOALS = "AWAITING_GOALS"
AWAITING_GOAL_TIMEFRAME = "AWAITING_GOAL_TIMEFRAME"
AWAITING_STREAMING_PROFILES = "AWAITING_STREAMING_PROFILES"

# Quick goal templates by career stage
QUICK_GOALS = {
    "emerging": [
        "Release first single",
        "Build social media presence",
        "Create EPK",
        "Book first live show"
    ],
    "developing": [
        "Release EP/Album",
        "Grow streaming numbers",
        "Build email list",
        "Book local tour"
    ],
    "established": [
        "Increase monthly listeners",
        "Launch merch line",
        "Book national tour",
        "Get playlist placements"
    ],
    "professional": [
        "Launch new album campaign",
        "Book international tour",
        "Secure brand partnerships",
        "Expand team"
    ]
}

# Career stage specific prompts
STAGE_PROMPTS = {
    "emerging": {
        "sound_description": "How would you describe your sound? (Think about mood, style, influences)",
        "target_audience": "Who is your ideal listener? (Age, interests, location)",
        "social_media": "Which social media platform do you use most to connect with fans?",
        "next_steps": "Let's focus on building your foundation and getting your music out there."
    },
    "developing": {
        "sound_description": "What makes your sound unique? What sets you apart?",
        "target_audience": "Who are your most engaged listeners currently?",
        "social_media": "Which platforms are driving the most engagement?",
        "next_steps": "Let's focus on growing your audience and building momentum."
    },
    "established": {
        "sound_description": "How has your sound evolved? What's your signature style?",
        "target_audience": "What demographics show the most growth potential?",
        "social_media": "Which content types perform best across your platforms?",
        "next_steps": "Let's focus on scaling your success and expanding your reach."
    },
    "professional": {
        "sound_description": "What defines your brand sonically? What's your vision?",
        "target_audience": "What audience segments drive the most revenue?",
        "social_media": "What's your content strategy across platforms?",
        "next_steps": "Let's focus on optimizing your operations and maximizing impact."
    }
}

class OnboardingHandlers(BaseBotHandler):
    """Handlers for onboarding process."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 0  # Highest priority
        self._load_name_data()

    def _load_name_data(self):
        """Load name components for generating manager names."""
        self.first_names = ["Alex", "Jordan", "Morgan", "Taylor", "Casey", "Sam", "Jamie", "Avery", "Riley", "Quinn"]
        self.last_names = ["Wright", "Reed", "Rivers", "Brooks", "Hayes", "Morgan", "Blake", "Rhodes", "Silva", "Chen"]
        
        # Generate random manager name if not already set
        if 'manager_name' not in self.bot.application.bot_data:
            import random
            first_name = random.choice(self.first_names)
            last_name = random.choice(self.last_names)
            self.bot.application.bot_data['manager_name'] = f"{first_name} {last_name}"

    def get_handlers(self) -> List[BaseHandler]:
        """Get onboarding-related handlers."""
        logger.info("Getting onboarding handlers")
        handler = self.get_conversation_handler()
        logger.debug(f"Created conversation handler: {handler}")
        return [handler]

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for onboarding."""
        logger.debug("Creating onboarding conversation handler")
        handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_onboarding, block=False),
                CallbackQueryHandler(self.handle_callback, pattern="^onboard_.*$")
            ],
            states={
                AWAITING_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_name)
                ],
                AWAITING_GENRE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_genre)
                ],
                AWAITING_SUBGENRE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_subgenre)
                ],
                AWAITING_SIMILAR_ARTISTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_similar_artists)
                ],
                AWAITING_SOUND_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_sound_description)
                ],
                AWAITING_TARGET_AUDIENCE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_target_audience)
                ],
                AWAITING_FANBASE_SIZE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_fanbase_size)
                ],
                AWAITING_CAREER_STAGE: [
                    CallbackQueryHandler(self.handle_career_stage, pattern="^stage_")
                ],
                AWAITING_SOCIAL_MEDIA: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_social_media),
                    CallbackQueryHandler(self.handle_social_media_callback, pattern="^social_")
                ],
                AWAITING_GOALS: [
                    CallbackQueryHandler(self.handle_goals, pattern="^goal_"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_custom_goal)
                ],
                AWAITING_GOAL_TIMEFRAME: [
                    CallbackQueryHandler(self.handle_goal_timeframe, pattern="^timeframe_"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_custom_timeframe)
                ],
                AWAITING_STREAMING_PROFILES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_streaming_profiles),
                    CallbackQueryHandler(self.handle_streaming_callback, pattern="^platform_")
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
            allow_reentry=True,
            block=False  # Added to ensure non-blocking
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
        logger.debug(f"Message type: {update.message and 'text' if update.message else 'callback'}")
        logger.debug(f"Command: {update.message and update.message.text if update.message else 'None'}")
        
        try:
            # Clear any existing state
            context.user_data.clear()
            logger.debug("Cleared user data")
            
            # Check if user already has a profile
            profile = self.bot.profiles.get(user_id)
            logger.debug(f"Found profile for user {user_id}: {profile is not None}")
            
            if profile:
                logger.info(f"Existing profile found for user {user_id}")
                # Show dashboard for existing users
                keyboard = [[InlineKeyboardButton("View Dashboard", callback_data="dashboard_view")]]
                await self._send_or_edit_message(
                    update,
                    f"Welcome back, {profile.name}! How can I help you today?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return ConversationHandler.END
            
            # Get or generate manager name
            manager_name = context.bot_data.get('manager_name', 'Avery Rhodes')
            logger.debug(f"Using manager name: {manager_name}")
            
            # If this is a button response, proceed directly to artist name input
            if update.callback_query:
                logger.debug("Processing callback query")
                await update.callback_query.answer()
                if update.callback_query.data == "onboard_start":
                    logger.info("Starting artist name input")
                    # Set conversation active flag
                    context.user_data["conversation_active"] = True
                    logger.debug("Set conversation_active flag")
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

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle artist name input."""
        name = update.message.text.strip()
        logger.info(f"Handling artist name input: {name}")
        context.user_data["name"] = name
        context.user_data["conversation_active"] = True  # Ensure flag stays set
        logger.debug(f"Updated user_data: {context.user_data}")
        
        await self._send_or_edit_message(
            update,
            "What genre best describes your music?\n\n"
            "Examples: Pop, Rock, Hip Hop, Electronic, etc.",
            reply_markup=None
        )
        return AWAITING_GENRE

    async def handle_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle genre input and ask for subgenre."""
        genre = update.message.text.strip()
        logger.info(f"Handling genre input: {genre}")
        context.user_data["genre"] = genre
        
        await self._send_or_edit_message(
            update,
            f"Great! What subgenre of {genre} best describes your music?\n\n"
            "For example: If genre is 'Hip Hop', subgenre might be 'Trap' or 'Boom Bap'",
            reply_markup=None
        )
        return AWAITING_SUBGENRE

    async def handle_subgenre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle subgenre input and ask for similar artists."""
        subgenre = update.message.text.strip()
        context.user_data["subgenre"] = subgenre
        
        await self._send_or_edit_message(
            update,
            "Who are 2-3 artists that have a similar sound or style to you?",
            reply_markup=None
        )
        return AWAITING_SIMILAR_ARTISTS

    async def handle_similar_artists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle similar artists input and move to career stage."""
        similar_artists = update.message.text.strip()
        context.user_data["similar_artists"] = similar_artists
        
        keyboard = [
            [InlineKeyboardButton("Emerging", callback_data="stage_emerging")],
            [InlineKeyboardButton("Developing", callback_data="stage_developing")],
            [InlineKeyboardButton("Established", callback_data="stage_established")],
            [InlineKeyboardButton("Professional", callback_data="stage_professional")]
        ]
        
        await self._send_or_edit_message(
            update,
            "What's your current career stage?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAITING_CAREER_STAGE

    async def handle_career_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle career stage input and ask personalized questions."""
        query = update.callback_query
        await query.answer()
        
        stage = query.data.split('_')[1]
        context.user_data["career_stage"] = stage
        
        # Get stage-specific prompts
        prompts = STAGE_PROMPTS[stage]
        
        # Ask for sound description with personalized prompt
        await self._send_or_edit_message(
            update,
            prompts["sound_description"],
            reply_markup=None
        )
        return AWAITING_SOUND_DESCRIPTION

    async def handle_sound_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle sound description and ask about target audience."""
        description = update.message.text.strip()
        context.user_data["sound_description"] = description
        
        stage = context.user_data["career_stage"]
        prompts = STAGE_PROMPTS[stage]
        
        await self._send_or_edit_message(
            update,
            prompts["target_audience"],
            reply_markup=None
        )
        return AWAITING_TARGET_AUDIENCE

    async def handle_target_audience(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle target audience and ask about fanbase size."""
        audience = update.message.text.strip()
        context.user_data["target_audience"] = audience
        
        await self._send_or_edit_message(
            update,
            "What's your current fanbase size?\n\n"
            "For example:\n"
            "• Monthly Listeners\n"
            "• Social Media Followers\n"
            "• Email List Size",
            reply_markup=None
        )
        return AWAITING_FANBASE_SIZE

    async def handle_fanbase_size(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle fanbase size and move to social media."""
        fanbase = update.message.text.strip()
        context.user_data["fanbase_size"] = fanbase
        
        # Show social media platform options
        keyboard = [
            [
                InlineKeyboardButton("Instagram 📸", callback_data="social_instagram"),
                InlineKeyboardButton("TikTok 📱", callback_data="social_tiktok")
            ],
            [
                InlineKeyboardButton("Twitter 🐦", callback_data="social_twitter"),
                InlineKeyboardButton("YouTube 🎥", callback_data="social_youtube")
            ],
            [InlineKeyboardButton("Skip", callback_data="social_skip")]
        ]
        
        await self._send_or_edit_message(
            update,
            "Let's connect your social media profiles.\nSelect a platform to add:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAITING_SOCIAL_MEDIA

    async def handle_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle goal selection."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.split('_')[1]
        
        if action == "custom":
            await self._send_or_edit_message(
                update,
                "What's your goal? (Type it in)",
                reply_markup=None
            )
            return AWAITING_GOALS
        
        elif action == "quick":
            goal = query.data.split('_', 2)[2]
            if "goals" not in context.user_data:
                context.user_data["goals"] = []
            context.user_data["goals"].append({"title": goal, "timeframe": None})
            
            # Show timeframe options
            keyboard = [
                [
                    InlineKeyboardButton("1 month", callback_data="timeframe_1"),
                    InlineKeyboardButton("3 months", callback_data="timeframe_3"),
                    InlineKeyboardButton("6 months", callback_data="timeframe_6")
                ],
                [
                    InlineKeyboardButton("1 year", callback_data="timeframe_12"),
                    InlineKeyboardButton("Custom", callback_data="timeframe_custom")
                ]
            ]
            
            await self._send_or_edit_message(
                update,
                f"When do you want to achieve: {goal}?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_GOAL_TIMEFRAME
        
        elif action == "done":
            # Move to streaming profiles
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
                "Great! Now let's connect your streaming profiles.\nSelect a platform to add:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_STREAMING_PROFILES
        
        return AWAITING_GOALS

    async def handle_custom_goal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle custom goal input."""
        goal = update.message.text.strip()
        if "goals" not in context.user_data:
            context.user_data["goals"] = []
        context.user_data["goals"].append({"title": goal, "timeframe": None})
        
        # Show timeframe options
        keyboard = [
            [
                InlineKeyboardButton("1 month", callback_data="timeframe_1"),
                InlineKeyboardButton("3 months", callback_data="timeframe_3"),
                InlineKeyboardButton("6 months", callback_data="timeframe_6")
            ],
            [
                InlineKeyboardButton("1 year", callback_data="timeframe_12"),
                InlineKeyboardButton("Custom", callback_data="timeframe_custom")
            ]
        ]
        
        await self._send_or_edit_message(
            update,
            f"When do you want to achieve: {goal}?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAITING_GOAL_TIMEFRAME

    async def handle_goal_timeframe(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle goal timeframe selection."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.split('_')[1]
        
        if action == "custom":
            await self._send_or_edit_message(
                update,
                "Enter the number of months (e.g., '9' for 9 months):",
                reply_markup=None
            )
            return AWAITING_GOAL_TIMEFRAME
        
        # Convert to months
        months = int(action)
        
        # Update the last added goal
        context.user_data["goals"][-1]["timeframe"] = months
        
        # Show current goals and options to add more
        goals_text = "Your goals:\n\n"
        for goal in context.user_data["goals"]:
            timeframe = f"{goal['timeframe']} months" if goal['timeframe'] else "No timeframe"
            goals_text += f"• {goal['title']} ({timeframe})\n"
        
        keyboard = [
            [InlineKeyboardButton("Add Another Goal", callback_data="goal_custom")],
            [InlineKeyboardButton("Continue", callback_data="goal_done")]
        ]
        
        await self._send_or_edit_message(
            update,
            f"{goals_text}\n\nWould you like to add another goal?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAITING_GOALS

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle onboarding-related callbacks."""
        query = update.callback_query
        
        try:
            # Answer callback query first to prevent timeout
            await query.answer()
            
            action = query.data.replace("onboard_", "")
            logger.info(f"Onboarding handler processing callback: {query.data} -> {action}")
            
            if action == "start":
                # Clear any existing state
                context.user_data.clear()
                await self._send_or_edit_message(
                    update,
                    "What's your artist name?",
                    reply_markup=None
                )
                return AWAITING_NAME
            elif action == "menu":
                await self.show_menu(update, context)
                return ConversationHandler.END
            else:
                logger.warning(f"Unknown onboarding action: {action}")
                await self.show_menu(update, context)
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Error in onboarding callback: {str(e)}", exc_info=True)
            # Ensure we still answer the callback query even in case of error
            try:
                await query.answer()
            except Exception:
                pass
            
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="onboard_menu")
                ]])
            )
            return ConversationHandler.END

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the onboarding menu."""
        keyboard = [
            [InlineKeyboardButton("Start Onboarding", callback_data="onboard_start")],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            "🎵 *Artist Manager Bot - Onboarding*\n\n"
            "Let's get your profile set up! This will help me:\n"
            "• Understand your goals\n"
            "• Track your progress\n"
            "• Provide personalized recommendations\n"
            "• Connect with your platforms",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        ) 

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

    async def handle_shortcut_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle shortcut commands during onboarding."""
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
            # Format goals as strings
            goals = []
            for goal in context.user_data.get("goals", []):
                timeframe = f"{goal['timeframe']} months" if goal['timeframe'] else "No timeframe"
                goals.append(f"{goal['title']} ({timeframe})")
            
            # Create profile with current data
            profile = ArtistProfile(
                id=str(uuid.uuid4()),
                name=context.user_data.get("name", ""),
                genre=context.user_data.get("genre", ""),
                career_stage=context.user_data.get("career_stage", ""),
                goals=goals,  # Now using formatted goal strings
                strengths=[],
                areas_for_improvement=[],
                achievements=[],
                social_media={},
                streaming_profiles=context.user_data.get("streaming_profiles", {}),
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
            
        elif command == 'no':
            # Go back to platform selection
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
            
        return AWAITING_STREAMING_PROFILES 

    async def cancel_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the onboarding process."""
        # Clear conversation state and flag
        context.user_data.clear()
        await update.message.reply_text(
            "Onboarding cancelled. Use /start to begin again."
        )
        return ConversationHandler.END

    async def handle_streaming_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle streaming platform selection callbacks."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("platform_", "")
        
        if action == "skip" or action == "done":
            try:
                # Format goals as strings
                goals = []
                for goal in context.user_data.get("goals", []):
                    timeframe = f"{goal['timeframe']} months" if goal['timeframe'] else "No timeframe"
                    goals.append(f"{goal['title']} ({timeframe})")
                
                # Create profile with current data
                profile = ArtistProfile(
                    id=str(uuid.uuid4()),
                    name=context.user_data.get("name", ""),
                    genre=context.user_data.get("genre", ""),
                    career_stage=context.user_data.get("career_stage", ""),
                    goals=goals,  # Now using formatted goal strings
                    strengths=[],
                    areas_for_improvement=[],
                    achievements=[],
                    social_media=context.user_data.get("social_media", {}),
                    streaming_profiles=context.user_data.get("streaming_profiles", {}),
                    brand_guidelines={"description": "", "colors": [], "fonts": [], "tone": "professional"}
                )
                
                # Save profile
                user_id = str(update.effective_user.id)
                self.bot.profiles[user_id] = profile
                logger.info(f"Created and saved profile for user {user_id}")
                
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
                logger.error(f"Error creating profile: {str(e)}", exc_info=True)
                await self._send_or_edit_message(
                    update,
                    "Sorry, there was an error creating your profile. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="onboard_menu")
                    ]])
                )
                return ConversationHandler.END
            
        elif action in ["spotify", "apple", "soundcloud"]:
            context.user_data["current_platform"] = action
            await self._send_or_edit_message(
                update,
                f"Please enter your {action.title()} profile link:",
                reply_markup=None
            )
            return AWAITING_STREAMING_PROFILES
            
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
            
        return AWAITING_STREAMING_PROFILES 

    async def handle_social_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle social media profile input."""
        text = update.message.text.strip()
        
        # Initialize social media dict if not exists
        if "social_media" not in context.user_data:
            context.user_data["social_media"] = {}
            
        # Get current platform being added
        platform = context.user_data.get("current_platform")
        if not platform:
            # Show platform options if no platform selected
            keyboard = [
                [
                    InlineKeyboardButton("Instagram 📸", callback_data="social_instagram"),
                    InlineKeyboardButton("TikTok 📱", callback_data="social_tiktok")
                ],
                [
                    InlineKeyboardButton("Twitter 🐦", callback_data="social_twitter"),
                    InlineKeyboardButton("YouTube 🎥", callback_data="social_youtube")
                ],
                [InlineKeyboardButton("Skip", callback_data="social_skip")]
            ]
            await self._send_or_edit_message(
                update,
                "Select a social media platform to add:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_SOCIAL_MEDIA
            
        # Store the profile
        context.user_data["social_media"][platform] = text
        context.user_data.pop("current_platform")
        
        # Ask if they want to add another platform
        keyboard = [
            [
                InlineKeyboardButton("Add Another", callback_data="social_add"),
                InlineKeyboardButton("Continue", callback_data="social_done")
            ]
        ]
        await self._send_or_edit_message(
            update,
            f"✅ Added {platform} profile!\nWould you like to add another platform?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAITING_SOCIAL_MEDIA

    async def handle_social_media_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle social media platform selection callbacks."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("social_", "")
        
        if action == "skip" or action == "done":
            # Move to goals
            stage = context.user_data.get("career_stage", "emerging")
            goals = QUICK_GOALS.get(stage, [])
            
            keyboard = []
            for goal in goals:
                keyboard.append([InlineKeyboardButton(goal, callback_data=f"goal_quick_{goal}")])
            keyboard.append([InlineKeyboardButton("Add Custom Goal", callback_data="goal_custom")])
            
            await self._send_or_edit_message(
                update,
                "Let's set some goals! Here are some suggestions based on your career stage:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_GOALS
            
        elif action in ["instagram", "tiktok", "twitter", "youtube"]:
            context.user_data["current_platform"] = action
            await self._send_or_edit_message(
                update,
                f"Please enter your {action.title()} profile link or username:",
                reply_markup=None
            )
            return AWAITING_SOCIAL_MEDIA
            
        elif action == "add":
            keyboard = [
                [
                    InlineKeyboardButton("Instagram 📸", callback_data="social_instagram"),
                    InlineKeyboardButton("TikTok 📱", callback_data="social_tiktok")
                ],
                [
                    InlineKeyboardButton("Twitter 🐦", callback_data="social_twitter"),
                    InlineKeyboardButton("YouTube 🎥", callback_data="social_youtube")
                ],
                [InlineKeyboardButton("Skip", callback_data="social_skip")]
            ]
            await self._send_or_edit_message(
                update,
                "Select a social media platform to add:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_SOCIAL_MEDIA
            
        return AWAITING_SOCIAL_MEDIA 

    async def handle_custom_timeframe(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle custom timeframe input for goals."""
        try:
            # Parse the number of months
            months = int(update.message.text.strip())
            if months <= 0:
                await self._send_or_edit_message(
                    update,
                    "Please enter a positive number of months:",
                    reply_markup=None
                )
                return AWAITING_GOAL_TIMEFRAME
            
            # Update the last added goal
            context.user_data["goals"][-1]["timeframe"] = months
            
            # Show current goals and options to add more
            goals_text = "Your goals:\n\n"
            for goal in context.user_data["goals"]:
                timeframe = f"{goal['timeframe']} months" if goal['timeframe'] else "No timeframe"
                goals_text += f"• {goal['title']} ({timeframe})\n"
            
            keyboard = [
                [InlineKeyboardButton("Add Another Goal", callback_data="goal_custom")],
                [InlineKeyboardButton("Continue", callback_data="goal_done")]
            ]
            
            await self._send_or_edit_message(
                update,
                f"{goals_text}\n\nWould you like to add another goal?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_GOALS
            
        except ValueError:
            await self._send_or_edit_message(
                update,
                "Please enter a valid number of months (e.g., '9' for 9 months):",
                reply_markup=None
            )
            return AWAITING_GOAL_TIMEFRAME 