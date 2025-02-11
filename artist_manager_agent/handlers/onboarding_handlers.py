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
    
    group = 4  # Handler group for registration
    
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
            CallbackQueryHandler(self.handle_dashboard_callback, pattern="^(newproject|social|goals|analytics|events|show_commands|start_tutorial|show_dashboard)$"),
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
            persistent=True,
            allow_reentry=True
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
            "Awesome! Now, let's add your social media profiles.\n\n"
            "You can enter them in any format you like:\n"
            "• Platform: @handle (e.g., Instagram: @artistname)\n"
            "• @handle - platform (e.g., @artistname - Twitter)\n"
            "• Just platform and handle (e.g., TikTok @artistname)\n"
            "• Or any other format!\n\n"
            "Enter each profile on a new line. For example:\n"
            "Instagram: @artistname\n"
            "@artistname - Twitter\n"
            "TikTok @artistname\n\n"
            "Or type 'skip' to skip this step.",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_SOCIAL_MEDIA

    def _parse_social_media(self, text: str) -> Dict[str, str]:
        """Parse social media handles from various formats."""
        social_media = {}
        
        # Skip if user wants to skip
        if text.lower() == 'skip':
            return social_media
            
        # Process each line
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Try different formats:
            # 1. platform: @handle
            # 2. platform - @handle
            # 3. platform @handle
            # 4. @handle (platform)
            # 5. @handle - platform
            # 6. Just @handle platform
            
            # Remove common separators
            line = line.replace(':', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ')
            parts = [p.strip() for p in line.split() if p.strip()]
            
            if not parts:
                continue
                
            # Find the handle (starts with @) and platform
            handle_part = next((p for p in parts if p.startswith('@')), None)
            if handle_part:
                # Handle found, platform is the other part
                platform_part = next((p for p in parts if p != handle_part), None)
                if platform_part:
                    social_media[platform_part.lower()] = handle_part
            else:
                # No @ symbol, assume last part is handle
                if len(parts) >= 2:
                    platform = parts[0].lower()
                    handle = parts[-1]
                    # Add @ if missing
                    if not handle.startswith('@'):
                        handle = f"@{handle}"
                    social_media[platform] = handle
                    
        return social_media

    def _parse_streaming_profiles(self, text: str) -> Dict[str, str]:
        """Parse streaming profiles from various formats."""
        streaming = {}
        
        # Skip if user wants to skip
        if text.lower() == 'skip':
            return streaming
            
        # Common streaming platforms to detect
        PLATFORMS = {
            'spotify': ['spotify', 'spot'],
            'apple': ['apple', 'apple music', 'itunes'],
            'soundcloud': ['soundcloud', 'sc'],
            'youtube': ['youtube', 'yt'],
            'bandcamp': ['bandcamp', 'bc'],
            'tidal': ['tidal'],
            'deezer': ['deezer']
        }
        
        # Process each line
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # If it's just a URL, try to detect platform
            if line.startswith(('http://', 'https://')):
                for platform, keywords in PLATFORMS.items():
                    if any(k in line.lower() for k in keywords):
                        streaming[platform] = line
                        break
                continue
                
            # Try different formats with platform name
            # Remove common separators
            line = line.replace(':', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ')
            parts = [p.strip() for p in line.split() if p.strip()]
            
            if len(parts) >= 2:
                # Try to identify platform from first or last word
                platform_word = parts[0].lower()
                url_part = ' '.join(parts[1:])
                
                # Check if platform is at the end instead
                if any(k in platform_word for p, keywords in PLATFORMS.items() for k in keywords):
                    platform = next(p for p, keywords in PLATFORMS.items() 
                                 if any(k in platform_word for k in keywords))
                else:
                    platform_word = parts[-1].lower()
                    if any(k in platform_word for p, keywords in PLATFORMS.items() for k in keywords):
                        platform = next(p for p, keywords in PLATFORMS.items() 
                                     if any(k in platform_word for k in keywords))
                        url_part = ' '.join(parts[:-1])
                    else:
                        continue
                        
                # Clean up URL
                url = url_part.strip()
                if not url.startswith(('http://', 'https://')):
                    url = f"https://{url}"
                    
                streaming[platform] = url
                
        return streaming

    async def handle_social_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle social media input."""
        text = update.message.text.strip()
        
        # Parse social media handles
        social_media = self._parse_social_media(text)
        if social_media:
            context.user_data['social_media'] = social_media
        
        # Show what was understood
        if social_media:
            confirmation = "I understood these social media profiles:\n\n"
            for platform, handle in social_media.items():
                confirmation += f"• {platform.title()}: {handle}\n"
            confirmation += "\nIs this correct? (Yes/No)"
            
            keyboard = [["Yes", "No"]]
            await update.message.reply_text(
                confirmation,
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return AWAITING_SOCIAL_MEDIA
            
        # Move to next step
        await update.message.reply_text(
            "Great! Now for your streaming platform profiles.\n"
            "You can:\n"
            "• Paste links directly\n"
            "• List platform name and link\n"
            "• Use any format (Spotify: link or Spotify - link etc)\n\n"
            "Example:\n"
            "spotify.com/artist/...\n"
            "Apple Music: music.apple.com/...\n"
            "soundcloud - soundcloud.com/...\n\n"
            "Or type 'skip' to skip this step.",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_STREAMING_PROFILES

    async def handle_streaming_profiles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle streaming profiles input."""
        text = update.message.text.strip()
        
        # If confirming social media
        if text.lower() in ['yes', 'no']:
            if text.lower() == 'no':
                await update.message.reply_text(
                    "Please enter your social media profiles again:",
                    reply_markup=ForceReply(selective=True)
                )
                return AWAITING_SOCIAL_MEDIA
            
            # If yes, move to streaming profiles
            await update.message.reply_text(
                "Great! Now for your streaming platform profiles.\n"
                "You can:\n"
                "• Paste links directly\n"
                "• List platform name and link\n"
                "• Use any format (Spotify: link or Spotify - link etc)\n\n"
                "Example:\n"
                "spotify.com/artist/...\n"
                "Apple Music: music.apple.com/...\n"
                "soundcloud - soundcloud.com/...\n\n"
                "Or type 'skip' to skip this step.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_STREAMING_PROFILES
        
        # Parse streaming profiles
        streaming = self._parse_streaming_profiles(text)
        if streaming:
            context.user_data['streaming_profiles'] = streaming
            
            # Show what was understood
            confirmation = "I understood these streaming profiles:\n\n"
            for platform, url in streaming.items():
                confirmation += f"• {platform.title()}: {url}\n"
            confirmation += "\nIs this correct? (Yes/No)"
            
            keyboard = [["Yes", "No"]]
            await update.message.reply_text(
                confirmation,
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return AWAITING_STREAMING_PROFILES
            
        # If skipped or no profiles entered, move to profile confirmation
        return await self._show_profile_summary(update, context)

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

    async def _analyze_profile_and_suggest(self, profile: ArtistProfile) -> Dict[str, Any]:
        """Analyze profile and generate personalized suggestions."""
        suggestions = {
            "quick_actions": [],
            "tutorials": [],
            "templates": []
        }
        
        # Initialize priority queue for suggestions
        action_scores = {}
        tutorial_scores = {}
        template_scores = {}
        
        # Base suggestions by career stage
        if profile.career_stage == "emerging":
            action_scores.update({
                ("Set up your first project", "Create a release plan", "/newproject"): 5,
                ("Build your online presence", "Manage your social media", "/social"): 5,
                ("Start tracking goals", "Set measurable targets", "/goals"): 4,
                ("Plan your promotion", "Create marketing strategy", "/marketing"): 3,
                ("Set up team", "Add your first team member", "/team"): 2
            })
            tutorial_scores.update({
                "Project Planning Basics": 5,
                "Social Media Strategy": 5,
                "Goal Setting Guide": 4,
                "Music Marketing 101": 3,
                "Team Management Basics": 2
            })
            template_scores.update({
                "First Release Plan": 5,
                "Social Media Calendar": 5,
                "Basic Marketing Plan": 4,
                "Goal Tracking Sheet": 3,
                "Team Structure Template": 2
            })
        elif profile.career_stage == "established":
            action_scores.update({
                ("Analyze your metrics", "Track your growth", "/analytics"): 5,
                ("Manage your team", "Coordinate with collaborators", "/team"): 5,
                ("Plan your next release", "Create a campaign", "/newproject"): 4,
                ("Optimize promotion", "Enhance marketing strategy", "/marketing"): 4,
                ("Schedule events", "Plan performances", "/events"): 3
            })
            tutorial_scores.update({
                "Advanced Analytics": 5,
                "Team Management": 5,
                "Campaign Planning": 4,
                "Marketing Strategy": 4,
                "Event Planning": 3
            })
            template_scores.update({
                "Release Campaign": 5,
                "Team Workflow": 5,
                "Growth Strategy": 4,
                "Marketing Calendar": 4,
                "Event Planning Guide": 3
            })
        else:  # veteran
            action_scores.update({
                ("Portfolio management", "Manage your catalog", "/portfolio"): 5,
                ("Revenue tracking", "Financial overview", "/finance"): 5,
                ("Team expansion", "Grow your team", "/team"): 4,
                ("Brand strategy", "Enhance your brand", "/brand"): 4,
                ("Investment planning", "Manage investments", "/invest"): 3
            })
            tutorial_scores.update({
                "Portfolio Management": 5,
                "Financial Planning": 5,
                "Team Scaling": 4,
                "Brand Development": 4,
                "Investment Strategy": 3
            })
            template_scores.update({
                "Business Plan": 5,
                "Investment Strategy": 5,
                "Team Structure": 4,
                "Brand Guidelines": 4,
                "Financial Forecast": 3
            })
            
        # Analyze goals and adjust scores
        for goal in profile.goals:
            goal_lower = goal.lower()
            
            # Release-related goals
            if any(word in goal_lower for word in ["release", "album", "ep", "single"]):
                action_scores[("Plan your release", "Create a release timeline", "/newproject")] = 10
                tutorial_scores["Release Planning"] = 10
                template_scores["Release Timeline"] = 10
                
            # Streaming/listener goals
            if any(word in goal_lower for word in ["stream", "listener", "spotify", "apple"]):
                action_scores[("Growth tracking", "Monitor streaming metrics", "/analytics")] = 10
                tutorial_scores["Streaming Growth"] = 10
                template_scores["Streaming Strategy"] = 10
                
            # Performance goals
            if any(word in goal_lower for word in ["tour", "perform", "show", "gig", "concert"]):
                action_scores[("Event planning", "Schedule performances", "/events")] = 10
                tutorial_scores["Event Planning"] = 10
                template_scores["Tour Planning"] = 10
                
            # Marketing goals
            if any(word in goal_lower for word in ["promot", "market", "advertis", "reach"]):
                action_scores[("Marketing strategy", "Plan your promotion", "/marketing")] = 10
                tutorial_scores["Marketing Strategy"] = 10
                template_scores["Marketing Plan"] = 10
                
            # Team goals
            if any(word in goal_lower for word in ["team", "manage", "collaborat"]):
                action_scores[("Team management", "Build your team", "/team")] = 10
                tutorial_scores["Team Building"] = 10
                template_scores["Team Structure"] = 10
                
        # Consider social media presence
        if not profile.social_media:
            action_scores[("Set up social profiles", "Add your social media", "/social")] = 9
            tutorial_scores["Social Media Setup"] = 9
            template_scores["Social Media Plan"] = 9
            
        # Consider streaming presence
        if not profile.streaming_profiles:
            action_scores[("Set up streaming profiles", "Add your music platforms", "/streaming")] = 9
            tutorial_scores["Music Distribution"] = 9
            template_scores["Distribution Plan"] = 9
            
        # Sort by score and get top suggestions
        suggestions["quick_actions"] = [action for action, _ in sorted(action_scores.items(), key=lambda x: x[1], reverse=True)][:5]
        suggestions["tutorials"] = [tutorial for tutorial, _ in sorted(tutorial_scores.items(), key=lambda x: x[1], reverse=True)][:5]
        suggestions["templates"] = [template for template, _ in sorted(template_scores.items(), key=lambda x: x[1], reverse=True)][:5]
        
        return suggestions

    async def _show_quick_start_dashboard(self, update: Update, profile: ArtistProfile, suggestions: Dict[str, Any]) -> None:
        """Show the personalized quick start dashboard."""
        # Create welcome message
        message = (
            f"Welcome, {profile.name}! 🎵\n\n"
            "I've analyzed your profile and prepared some personalized suggestions to help you get started.\n\n"
            "🎯 Recommended Actions:\n"
        )
        
        # Add quick actions
        keyboard = []
        for action, description, command in suggestions["quick_actions"][:3]:  # Show top 3
            message += f"• {action}: {description}\n"
            keyboard.append([InlineKeyboardButton(action, callback_data=command[1:])])  # Remove / from command
            
        message += "\n📚 Available Tutorials:\n"
        for tutorial in suggestions["tutorials"][:3]:
            message += f"• {tutorial}\n"
            
        message += "\n✨ Suggested Templates:\n"
        for template in suggestions["templates"][:3]:
            message += f"• {template}\n"
            
        # Add navigation buttons
        keyboard.extend([
            [InlineKeyboardButton("View All Commands", callback_data="show_commands")],
            [InlineKeyboardButton("View Profile", callback_data="profile_view")],
            [InlineKeyboardButton("Start Tutorial", callback_data="start_tutorial")]
        ])
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_profile_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle profile confirmation."""
        choice = update.message.text.lower()
        
        if choice == 'confirm profile':
            try:
                # Create ArtistProfile object
                profile = ArtistProfile(
                    id=str(update.effective_user.id),
                    name=context.user_data.get('name', ''),
                    genre=context.user_data.get('genre', ''),
                    career_stage=context.user_data.get('career_stage', ''),
                    goals=context.user_data.get('goals', []),
                    strengths=context.user_data.get('strengths', []),
                    areas_for_improvement=context.user_data.get('improvements', []),
                    achievements=context.user_data.get('achievements', []),
                    social_media=context.user_data.get('social_media', {}),
                    streaming_profiles=context.user_data.get('streaming_profiles', {}),
                    brand_guidelines={
                        "description": "Default brand guidelines",
                        "colors": [],
                        "fonts": [],
                        "tone": "professional"
                    },
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                # Save profile
                self.bot.profiles[str(update.effective_user.id)] = profile
                
                # Analyze profile and get suggestions
                suggestions = await self._analyze_profile_and_suggest(profile)
                
                # Show success message
                await update.message.reply_text(
                    "✨ Profile created successfully! ✨\n\n"
                    "I'll help you get started with managing your music career."
                )
                
                # Show personalized dashboard
                await self._show_quick_start_dashboard(update, profile, suggestions)
                
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"Error creating profile: {str(e)}")
                await update.message.reply_text(
                    "Sorry, there was an error creating your profile. Please try again."
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

    async def _show_profile_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show profile summary and confirmation options."""
        # Create profile summary
        profile_text = self._create_profile_summary(context.user_data)
        
        # Create confirmation keyboard
        keyboard = [
            ["Confirm Profile"],
            ["Edit Profile"],
            ["Start Over"]
        ]
        
        # Show summary
        await update.message.reply_text(
            "Here's your profile summary:\n\n"
            f"{profile_text}\n\n"
            "What would you like to do?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return CONFIRM_PROFILE 

    async def handle_dashboard_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callbacks from the personalized dashboard."""
        query = update.callback_query
        await query.answer()  # Acknowledge the button click
        
        try:
            # Get user profile
            user_id = str(update.effective_user.id)
            profile = self.bot.profiles.get(user_id)
            if not profile:
                await query.message.reply_text(
                    "Sorry, I couldn't find your profile. Please use /start to set up your profile."
                )
                return
                
            # Handle different actions
            if query.data == "newproject":
                # Create new project
                await query.message.reply_text(
                    "Let's create your first project! 🚀\n\n"
                    "I'll guide you through setting up a new project step by step."
                )
                await self.bot.project_handlers.start_project_creation(query.message, context)
                
            elif query.data == "social":
                # Social media management
                social_profiles = profile.social_media
                if not social_profiles:
                    message = (
                        "I notice you haven't added any social media profiles yet.\n"
                        "Would you like to add them now?"
                    )
                    keyboard = [[
                        InlineKeyboardButton("Add Profiles", callback_data="profile_edit_social"),
                        InlineKeyboardButton("Skip for Now", callback_data="show_menu")
                    ]]
                else:
                    message = "Here are your current social media profiles:\n\n"
                    for platform, handle in social_profiles.items():
                        message += f"• {platform.title()}: {handle}\n"
                    message += "\nWhat would you like to do?"
                    keyboard = [[
                        InlineKeyboardButton("Update Profiles", callback_data="profile_edit_social"),
                        InlineKeyboardButton("View Analytics", callback_data="social_analytics")
                    ]]
                
                await query.message.edit_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            elif query.data == "goals":
                # Goal management
                goals = profile.goals
                if not goals:
                    message = "Let's set up some goals for your music career!"
                else:
                    message = "Here are your current goals:\n\n"
                    for goal in goals:
                        message += f"• {goal}\n"
                    message += "\nWould you like to update them or track progress?"
                    
                keyboard = [[
                    InlineKeyboardButton("Set New Goals", callback_data="goal_create"),
                    InlineKeyboardButton("Track Progress", callback_data="goal_progress")
                ]]
                await query.message.edit_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            elif query.data == "analytics":
                # Show analytics dashboard
                await query.message.edit_text(
                    "📊 Analytics Dashboard\n\n"
                    "I'll help you track your growth across platforms:\n"
                    "• Social media engagement\n"
                    "• Streaming performance\n"
                    "• Goal progress\n"
                    "• Project milestones",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("View Details", callback_data="show_analytics"),
                        InlineKeyboardButton("Back to Menu", callback_data="show_menu")
                    ]])
                )
                
            elif query.data == "events":
                # Event planning
                await query.message.edit_text(
                    "🎵 Event Planning\n\n"
                    "I can help you:\n"
                    "• Schedule performances\n"
                    "• Track event details\n"
                    "• Manage bookings\n"
                    "• Coordinate with venues",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Schedule Event", callback_data="event_create"),
                        InlineKeyboardButton("View Calendar", callback_data="event_calendar")
                    ]])
                )
                
            elif query.data == "show_commands":
                # Show all available commands
                commands = (
                    "🎵 Available Commands:\n\n"
                    "Core Commands:\n"
                    "/start - Start/restart bot\n"
                    "/help - Show this help message\n"
                    "/menu - Show main menu\n\n"
                    "Project Management:\n"
                    "/newproject - Create new project\n"
                    "/projects - View all projects\n\n"
                    "Goal Tracking:\n"
                    "/goals - Manage goals\n"
                    "/progress - Track progress\n\n"
                    "Team Management:\n"
                    "/team - Manage team\n"
                    "/tasks - Manage tasks\n\n"
                    "Analytics:\n"
                    "/analytics - View analytics\n"
                    "/reports - Generate reports"
                )
                await query.message.edit_text(
                    commands,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Back to Dashboard", callback_data="show_dashboard")
                    ]])
                )
                
            elif query.data == "start_tutorial":
                # Start interactive tutorial
                await query.message.edit_text(
                    "Welcome to the Artist Manager Tutorial! 🎓\n\n"
                    "I'll guide you through the key features:\n"
                    "1. Project Management\n"
                    "2. Goal Tracking\n"
                    "3. Team Coordination\n"
                    "4. Analytics & Reporting\n\n"
                    "Where would you like to start?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Project Management", callback_data="tutorial_projects")],
                        [InlineKeyboardButton("Goal Tracking", callback_data="tutorial_goals")],
                        [InlineKeyboardButton("Team Coordination", callback_data="tutorial_team")],
                        [InlineKeyboardButton("Analytics", callback_data="tutorial_analytics")],
                        [InlineKeyboardButton("Skip Tutorial", callback_data="show_menu")]
                    ])
                )
                
            elif query.data == "show_dashboard":
                # Show dashboard again
                suggestions = await self._analyze_profile_and_suggest(profile)
                await self._show_quick_start_dashboard(query.message, profile, suggestions)
                
        except Exception as e:
            logger.error(f"Error handling dashboard callback: {str(e)}")
            await query.message.reply_text(
                "Sorry, something went wrong. Please try again or use /help to see available commands."
            ) 