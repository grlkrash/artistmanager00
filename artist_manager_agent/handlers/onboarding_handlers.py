"""Onboarding handlers for the Artist Manager Bot."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ForceReply
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters, CallbackQueryHandler, BaseHandler
)
import random
import re
import logging
from ..models import ArtistProfile
from .base_handler import BaseHandlerMixin

logger = logging.getLogger(__name__)

# State definitions
(
    AWAITING_NAME,
    AWAITING_MANAGER_NAME,
    AWAITING_GENRE,
    AWAITING_SUBGENRE,
    AWAITING_STYLE_DESCRIPTION,
    AWAITING_INFLUENCES,
    AWAITING_CAREER_STAGE,
    AWAITING_GOALS,
    AWAITING_GOALS_CONFIRMATION,
    AWAITING_STRENGTHS,
    AWAITING_STRENGTHS_CONFIRMATION,
    AWAITING_IMPROVEMENTS,
    AWAITING_IMPROVEMENTS_CONFIRMATION,
    AWAITING_ACHIEVEMENTS,
    AWAITING_SOCIAL_MEDIA,
    AWAITING_STREAMING_PROFILES,
    CONFIRM_PROFILE,
    EDIT_CHOICE,
    EDIT_SECTION
) = range(19)

class StateManager:
    """Manages conversation states and transitions."""
    
    def __init__(self):
        self.active_states: Dict[int, str] = {}
        self.state_history: Dict[int, List[str]] = {}
        
    async def transition_to(self, user_id: int, new_state: str) -> bool:
        """
        Attempt to transition to a new state.
        Returns True if transition is allowed and successful.
        """
        current_state = self.active_states.get(user_id)
        
        # Log the attempted transition
        logger.info(f"State transition attempt for user {user_id}: {current_state} -> {new_state}")
        
        # Initialize history if needed
        if user_id not in self.state_history:
            self.state_history[user_id] = []
            
        # Validate transition
        if current_state == new_state:
            logger.warning(f"Attempted transition to same state for user {user_id}: {new_state}")
            return False
            
        # Update state
        self.active_states[user_id] = new_state
        self.state_history[user_id].append(new_state)
        
        logger.info(f"State transition successful for user {user_id}: {current_state} -> {new_state}")
        return True
        
    def get_current_state(self, user_id: int) -> Optional[str]:
        """Get the current state for a user."""
        return self.active_states.get(user_id)
        
    def clear_state(self, user_id: int):
        """Clear the state for a user."""
        if user_id in self.active_states:
            del self.active_states[user_id]
        if user_id in self.state_history:
            del self.state_history[user_id]

class OnboardingHandlers(BaseHandlerMixin):
    """Handlers for onboarding process."""
    
    group = "onboarding"  # Handler group for registration
    
    def __init__(self, bot):
        self.bot = bot
        self.temp_data: Dict[str, Any] = {}
        self._load_name_data()
        self.state_manager = StateManager()

    def get_handlers(self) -> List[BaseHandler]:
        """Get onboarding-related handlers."""
        return [
            CommandHandler("start", self.start_onboarding),
            CommandHandler("onboard", self.start_onboarding),
            self.get_conversation_handler()
        ]

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for onboarding."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_onboarding),
                CommandHandler("onboard", self.start_onboarding)
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
                AWAITING_GOALS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_goals)
                ],
                AWAITING_GOALS_CONFIRMATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_goals_confirmation)
                ],
                AWAITING_STRENGTHS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_strengths)
                ],
                AWAITING_STRENGTHS_CONFIRMATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_strengths_confirmation)
                ],
                AWAITING_IMPROVEMENTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_improvements)
                ],
                AWAITING_IMPROVEMENTS_CONFIRMATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_improvements_confirmation)
                ],
                AWAITING_ACHIEVEMENTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_achievements)
                ],
                AWAITING_SOCIAL_MEDIA: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_social_media)
                ],
                AWAITING_STREAMING_PROFILES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_streaming_profiles)
                ],
                CONFIRM_PROFILE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_profile_confirmation)
                ],
                EDIT_CHOICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_choice)
                ],
                EDIT_SECTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_section)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_onboarding),
                CommandHandler("skip", self.skip_current_step)
            ],
            name="onboarding",
            persistent=True
        )

    def _load_name_data(self):
        """Load name components for generating manager names."""
        self.first_names = [
            "Alex", "Jordan", "Morgan", "Taylor", "Casey", "Sam", "Jamie", 
            "Riley", "Quinn", "Avery", "Blake", "Charlie", "Drew", "Emerson",
            "Frankie", "Gray", "Harper", "Indie", "Jules", "Kennedy"
        ]
        self.last_names = [
            "Wright", "Reed", "Rivers", "Brooks", "Hayes", "Morgan", "Blake",
            "Quinn", "Parker", "Foster", "Gray", "Rhodes", "Shaw", "Sterling",
            "Turner", "Vale", "West", "Young", "Zane", "Ellis"
        ]

    def _generate_manager_name(self) -> str:
        """Generate a random manager name."""
        return f"{random.choice(self.first_names)} {random.choice(self.last_names)}"

    async def start_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the onboarding process."""
        user_id = update.effective_user.id
        logger.info(f"Starting onboarding for user {user_id}")
        
        # Clear any existing state
        self.state_manager.clear_state(user_id)
        
        # Initialize first state
        if await self.state_manager.transition_to(user_id, AWAITING_NAME):
            await update.message.reply_text(
                "🎵 Welcome to Artist Manager Bot! 🎵\n\n"
                "Let's get started with setting up your artist profile! "
                "First, what's your artist name?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_NAME
        else:
            logger.error(f"Failed to initialize state for user {user_id}")
            await update.message.reply_text(
                "Sorry, I encountered an error starting the onboarding process. "
                "Please try again with /start or /onboard."
            )
            return ConversationHandler.END

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the artist name input."""
        user_id = update.effective_user.id
        name = update.message.text
        logger.info(f"Handling name input for user {user_id}: {name}")
        
        try:
            context.user_data['name'] = name
            logger.info(f"Saved name {name} for user {user_id}")
            
            # Create keyboard for genre selection
            keyboard = [
                ["Pop", "Rock", "Hip Hop"],
                ["Electronic", "R&B", "Jazz"],
                ["Classical", "Folk", "Other"]
            ]
            
            await update.message.reply_text(
                f"Great to meet you, {name}! What genre best describes your music?",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            logger.info(f"Sent genre prompt to user {user_id}")
            return AWAITING_GENRE
            
        except Exception as e:
            logger.error(f"Error handling name for user {user_id}: {str(e)}")
            await update.message.reply_text(
                "Sorry, I encountered an error processing your name. Please try again."
            )
            return AWAITING_NAME

    async def handle_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the genre input."""
        genre = update.message.text
        context.user_data['genre'] = genre
        
        # Create keyboard for career stage
        keyboard = [
            ["Emerging", "Established", "Veteran"]
        ]
        
        await update.message.reply_text(
            "What's your current career stage?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_CAREER_STAGE

    async def handle_career_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the career stage input."""
        stage = update.message.text.lower()
        if stage not in ["emerging", "established", "veteran"]:
            await update.message.reply_text(
                "Please select one of: emerging, established, or veteran"
            )
            return AWAITING_CAREER_STAGE
        
        context.user_data['career_stage'] = stage
        await update.message.reply_text(
            "What are your main goals as an artist?\n\n"
            "You can:\n"
            "• List them one per line\n"
            "• Separate them with commas\n"
            "• Use bullet points\n\n"
            "Example:\n"
            "Release an EP by end of year\n"
            "Reach 10k monthly listeners\n"
            "Book 5 live shows",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_GOALS

    async def handle_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the goals input."""
        text = update.message.text.strip()
        
        # Split by common separators and clean up
        goals = [
            goal.strip()
            for goal in re.split(r'[,;\n•\-]', text)
            if goal.strip()
        ]
        
        if not goals:
            await update.message.reply_text(
                "I couldn't detect any goals. Please share your goals as an artist.\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Release an EP by end of year\n"
                "Reach 10k monthly listeners\n"
                "Book 5 live shows"
            )
            return AWAITING_GOALS
            
        context.user_data['temp_goals'] = goals
        
        # Show what was understood
        goals_str = "\n".join(f"• {goal}" for goal in goals)
        
        # Create confirmation keyboard
        keyboard = [["Yes", "No"]]
        
        await update.message.reply_text(
            f"I understood these goals:\n\n{goals_str}\n\n"
            "Is this correct?\n"
            "If yes, let's move on to your strengths.\n"
            "If no, please enter your goals again.",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_GOALS_CONFIRMATION

    async def handle_goals_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle confirmation of goals."""
        if update.message.text.lower() == 'yes':
            context.user_data['goals'] = context.user_data.pop('temp_goals')
            await update.message.reply_text(
                "Great! Now, what would you say are your strengths as an artist?\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Strong vocal range\n"
                "Experienced with live performances\n"
                "Good at social media engagement",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_STRENGTHS
        else:
            await update.message.reply_text(
                "Okay, please enter your goals again.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_GOALS

    async def handle_strengths(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the strengths input."""
        text = update.message.text.strip()
        
        # Split by common separators and clean up
        strengths = [
            strength.strip()
            for strength in re.split(r'[,;\n•\-]', text)
            if strength.strip()
        ]
        
        if not strengths:
            await update.message.reply_text(
                "I couldn't detect any strengths. Please share your strengths as an artist.\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_STRENGTHS
            
        context.user_data['temp_strengths'] = strengths
        
        # Show what was understood
        strengths_str = "\n".join(f"• {strength}" for strength in strengths)
        
        # Create confirmation keyboard
        keyboard = [["Yes", "No"]]
        
        await update.message.reply_text(
            f"I understood these strengths:\n\n{strengths_str}\n\n"
            "Is this correct?\n"
            "If yes, let's move on to areas for improvement.\n"
            "If no, please enter your strengths again.",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_STRENGTHS_CONFIRMATION

    async def handle_strengths_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle confirmation of strengths."""
        if update.message.text.lower() == 'yes':
            context.user_data['strengths'] = context.user_data.pop('temp_strengths')
            await update.message.reply_text(
                "Excellent! Now, what areas would you like to improve in?\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Music theory knowledge\n"
                "Stage presence\n"
                "Marketing skills",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_IMPROVEMENTS
        else:
            await update.message.reply_text(
                "Okay, please enter your strengths again.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_STRENGTHS

    async def handle_improvements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the improvements input."""
        text = update.message.text.strip()
        
        # Split by common separators and clean up
        improvements = [
            improvement.strip()
            for improvement in re.split(r'[,;\n•\-]', text)
            if improvement.strip()
        ]
        
        if not improvements:
            await update.message.reply_text(
                "I couldn't detect any areas for improvement. Please share what you'd like to improve.\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_IMPROVEMENTS
            
        context.user_data['temp_improvements'] = improvements
        
        # Show what was understood
        improvements_str = "\n".join(f"• {improvement}" for improvement in improvements)
        
        # Create confirmation keyboard
        keyboard = [["Yes", "No"]]
        
        await update.message.reply_text(
            f"I understood these areas for improvement:\n\n{improvements_str}\n\n"
            "Is this correct?\n"
            "If yes, let's move on to your achievements.\n"
            "If no, please enter them again.",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_IMPROVEMENTS_CONFIRMATION

    async def handle_improvements_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle confirmation of improvements."""
        if update.message.text.lower() == 'yes':
            context.user_data['improvements'] = context.user_data.pop('temp_improvements')
            await update.message.reply_text(
                "Great! Now, what are some of your notable achievements?\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Released debut EP\n"
                "Performed at major festival\n"
                "Featured in music blog",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_ACHIEVEMENTS
        else:
            await update.message.reply_text(
                "Okay, please enter your areas for improvement again.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_IMPROVEMENTS

    async def handle_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the achievements input."""
        text = update.message.text.strip()
        
        # Split by common separators and clean up
        achievements = [
            achievement.strip()
            for achievement in re.split(r'[,;\n•\-]', text)
            if achievement.strip()
        ]
        
        context.user_data['achievements'] = achievements
        
        await update.message.reply_text(
            "Awesome! Now, please share your social media handles.\n"
            "Format: platform: handle\n\n"
            "Example:\n"
            "Instagram: @artistname\n"
            "Twitter: @artistname\n"
            "TikTok: @artistname\n\n"
            "Or type 'skip' to skip this step.",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_SOCIAL_MEDIA

    async def handle_social_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle social media input."""
        text = update.message.text.strip()
        
        if text.lower() != 'skip':
            # Parse social media handles
            social_media = {}
            for line in text.split('\n'):
                if ':' in line:
                    platform, handle = line.split(':', 1)
                    social_media[platform.strip().lower()] = handle.strip()
            context.user_data['social_media'] = social_media
        
        await update.message.reply_text(
            "Last step! Please share your streaming platform profiles.\n"
            "Format: platform: profile_url\n\n"
            "Example:\n"
            "Spotify: spotify.com/artist/...\n"
            "Apple Music: music.apple.com/...\n"
            "SoundCloud: soundcloud.com/...\n\n"
            "Or type 'skip' to skip this step.",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_STREAMING_PROFILES

    async def handle_streaming_profiles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle streaming profiles input."""
        text = update.message.text.strip()
        
        if text.lower() != 'skip':
            # Parse streaming profiles
            streaming = {}
            for line in text.split('\n'):
                if ':' in line:
                    platform, url = line.split(':', 1)
                    streaming[platform.strip().lower()] = url.strip()
            context.user_data['streaming_profiles'] = streaming
        
        # Create profile summary
        profile_text = self._create_profile_summary(context.user_data)
        
        # Create confirmation keyboard
        keyboard = [
            ["Confirm Profile"],
            ["Edit Profile"],
            ["Start Over"]
        ]
        
        await update.message.reply_text(
            "Here's your profile summary:\n\n"
            f"{profile_text}\n\n"
            "What would you like to do?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return CONFIRM_PROFILE

    def _create_profile_summary(self, data: Dict[str, Any]) -> str:
        """Create a formatted profile summary."""
        summary = [
            f"🎤 Artist Name: {data.get('name', 'Not set')}",
            f"🎵 Genre: {data.get('genre', 'Not set')}",
            f"📈 Career Stage: {data.get('career_stage', 'Not set')}",
            "\n🎯 Goals:"
        ]
        
        if 'goals' in data:
            summary.extend(f"• {goal}" for goal in data['goals'])
            
        summary.append("\n💪 Strengths:")
        if 'strengths' in data:
            summary.extend(f"• {strength}" for strength in data['strengths'])
            
        summary.append("\n📈 Areas for Improvement:")
        if 'improvements' in data:
            summary.extend(f"• {improvement}" for improvement in data['improvements'])
            
        summary.append("\n🏆 Achievements:")
        if 'achievements' in data:
            summary.extend(f"• {achievement}" for achievement in data['achievements'])
            
        if 'social_media' in data:
            summary.append("\n📱 Social Media:")
            for platform, handle in data['social_media'].items():
                summary.append(f"• {platform.title()}: {handle}")
                
        if 'streaming_profiles' in data:
            summary.append("\n🎧 Streaming Profiles:")
            for platform, url in data['streaming_profiles'].items():
                summary.append(f"• {platform.title()}: {url}")
                
        return "\n".join(summary)

    async def handle_profile_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle profile confirmation."""
        choice = update.message.text.lower()
        
        if choice == 'confirm profile':
            # Create ArtistProfile object
            profile = ArtistProfile(
                id=str(update.effective_user.id),
                name=context.user_data.get('name', ''),
                genre=context.user_data.get('genre', ''),
                career_stage=context.user_data.get('career_stage', ''),
                goals=context.user_data.get('goals', []),
                strengths=context.user_data.get('strengths', []),
                improvements=context.user_data.get('improvements', []),
                achievements=context.user_data.get('achievements', []),
                social_media=context.user_data.get('social_media', {}),
                streaming_profiles=context.user_data.get('streaming_profiles', {}),
                created_at=datetime.now()
            )
            
            # Save profile
            self.bot.profiles[str(update.effective_user.id)] = profile.dict()
            
            # Show success message
            keyboard = [
                [
                    InlineKeyboardButton("View Profile", callback_data="profile_view"),
                    InlineKeyboardButton("Edit Profile", callback_data="profile_edit")
                ],
                [InlineKeyboardButton("Start Using Bot", callback_data="show_menu")]
            ]
            
            await update.message.reply_text(
                "✨ Profile created successfully! ✨\n\n"
                "You're all set to start using the Artist Manager Bot.\n"
                "What would you like to do next?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
        elif choice == 'edit profile':
            sections = [
                "Name", "Genre", "Career Stage", "Goals",
                "Strengths", "Improvements", "Achievements",
                "Social Media", "Streaming Profiles"
            ]
            keyboard = [[section] for section in sections]
            keyboard.append(["Cancel"])
            
            await update.message.reply_text(
                "Which section would you like to edit?",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return EDIT_CHOICE
            
        elif choice == 'start over':
            # Clear user data
            context.user_data.clear()
            
            # Restart onboarding
            return await self.start_onboarding(update, context)
            
        else:
            await update.message.reply_text(
                "Please select one of the options: Confirm Profile, Edit Profile, or Start Over"
            )
            return CONFIRM_PROFILE

    async def handle_edit_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle edit section choice."""
        section = update.message.text.lower()
        
        if section == 'cancel':
            return await self.handle_streaming_profiles(update, context)
            
        context.user_data['editing_section'] = section
        
        await update.message.reply_text(
            f"Please enter the new value for {section}:",
            reply_markup=ForceReply(selective=True)
        )
        return EDIT_SECTION

    async def handle_edit_section(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle section edit input."""
        section = context.user_data.pop('editing_section')
        new_value = update.message.text.strip()
        
        # Update the appropriate section
        if section in ['goals', 'strengths', 'improvements', 'achievements']:
            context.user_data[section] = [
                item.strip()
                for item in re.split(r'[,;\n•\-]', new_value)
                if item.strip()
            ]
        elif section in ['social_media', 'streaming_profiles']:
            profiles = {}
            for line in new_value.split('\n'):
                if ':' in line:
                    platform, value = line.split(':', 1)
                    profiles[platform.strip().lower()] = value.strip()
            context.user_data[section] = profiles
        else:
            context.user_data[section.lower().replace(' ', '_')] = new_value
        
        # Show updated profile
        return await self.handle_streaming_profiles(update, context)

    async def cancel_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the onboarding process."""
        user_id = update.effective_user.id
        self.state_manager.clear_state(user_id)
        context.user_data.clear()
        
        keyboard = [[InlineKeyboardButton("Start Over", callback_data="start_onboarding")]]
        
        await update.message.reply_text(
            "Onboarding cancelled. You can start over when you're ready.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    async def skip_current_step(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Skip the current step."""
        current_state = self.state_manager.get_current_state(update.effective_user.id)
        
        if current_state in [AWAITING_SOCIAL_MEDIA, AWAITING_STREAMING_PROFILES]:
            return await self.handle_streaming_profiles(update, context)
            
        await update.message.reply_text(
            "This step cannot be skipped. Please provide the requested information or use /cancel to stop."
        )
        return current_state 