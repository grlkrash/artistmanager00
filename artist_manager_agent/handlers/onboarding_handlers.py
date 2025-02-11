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
import asyncio
import uuid

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_MANAGER_NAME = "AWAITING_MANAGER_NAME"
AWAITING_NAME = "AWAITING_NAME"
AWAITING_GENRE = "AWAITING_GENRE"
AWAITING_SUBGENRE = "AWAITING_SUBGENRE"
AWAITING_INFLUENCES = "AWAITING_INFLUENCES"
AWAITING_SIMILAR_ARTISTS = "AWAITING_SIMILAR_ARTISTS"
AWAITING_CAREER_STAGE = "AWAITING_CAREER_STAGE"
AWAITING_GOALS = "AWAITING_GOALS"
AWAITING_GOALS_CONFIRMATION = "AWAITING_GOALS_CONFIRMATION"
AWAITING_STRENGTHS = "AWAITING_STRENGTHS"
AWAITING_STRENGTHS_CONFIRMATION = "AWAITING_STRENGTHS_CONFIRMATION"
AWAITING_IMPROVEMENTS = "AWAITING_IMPROVEMENTS"
AWAITING_IMPROVEMENTS_CONFIRMATION = "AWAITING_IMPROVEMENTS_CONFIRMATION"
AWAITING_ACHIEVEMENTS = "AWAITING_ACHIEVEMENTS"
AWAITING_SOCIAL_MEDIA = "AWAITING_SOCIAL_MEDIA"
AWAITING_STREAMING_PROFILES = "AWAITING_STREAMING_PROFILES"

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
        logger.info("Initializing onboarding handlers...")
        try:
            handlers = [
                # Only return the conversation handler
                self.get_conversation_handler()
            ]
            logger.info(f"Created {len(handlers)} onboarding handlers")
            return handlers
        except Exception as e:
            logger.error(f"Failed to create onboarding handlers: {str(e)}")
            raise

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
                AWAITING_SUBGENRE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_subgenre)
                ],
                AWAITING_INFLUENCES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_influences)
                ],
                AWAITING_SIMILAR_ARTISTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_similar_artists)
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
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_onboarding),
                CommandHandler("skip", self.skip_current_step)
            ],
            name="onboarding",
            persistent=True,
            per_chat=True,
            per_user=True,
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
        """Start the onboarding process with progressive disclosure."""
        try:
            # Clear any existing state
            context.user_data.clear()
            self.state_manager.clear_state(update.effective_user.id)
            
            # Generate manager name
            manager_name = self._generate_manager_name()
            context.user_data["manager_name"] = manager_name
            
            # Send combined initial message with buttons
            keyboard = [
                [InlineKeyboardButton("Let's Get Started", callback_data="onboard_start")],
                [InlineKeyboardButton("Change Manager Name", callback_data="onboard_change_name")]
            ]
            
            await update.message.reply_text(
                f"Hey! I'm {manager_name} 👋\n\n"
                "I specialize in helping artists like you succeed in today's music industry. "
                "I can help with:\n\n"
                "🎯 Release strategy & planning\n"
                "📈 Marketing & promotion\n"
                "👥 Team coordination\n"
                "📊 Performance tracking\n\n"
                "Ready to start building your success strategy?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return AWAITING_MANAGER_NAME
            
        except Exception as e:
            logger.error(f"Error in start_onboarding: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting the onboarding process. Please try again with /start"
            )
            return ConversationHandler.END

    async def handle_onboard_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle onboarding callbacks."""
        query = update.callback_query
        try:
            await query.answer()
            
            if query.data == "onboard_start":
                # Move directly to name input
                await query.message.reply_text(
                    "What name do you perform under?",
                    reply_markup=ForceReply(selective=True)
                )
                return AWAITING_NAME
                
            elif query.data == "onboard_change_name":
                await query.message.reply_text(
                    "What name would you like me to use?",
                    reply_markup=ForceReply(selective=True)
                )
                return AWAITING_MANAGER_NAME
                
            # Log unhandled callbacks
            logger.warning(f"Unhandled onboard callback: {query.data}")
            return AWAITING_MANAGER_NAME
            
        except Exception as e:
            logger.error(f"Error handling onboard callback: {str(e)}")
            await query.message.reply_text(
                "Sorry, something went wrong. Please try /start to begin again."
            )
            return ConversationHandler.END

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the artist name input with progressive disclosure."""
        try:
            name = update.message.text.strip()
            context.user_data["name"] = name
            
            # Acknowledge and show enthusiasm
            await update.message.reply_text(f"Nice to meet you, {name}! 🎵")
            await asyncio.sleep(1)
            
            # Lead into genre selection with context
            await update.message.reply_text(
                "To help me understand your music better and provide targeted advice, "
                "let's start with your genre."
            )
            await asyncio.sleep(1)
            
            # Present genre options
            keyboard = [
                ["Pop", "Rock", "Hip Hop"],
                ["Electronic", "R&B", "Jazz"],
                ["Classical", "Folk", "Other"]
            ]
            await update.message.reply_text(
                "Which genre best describes your music?",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return AWAITING_GENRE
            
        except Exception as e:
            logger.error(f"Error handling name: {str(e)}")
            await update.message.reply_text(
                "Sorry, I encountered an error. Could you try entering your name again?"
            )
            return AWAITING_NAME

    async def handle_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle genre input with natural conversation flow."""
        try:
            genre = update.message.text.strip()
            context.user_data["genre"] = genre
            
            # Acknowledge genre choice
            await update.message.reply_text(
                f"Ah, {genre}! That's a great space to be in right now. 🎵"
            )
            await asyncio.sleep(1)
            
            # Ask for subgenres with context
            await update.message.reply_text(
                f"Within {genre}, artists often have their own unique blend of styles. "
                "What subgenres would you say your music incorporates?\n\n"
                "You can list multiple, separated by commas.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_SUBGENRE
            
        except Exception as e:
            logger.error(f"Error handling genre: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error. Could you select your genre again?"
            )
            return AWAITING_GENRE

    async def handle_subgenre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle subgenre input with natural conversation flow."""
        try:
            subgenres = [g.strip() for g in update.message.text.split(',')]
            context.user_data["subgenres"] = subgenres
            
            # Acknowledge subgenres
            subgenre_list = ", ".join(subgenres)
            await update.message.reply_text(
                f"That's a great mix! {subgenre_list} gives your sound a unique edge. 🎸"
            )
            await asyncio.sleep(1)
            
            # Lead into influences
            await update.message.reply_text(
                "Every artist has their influences - the ones who shaped their sound and inspired their journey.\n\n"
                "Who would you say are your main musical influences?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_INFLUENCES
            
        except Exception as e:
            logger.error(f"Error handling subgenre: {str(e)}")
            await update.message.reply_text(
                "Sorry, I didn't catch that. Could you list your subgenres again?"
            )
            return AWAITING_SUBGENRE

    async def handle_influences(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle influences input with engaging conversation."""
        try:
            influences = [i.strip() for i in update.message.text.split(',')]
            context.user_data["influences"] = influences
            
            # Acknowledge influences
            await update.message.reply_text(
                "Those are some solid influences! They've definitely left their mark on the industry. 🌟"
            )
            await asyncio.sleep(1)
            
            # Lead into similar artists
            await update.message.reply_text(
                "Now, thinking about today's music scene...\n\n"
                "Which current artists would you say your music is similar to?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_SIMILAR_ARTISTS
            
        except Exception as e:
            logger.error(f"Error handling influences: {str(e)}")
            await update.message.reply_text(
                "I didn't quite get that. Could you share your influences again?"
            )
            return AWAITING_INFLUENCES

    async def handle_similar_artists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle similar artists input with natural progression."""
        try:
            similar_artists = [a.strip() for a in update.message.text.split(',')]
            context.user_data["similar_artists"] = similar_artists
            
            # Acknowledge similar artists
            await update.message.reply_text(
                "Great comparisons! This helps me understand where you fit in today's market. 📊"
            )
            await asyncio.sleep(1)
            
            # Lead into career stage
            await update.message.reply_text(
                "Every artist's journey is unique, and knowing where you are helps me provide better guidance."
            )
            await asyncio.sleep(1)
            
            # Present career stage options
            keyboard = [
                ["Emerging Artist", "Developing Artist"],
                ["Established Artist", "Professional Artist"]
            ]
            await update.message.reply_text(
                "Where would you say you are in your career?",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return AWAITING_CAREER_STAGE
            
        except Exception as e:
            logger.error(f"Error handling similar artists: {str(e)}")
            await update.message.reply_text(
                "I missed that. Could you list those similar artists again?"
            )
            return AWAITING_SIMILAR_ARTISTS

    async def handle_career_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle career stage with supportive conversation."""
        try:
            stage = update.message.text.strip()
            context.user_data["career_stage"] = stage
            
            # Acknowledge career stage with encouragement
            stage_responses = {
                "emerging artist": "Every major artist started exactly where you are. The potential is exciting! 🌱",
                "developing artist": "You've built some momentum - that's great! Time to amplify it. 🚀",
                "established artist": "You've already achieved what many dream of. Let's take it further! ⭐",
                "professional artist": "You've mastered your craft. Let's focus on legacy and innovation. 👑"
            }
            
            await update.message.reply_text(stage_responses.get(stage.lower(), "That's great to know!"))
            await asyncio.sleep(1)
            
            # Lead into goals
            await update.message.reply_text(
                "Now for the exciting part - your goals! 🎯\n\n"
                "These will help me create a strategy that's perfectly aligned with your vision.\n\n"
                "What are your main goals as an artist? You can:\n"
                "• List them one per line\n"
                "• Separate with commas\n"
                "• Be as specific as you like\n\n"
                "Example:\n"
                "Release an EP by end of year\n"
                "Reach 10k monthly listeners\n"
                "Book 5 live shows",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_GOALS
            
        except Exception as e:
            logger.error(f"Error handling career stage: {str(e)}")
            await update.message.reply_text(
                "I didn't catch that. Could you select your career stage again?"
            )
            return AWAITING_CAREER_STAGE

    async def handle_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle goals input with strategic conversation."""
        try:
            goals = [g.strip() for g in update.message.text.split('\n') if g.strip()]
            context.user_data["goals"] = goals
            
            # Format goals for display
            goals_text = "\n".join(f"• {goal}" for goal in goals)
            
            # Show goals and ask for confirmation
            await update.message.reply_text(
                "I've noted down these goals:\n\n"
                f"{goals_text}\n\n"
                "These will help me create targeted strategies for your success. "
                "Would you like to add more goals or are these good to start with?\n\n"
                "Type 'more' to add more goals, or 'continue' to move forward.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_GOALS_CONFIRMATION
            
        except Exception as e:
            logger.error(f"Error handling goals: {str(e)}")
            await update.message.reply_text(
                "I didn't quite catch those goals. Could you list them again?"
            )
            return AWAITING_GOALS

    async def handle_goals_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle goals confirmation with strategic transition."""
        response = update.message.text.lower().strip()
        
        if response == "more":
            await update.message.reply_text(
                "Sure! What additional goals would you like to add?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_GOALS
            
        # Transition to strengths
        await update.message.reply_text(
            "Great goals! To help achieve them, let's talk about your strengths. 💪\n\n"
            "What would you say are your biggest strengths as an artist?\n\n"
            "This could be anything from:\n"
            "• Technical skills (great vocalist, skilled producer)\n"
            "• Creative aspects (songwriting, unique sound)\n"
            "• Business skills (networking, social media)\n"
            "• Personal qualities (work ethic, creativity)",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_STRENGTHS

    async def handle_strengths(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle strengths input with positive reinforcement."""
        try:
            strengths = [s.strip() for s in update.message.text.split('\n') if s.strip()]
            context.user_data["strengths"] = strengths
            
            # Format strengths for display
            strengths_text = "\n".join(f"• {strength}" for strength in strengths)
            
            # Acknowledge strengths and ask for confirmation
            await update.message.reply_text(
                "Those are fantastic strengths! I've noted:\n\n"
                f"{strengths_text}\n\n"
                "Would you like to add any other strengths, or shall we continue?\n\n"
                "Type 'more' to add more, or 'continue' to move forward.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_STRENGTHS_CONFIRMATION
            
        except Exception as e:
            logger.error(f"Error handling strengths: {str(e)}")
            await update.message.reply_text(
                "I missed that. Could you share your strengths again?"
            )
            return AWAITING_STRENGTHS

    async def handle_strengths_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle strengths confirmation and transition to improvements."""
        response = update.message.text.lower().strip()
        
        if response == "more":
            await update.message.reply_text(
                "Of course! What other strengths would you like to add?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_STRENGTHS
            
        # Transition to improvements with context
        await update.message.reply_text(
            "Excellent! Now, every artist has areas they want to improve - "
            "that's what keeps us growing and evolving. 🌱\n\n"
            "What areas would you like to focus on developing?\n\n"
            "This helps me identify opportunities for growth and learning.",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_IMPROVEMENTS

    async def handle_improvements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle improvements input with supportive conversation."""
        try:
            improvements = [i.strip() for i in update.message.text.split('\n') if i.strip()]
            context.user_data["improvements"] = improvements
            
            # Format improvements for display
            improvements_text = "\n".join(f"• {improvement}" for improvement in improvements)
            
            # Acknowledge improvements and ask for confirmation
            await update.message.reply_text(
                "These are great areas to focus on! I've noted:\n\n"
                f"{improvements_text}\n\n"
                "Would you like to add any other areas for improvement?\n\n"
                "Type 'more' to add more, or 'continue' to move forward.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_IMPROVEMENTS_CONFIRMATION
            
        except Exception as e:
            logger.error(f"Error handling improvements: {str(e)}")
            await update.message.reply_text(
                "I didn't catch that. Could you share those areas for improvement again?"
            )
            return AWAITING_IMPROVEMENTS

    async def handle_improvements_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle improvements confirmation and transition to achievements."""
        response = update.message.text.lower().strip()
        
        if response == "more":
            await update.message.reply_text(
                "Sure! What other areas would you like to add?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_IMPROVEMENTS
            
        # Transition to achievements with context
        await update.message.reply_text(
            "Perfect! Now let's celebrate your achievements! 🎉\n\n"
            "What are some of your proudest moments or biggest achievements as an artist?\n\n"
            "This could be anything from:\n"
            "• Release milestones\n"
            "• Performance highlights\n"
            "• Streaming achievements\n"
            "• Personal growth moments",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_ACHIEVEMENTS

    async def handle_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle achievements with celebration and transition to social media."""
        try:
            achievements = [a.strip() for a in update.message.text.split('\n') if a.strip()]
            context.user_data["achievements"] = achievements
            
            # Celebrate achievements
            await update.message.reply_text(
                "Those are impressive achievements! 🌟 Each one is a stepping stone to even greater success."
            )
            await asyncio.sleep(1)
            
            # Transition to social media
            await update.message.reply_text(
                "Now, let's talk about your online presence.\n\n"
                "What social media platforms are you active on?\n\n"
                "You can list them in any format:\n"
                "• Instagram: @handle\n"
                "• Twitter - @handle\n"
                "• TikTok @handle\n\n"
                "Or simply type 'skip' if you prefer not to share.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_SOCIAL_MEDIA
            
        except Exception as e:
            logger.error(f"Error handling achievements: {str(e)}")
            await update.message.reply_text(
                "I missed those achievements. Could you share them again?"
            )
            return AWAITING_ACHIEVEMENTS

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
        try:
            text = update.message.text.strip()
            
            if text.lower() == "skip":
                context.user_data["social_media"] = {}
                return await self.handle_streaming_profiles(update, context)
            
            # Parse social media with more lenient validation
            social_media = {}
            entries = text.split('\n')
            
            for entry in entries:
                entry = entry.strip()
                if not entry:
                    continue
                    
                # Accept various formats
                if '@' in entry:
                    platform, handle = entry.split('@', 1)
                    social_media[platform.strip().lower()] = '@' + handle.strip()
                elif ':' in entry:
                    platform, handle = entry.split(':', 1)
                    social_media[platform.strip().lower()] = handle.strip()
                elif ' ' in entry:
                    platform, handle = entry.split(' ', 1)
                    social_media[platform.strip().lower()] = handle.strip()
                else:
                    continue
            
            if not social_media:
                await update.message.reply_text(
                    "Please enter your social media handles in any of these formats:\n"
                    "platform @handle\n"
                    "platform: handle\n"
                    "Or type 'skip' to continue."
                )
                return AWAITING_SOCIAL_MEDIA
            
            context.user_data["social_media"] = social_media
            return await self.handle_streaming_profiles(update, context)
            
        except Exception as e:
            logger.error(f"Error handling social media: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your social media. Please try again or type 'skip'."
            )
            return AWAITING_SOCIAL_MEDIA

    async def handle_streaming_profiles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle streaming profiles with natural conversation flow."""
        text = update.message.text.strip()
        
        if text.lower() == "skip":
            # Move to profile summary with context
            await update.message.reply_text(
                "No problem! We can always add streaming profiles later. 👍"
            )
            await asyncio.sleep(1)
            return await self._show_profile_summary(update, context)
        
        # Parse streaming profiles
        streaming = self._parse_streaming_profiles(text)
        if streaming:
            context.user_data['streaming_profiles'] = streaming
            
            # Show what was understood with enthusiasm
            confirmation = (
                "Great! I've found your profiles on:\n\n"
                + "\n".join(f"• {platform.title()}: {url}" for platform, url in streaming.items())
                + "\n\nDoes this look correct? (Yes/No)"
            )
            
            keyboard = [["Yes", "No"]]
            await update.message.reply_text(
                confirmation,
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return AWAITING_STREAMING_PROFILES
            
        # If no profiles were parsed
        await update.message.reply_text(
            "I couldn't quite understand those links. Could you try again with this format?\n\n"
            "• Spotify: spotify.com/artist/...\n"
            "• Apple Music - music.apple.com/...\n"
            "• SoundCloud: soundcloud.com/...\n\n"
            "Or type 'skip' to continue without adding profiles.",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_STREAMING_PROFILES

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
                ("Create Release Plan", "Plan your first release", "newproject"): 10,
                ("Set Social Strategy", "Optimize your social presence", "social"): 9,
                ("Track Goals", "Set and monitor your goals", "goals"): 8,
                ("Build Team", "Start building your team", "team"): 7,
                ("Plan Marketing", "Create marketing strategy", "marketing"): 6
            })
            
            # Specific tutorials for emerging artists
            tutorial_scores.update({
                "Building Your Brand": 10,
                "Social Media Growth": 9,
                "First Release Guide": 8,
                "Music Marketing Basics": 7,
                "Team Building 101": 6
            })
            
            # Templates for emerging artists
            template_scores.update({
                "Release Timeline": 10,
                "Social Media Calendar": 9,
                "Goal Tracking Sheet": 8,
                "Basic Marketing Plan": 7,
                "Team Structure": 6
            })
        elif profile.career_stage == "established":
            action_scores.update({
                ("Growth Analysis", "Track your metrics", "analytics"): 10,
                ("Team Management", "Manage your team", "team"): 9,
                ("Release Campaign", "Plan your next release", "newproject"): 8,
                ("Marketing Strategy", "Optimize promotion", "marketing"): 7,
                ("Event Planning", "Schedule performances", "events"): 6
            })
            
            # Advanced tutorials
            tutorial_scores.update({
                "Advanced Analytics": 10,
                "Team Leadership": 9,
                "Campaign Strategy": 8,
                "Advanced Marketing": 7,
                "Tour Planning": 6
            })
            
            # Professional templates
            template_scores.update({
                "Campaign Strategy": 10,
                "Team Workflow": 9,
                "Analytics Dashboard": 8,
                "Marketing Calendar": 7,
                "Event Planning": 6
            })
        else:  # veteran
            action_scores.update({
                ("Portfolio Management", "Manage your catalog", "portfolio"): 10,
                ("Revenue Analysis", "Track financials", "finance"): 9,
                ("Team Expansion", "Scale your team", "team"): 8,
                ("Brand Strategy", "Enhance your brand", "brand"): 7,
                ("Investment Planning", "Manage investments", "invest"): 6
            })
            
            # Expert tutorials
            tutorial_scores.update({
                "Portfolio Strategy": 10,
                "Financial Planning": 9,
                "Team Scaling": 8,
                "Brand Development": 7,
                "Investment Guide": 6
            })
            
            # Professional templates
            template_scores.update({
                "Business Plan": 10,
                "Investment Strategy": 9,
                "Team Structure": 8,
                "Brand Guidelines": 7,
                "Financial Model": 6
            })
            
        # Analyze goals and adjust scores
        for goal in profile.goals:
            goal_lower = goal.lower()
            
            # Release-related goals
            if any(word in goal_lower for word in ["release", "album", "ep", "single"]):
                action_scores[("Plan Release", "Create release timeline", "newproject")] = 15
                tutorial_scores["Release Strategy"] = 15
                template_scores["Release Timeline"] = 15
                
            # Streaming/listener goals
            if any(word in goal_lower for word in ["stream", "listener", "spotify", "apple"]):
                action_scores[("Track Growth", "Monitor streaming metrics", "analytics")] = 15
                tutorial_scores["Streaming Growth"] = 15
                template_scores["Streaming Strategy"] = 15
                
            # Performance goals
            if any(word in goal_lower for word in ["tour", "perform", "show", "gig", "concert"]):
                action_scores[("Plan Events", "Schedule performances", "events")] = 15
                tutorial_scores["Tour Planning"] = 15
                template_scores["Tour Strategy"] = 15
                
            # Marketing goals
            if any(word in goal_lower for word in ["promot", "market", "advertis", "reach"]):
                action_scores[("Marketing Plan", "Create promotion strategy", "marketing")] = 15
                tutorial_scores["Marketing Strategy"] = 15
                template_scores["Marketing Plan"] = 15
                
            # Team goals
            if any(word in goal_lower for word in ["team", "manage", "collaborat"]):
                action_scores[("Team Building", "Grow your team", "team")] = 15
                tutorial_scores["Team Management"] = 15
                template_scores["Team Structure"] = 15
                
        # Consider areas for improvement
        for area in profile.areas_for_improvement:
            area_lower = area.lower()
            
            # Marketing improvements
            if any(word in area_lower for word in ["market", "promot", "brand"]):
                action_scores[("Marketing Strategy", "Improve your marketing", "marketing")] = 12
                tutorial_scores["Marketing Masterclass"] = 12
                
            # Performance improvements
            if any(word in area_lower for word in ["perform", "stage", "live"]):
                action_scores[("Performance Planning", "Improve live shows", "events")] = 12
                tutorial_scores["Stage Presence"] = 12
                
            # Production improvements
            if any(word in area_lower for word in ["produc", "mix", "master"]):
                action_scores[("Production Tools", "Enhance your sound", "music")] = 12
                tutorial_scores["Production Tips"] = 12
                
        # Sort by score and get top suggestions
        suggestions["quick_actions"] = sorted(
            [(title, desc, cmd) for (title, desc, cmd), score in action_scores.items()],
            key=lambda x: action_scores[(x[0], x[1], x[2])],
            reverse=True
        )[:5]

        suggestions["tutorials"] = sorted(
            [(title, score) for title, score in tutorial_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        suggestions["templates"] = sorted(
            [(title, score) for title, score in template_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
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
            keyboard.append([InlineKeyboardButton(action, callback_data=f"dashboard_action_{command}")])
            
        message += "\n📚 Available Tutorials:\n"
        for tutorial, _ in suggestions["tutorials"][:3]:
            message += f"• {tutorial}\n"
            
        message += "\n✨ Suggested Templates:\n"
        for template, _ in suggestions["templates"][:3]:
            message += f"• {template}\n"
            
        # Add navigation buttons with consistent patterns
        keyboard.extend([
            [InlineKeyboardButton("View All Commands", callback_data="dashboard_commands")],
            [InlineKeyboardButton("View Profile", callback_data="dashboard_profile")],
            [InlineKeyboardButton("Start Tutorial", callback_data="dashboard_tutorial")]
        ])
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_profile_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle profile confirmation with enthusiasm."""
        response = update.message.text.strip()
        
        if response == "Perfect! Let's Begin":
            # Create the profile
            profile_data = {
                "id": str(uuid.uuid4()),
                "name": context.user_data.get("name"),
                "genre": context.user_data.get("genre"),
                "subgenres": context.user_data.get("subgenres", []),
                "influences": context.user_data.get("influences", []),
                "similar_artists": context.user_data.get("similar_artists", []),
                "career_stage": context.user_data.get("career_stage"),
                "goals": context.user_data.get("goals", []),
                "strengths": context.user_data.get("strengths", []),
                "areas_for_improvement": context.user_data.get("improvements", []),
                "achievements": context.user_data.get("achievements", []),
                "social_media": context.user_data.get("social_media", {}),
                "streaming_profiles": context.user_data.get("streaming_profiles", {}),
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Save profile
            profile = ArtistProfile(**profile_data)
            self.bot.profiles[str(profile.id)] = profile
            
            # Show success message and next steps
            await update.message.reply_text(
                f"🎉 Welcome aboard, {profile.name}! I'm excited to start this journey with you.\n\n"
                "I'll be your dedicated manager, helping you:\n"
                "• Achieve your goals\n"
                "• Grow your career\n"
                "• Track your progress\n"
                "• Make strategic decisions\n\n"
                "Ready to get started?"
            )
            await asyncio.sleep(1)
            
            # Show quick actions with proper callback patterns
            keyboard = [
                [InlineKeyboardButton("Set First Goal", callback_data="goal_create_new")],
                [InlineKeyboardButton("View Dashboard", callback_data="dashboard_view")],
                [InlineKeyboardButton("Explore Features", callback_data="dashboard_help")]
            ]
            
            await update.message.reply_text(
                "What would you like to do first?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return ConversationHandler.END
            
        else:
            # Offer edit options
            keyboard = [
                ["Basic Info", "Genre & Style"],
                ["Goals & Vision", "Strengths & Growth"],
                ["Achievements", "Online Presence"],
                ["Start Fresh"]
            ]
            
            await update.message.reply_text(
                "No problem! What would you like to edit?",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return AWAITING_EDIT_CHOICE

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
        """Show profile summary with engaging presentation."""
        try:
            # Build profile summary with personality
            summary = "🎵 Here's what I know about you so far:\n\n"
            
            # Basic info with context
            summary += f"Name: {context.user_data.get('name', 'Not specified')}\n"
            summary += f"Genre: {context.user_data.get('genre', 'Not specified')}"
            
            # Add subgenres if available
            if subgenres := context.user_data.get('subgenres'):
                summary += f"\nSubgenres: {', '.join(subgenres)}"
            
            # Add influences with context
            if influences := context.user_data.get('influences'):
                summary += f"\n\n🎸 Influenced by:\n"
                summary += "\n".join(f"• {influence}" for influence in influences)
            
            # Add similar artists
            if similar := context.user_data.get('similar_artists'):
                summary += f"\n\n🎤 Similar sound to:\n"
                summary += "\n".join(f"• {artist}" for artist in similar)
            
            # Career stage and goals
            summary += f"\n\n📈 Career Stage: {context.user_data.get('career_stage', 'Not specified')}\n"
            if goals := context.user_data.get('goals'):
                summary += "\n🎯 Goals:\n"
                summary += "\n".join(f"• {goal}" for goal in goals)
            
            # Strengths and improvements
            if strengths := context.user_data.get('strengths'):
                summary += "\n\n💪 Strengths:\n"
                summary += "\n".join(f"• {strength}" for strength in strengths)
            
            if improvements := context.user_data.get('improvements'):
                summary += "\n\n🌱 Areas for Growth:\n"
                summary += "\n".join(f"• {improvement}" for improvement in improvements)
            
            # Achievements
            if achievements := context.user_data.get('achievements'):
                summary += "\n\n🏆 Achievements:\n"
                summary += "\n".join(f"• {achievement}" for achievement in achievements)
            
            # Online presence
            if social := context.user_data.get('social_media'):
                summary += "\n\n📱 Social Media:\n"
                summary += "\n".join(f"• {platform.title()}: {handle}" for platform, handle in social.items())
            
            if streaming := context.user_data.get('streaming_profiles'):
                summary += "\n\n🎧 Streaming Platforms:\n"
                summary += "\n".join(f"• {platform.title()}: {url}" for platform, url in streaming.items())
            
            # Send summary with confirmation options
            keyboard = [
                ["Perfect! Let's Begin"],
                ["I Need to Edit Something"]
            ]
            
            await update.message.reply_text(
                f"{summary}\n\n"
                "How does this look? Ready to start working together?",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            
            return AWAITING_PROFILE_CONFIRMATION
            
        except Exception as e:
            logger.error(f"Error showing profile summary: {str(e)}")
            await update.message.reply_text(
                "I encountered an error creating your profile summary. "
                "Would you like to try again or start fresh?",
                reply_markup=ReplyKeyboardMarkup([["Start Fresh"], ["Try Again"]], one_time_keyboard=True)
            )
            return AWAITING_PROFILE_CONFIRMATION

    async def handle_dashboard_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callbacks from the personalized dashboard."""
        query = update.callback_query
        
        try:
            # Try to answer the callback query, but don't fail if it's expired
            try:
                await query.answer()
            except Exception as e:
                if "Query is too old" in str(e):
                    # For expired queries, send a new message instead
                    await query.message.reply_text(
                        "This button has expired. Please use /start to begin a new session."
                    )
                    return
                logger.warning(f"Could not answer callback query: {str(e)}")
            
            # Route to appropriate handler based on prefix
            callback_data = query.data
            logger.info(f"Routing callback: {callback_data}")
            
            if callback_data == "start_onboarding":
                await self.start_onboarding(update, context)
                return
            
            # Send a new message for expired buttons
            await query.message.reply_text(
                "Please use /start to begin a new session with fresh options."
            )
                
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
            await query.message.reply_text(
                "Please use /start to begin a new session."
            ) 