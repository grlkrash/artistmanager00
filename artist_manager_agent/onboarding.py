from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters, CallbackQueryHandler
)
from pydantic import BaseModel
import random
import re
import logging
from artist_manager_agent.log import logger
from artist_manager_agent.models import ArtistProfile

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
) = range(19)  # Updated range for all states

class ArtistContext(BaseModel):
    """Extended artist context for better guidance."""
    influences: List[str] = []
    style_description: str = ""
    target_audience: List[str] = []
    similar_artists: List[str] = []
    preferred_collaboration_types: List[str] = []
    creative_process: str = ""
    production_preferences: Dict[str, Any] = {}
    manager_name: str = ""  # Add manager name field

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

class OnboardingWizard:
    def __init__(self, agent: Any):
        self.agent = agent
        self.temp_data: Dict[str, Any] = {}
        self._load_name_data()
        self.state_manager = StateManager()

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
                "Let's get started with setting up your artist profile! "
                "First, what's your artist name?"
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
            
            await update.message.reply_text(
                f"Great to meet you, {name}! What genre best describes your music?"
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
        await update.message.reply_text(
            "What's your current career stage? (emerging/established/veteran)"
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
            "What are your main goals as an artist? (List them separated by commas)"
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
        await update.message.reply_text(
            f"I understood these goals:\n\n{goals_str}\n\n"
            "Is this correct? (yes/no)\n"
            "If yes, let's move on to your strengths.\n"
            "If no, please enter your goals again."
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
                "Good at social media engagement"
            )
            return AWAITING_STRENGTHS
        else:
            await update.message.reply_text("Okay, please enter your goals again.")
            return AWAITING_GOALS

    async def handle_strengths(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the strengths input."""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Ensure we're in the correct state
        current_state = self.state_manager.get_current_state(user_id)
        if current_state != AWAITING_STRENGTHS:
            logger.warning(f"Unexpected state for handle_strengths: {current_state}")
            await update.message.reply_text(
                "Sorry, there was a confusion in the conversation flow. "
                "Let's start over with your strengths. What are your strengths as an artist?"
            )
            await self.state_manager.transition_to(user_id, AWAITING_STRENGTHS)
            return AWAITING_STRENGTHS
        
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
                "• Use bullet points\n\n"
                "Example:\n"
                "Strong vocal range\n"
                "Experienced with live performances\n"
                "Good at social media engagement"
            )
            return AWAITING_STRENGTHS
            
        context.user_data['temp_strengths'] = strengths
        
        # Show what was understood
        strengths_str = "\n".join(f"• {strength}" for strength in strengths)
        
        # Transition to confirmation state
        if await self.state_manager.transition_to(user_id, AWAITING_STRENGTHS_CONFIRMATION):
            await update.message.reply_text(
                f"I understood these strengths:\n\n{strengths_str}\n\n"
                "Is this correct? (yes/no)\n"
                "If yes, let's move on to areas you'd like to improve.\n"
                "If no, please enter your strengths again."
            )
            return AWAITING_STRENGTHS_CONFIRMATION
        else:
            logger.error(f"Failed to transition state for user {user_id}")
            return AWAITING_STRENGTHS

    async def handle_strengths_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle confirmation of strengths."""
        user_id = update.effective_user.id
        response = update.message.text.lower()
        
        # Ensure we're in the correct state
        current_state = self.state_manager.get_current_state(user_id)
        if current_state != AWAITING_STRENGTHS_CONFIRMATION:
            logger.warning(f"Unexpected state for handle_strengths_confirmation: {current_state}")
            return current_state
        
        if response == 'yes':
            context.user_data['strengths'] = context.user_data.pop('temp_strengths')
            
            # Transition to improvements state
            if await self.state_manager.transition_to(user_id, AWAITING_IMPROVEMENTS):
                await update.message.reply_text(
                    "Great! Now, what areas would you like to improve?\n"
                    "You can:\n"
                    "• List them one per line\n"
                    "• Separate them with commas\n"
                    "• Use bullet points\n\n"
                    "Example:\n"
                    "Music theory knowledge\n"
                    "Studio recording techniques\n"
                    "Marketing strategy"
                )
                return AWAITING_IMPROVEMENTS
        else:
            # Transition back to strengths input
            if await self.state_manager.transition_to(user_id, AWAITING_STRENGTHS):
                await update.message.reply_text("Okay, please enter your strengths again.")
                return AWAITING_STRENGTHS
        
        logger.error(f"Failed to transition state for user {user_id}")
        return current_state

    async def handle_improvements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle areas for improvement input."""
        user_id = update.effective_user.id
        user_input = update.message.text
        
        # Ensure we're in the correct state
        current_state = self.state_manager.get_current_state(user_id)
        if current_state != AWAITING_IMPROVEMENTS:
            logger.warning(f"Unexpected state for handle_improvements: {current_state}")
            await update.message.reply_text(
                "Sorry, there was a confusion in the conversation flow. "
                "Let's start over with your areas for improvement."
            )
            await self.state_manager.transition_to(user_id, AWAITING_IMPROVEMENTS)
            return AWAITING_IMPROVEMENTS
        
        # Store improvements temporarily
        if "temp_improvements" not in context.user_data:
            context.user_data["temp_improvements"] = []
            
        # Split input by commas and newlines
        improvements = re.split(r'[,\n]', user_input)
        improvements = [imp.strip() for imp in improvements if imp.strip()]
        
        if not improvements:
            await update.message.reply_text(
                "I couldn't detect any areas for improvement. Please try again.\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points"
            )
            return AWAITING_IMPROVEMENTS
        
        context.user_data["temp_improvements"] = improvements
        
        # Transition to confirmation state
        if await self.state_manager.transition_to(user_id, AWAITING_IMPROVEMENTS_CONFIRMATION):
            # Show confirmation message
            confirmation_text = (
                "I understood these areas for improvement:\n\n"
                + "\n".join(f"• {imp}" for imp in improvements)
                + "\n\nIs this correct? (yes/no)\n"
                + "If yes, let's move on to your achievements.\n"
                + "If no, please enter the areas again."
            )
            await update.message.reply_text(confirmation_text)
            return AWAITING_IMPROVEMENTS_CONFIRMATION
        else:
            logger.error(f"Failed to transition state for user {user_id}")
            return AWAITING_IMPROVEMENTS

    async def handle_improvements_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle confirmation of improvements."""
        user_id = update.effective_user.id
        response = update.message.text.lower()
        
        # Ensure we're in the correct state
        current_state = self.state_manager.get_current_state(user_id)
        if current_state != AWAITING_IMPROVEMENTS_CONFIRMATION:
            logger.warning(f"Unexpected state for handle_improvements_confirmation: {current_state}")
            return current_state
        
        if response == "yes":
            # Store confirmed improvements
            context.user_data["improvements"] = context.user_data.get("temp_improvements", [])
            
            # Clear temporary storage
            if "temp_improvements" in context.user_data:
                del context.user_data["temp_improvements"]
            
            # Transition to achievements state
            if await self.state_manager.transition_to(user_id, AWAITING_ACHIEVEMENTS):
                # Move to achievements
                await update.message.reply_text(
                    "Great! Now, what are your notable achievements?\n"
                    "You can:\n"
                    "• List them one per line\n"
                    "• Separate them with commas\n"
                    "• Use bullet points\n\n"
                    "Example:\n"
                    "Released debut EP in 2023\n"
                    "Performed at SXSW\n"
                    "100k+ streams on Spotify"
                )
                return AWAITING_ACHIEVEMENTS
                
        elif response == "no":
            # Transition back to improvements input
            if await self.state_manager.transition_to(user_id, AWAITING_IMPROVEMENTS):
                await update.message.reply_text(
                    "Okay, please enter your areas for improvement again.\n"
                    "You can:\n"
                    "• List them one per line\n"
                    "• Separate them with commas\n"
                    "• Use bullet points"
                )
                return AWAITING_IMPROVEMENTS
                
        else:
            await update.message.reply_text(
                "Please respond with 'yes' or 'no'."
            )
            return AWAITING_IMPROVEMENTS_CONFIRMATION
            
        logger.error(f"Failed to transition state for user {user_id}")
        return current_state

    async def handle_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the achievements input."""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Ensure we're in the correct state
        current_state = self.state_manager.get_current_state(user_id)
        if current_state != AWAITING_ACHIEVEMENTS:
            logger.warning(f"Unexpected state for handle_achievements: {current_state}")
            await update.message.reply_text(
                "Sorry, there was a confusion in the conversation flow. "
                "Let's start over with your achievements."
            )
            await self.state_manager.transition_to(user_id, AWAITING_ACHIEVEMENTS)
            return AWAITING_ACHIEVEMENTS
        
        # Split by common separators and clean up
        achievements = [
            achievement.strip()
            for achievement in re.split(r'[,;\n•\-]', text)
            if achievement.strip()
        ]
        
        if not achievements:
            await update.message.reply_text(
                "I couldn't detect any achievements. Please share your notable achievements.\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Released debut EP in 2023\n"
                "Performed at SXSW\n"
                "100k+ streams on Spotify"
            )
            return AWAITING_ACHIEVEMENTS
            
        context.user_data['achievements'] = achievements
        
        # Show what was understood and transition to social media
        achievements_str = "\n".join(f"• {achievement}" for achievement in achievements)
        
        if await self.state_manager.transition_to(user_id, AWAITING_SOCIAL_MEDIA):
            await update.message.reply_text(
                f"I understood these achievements:\n\n{achievements_str}\n\n"
                "Great! Now, let's add your social media profiles.\n"
                "You can:\n"
                "• Paste full profile URLs\n"
                "• Use @handles (optionally followed by platform name)\n"
                "• Use format 'platform - handle'\n"
                "• Separate multiple profiles with commas or new lines\n\n"
                "Example inputs:\n"
                "https://instagram.com/artistname\n"
                "@artistname twitter\n"
                "instagram - @artistname\n"
                "facebook: fb.com/artistpage"
            )
            return AWAITING_SOCIAL_MEDIA
        else:
            logger.error(f"Failed to transition state for user {user_id}")
            return AWAITING_ACHIEVEMENTS

    async def handle_social_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the social media input."""
        social_media = {}
        text = update.message.text.strip()
        
        # Handle different input formats
        try:
            # Split by any common separator (comma, newline, or semicolon)
            entries = [e.strip() for e in re.split(r'[,;\n]', text) if e.strip()]
            
            for entry in entries:
                # Try different formats:
                # 1. platform:handle
                # 2. platform - handle
                # 3. Full URL
                # 4. @handle platform
                if ':' in entry:
                    platform, handle = entry.split(':', 1)
                elif ' - ' in entry:
                    platform, handle = entry.split(' - ', 1)
                elif entry.startswith(('http://', 'https://')):
                    url = entry.lower()
                    if 'instagram.com' in url:
                        platform = 'instagram'
                        handle = url.split('/')[-1].split('?')[0]
                    elif 'twitter.com' in url:
                        platform = 'twitter'
                        handle = url.split('/')[-1].split('?')[0]
                    elif 'facebook.com' in url:
                        platform = 'facebook'
                        handle = url.split('/')[-1].split('?')[0]
                    else:
                        platform = 'other'
                        handle = url
                elif entry.startswith('@'):
                    parts = entry.split()
                    handle = parts[0]
                    platform = parts[1] if len(parts) > 1 else 'instagram'  # Default to Instagram for @handles
                else:
                    # Try to guess platform from common keywords
                    lower_entry = entry.lower()
                    if any(x in lower_entry for x in ['insta', 'ig']):
                        platform = 'instagram'
                        handle = entry
                    elif any(x in lower_entry for x in ['tw', 'twitter']):
                        platform = 'twitter'
                        handle = entry
                    elif any(x in lower_entry for x in ['fb', 'facebook']):
                        platform = 'facebook'
                        handle = entry
                    else:
                        platform = 'other'
                        handle = entry
                
                social_media[platform.strip().lower()] = handle.strip()
                
        except Exception as e:
            logger.error(f"Error parsing social media: {str(e)}")
            await update.message.reply_text(
                "I couldn't understand some of your social media profiles. You can:\n"
                "• Paste full profile URLs\n"
                "• Use @handles (optionally followed by platform name)\n"
                "• Use format 'platform - handle'\n"
                "• Separate multiple profiles with commas or new lines\n\n"
                "Example inputs:\n"
                "https://instagram.com/artistname\n"
                "@artistname twitter\n"
                "instagram - @artistname\n"
                "facebook: fb.com/artistpage"
            )
            return AWAITING_SOCIAL_MEDIA
        
        if not social_media:
            await update.message.reply_text(
                "I couldn't detect any social media profiles. Please try again with at least one profile."
            )
            return AWAITING_SOCIAL_MEDIA
        
        context.user_data['social_media'] = social_media
        
        # Show what was understood and ask for confirmation
        platforms_str = "\n".join(f"• {platform}: {handle}" for platform, handle in social_media.items())
        await update.message.reply_text(
            f"I understood these social media profiles:\n\n{platforms_str}\n\n"
            "Is this correct? (yes/no)\n"
            "If yes, let's move on to your streaming profiles.\n"
            "If no, please enter your profiles again."
        )
        
        if update.message.text.lower() == 'no':
            return AWAITING_SOCIAL_MEDIA
            
        await update.message.reply_text(
            "Great! Now, please share your streaming profiles.\n"
            "You can:\n"
            "• Paste the URLs directly\n"
            "• Enter them one per line\n"
            "• Separate them with commas\n\n"
            "Example:\n"
            "https://open.spotify.com/artist/...\n"
            "https://music.apple.com/artist/..."
        )
        return AWAITING_STREAMING_PROFILES

    async def handle_streaming_profiles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the streaming profiles input."""
        streaming_profiles = {}
        text = update.message.text.strip()
        
        # Handle different input formats
        try:
            # Split by any common separator (comma, newline, or semicolon)
            entries = [e.strip() for e in re.split(r'[,;\n]', text) if e.strip()]
            
            for entry in entries:
                url = entry.lower()
                # Auto-detect platform from URL
                if 'spotify.com' in url:
                    platform = 'spotify'
                elif 'apple.com/music' in url or 'music.apple.com' in url:
                    platform = 'apple_music'
                elif 'soundcloud.com' in url:
                    platform = 'soundcloud'
                elif 'youtube.com' in url or 'youtu.be' in url:
                    platform = 'youtube'
                elif 'deezer.com' in url:
                    platform = 'deezer'
                elif 'tidal.com' in url:
                    platform = 'tidal'
                elif 'bandcamp.com' in url:
                    platform = 'bandcamp'
                else:
                    # Try to extract platform from format platform:url
                    if ':' in entry:
                        platform, url = entry.split(':', 1)
                    else:
                        platform = 'other'
                
                streaming_profiles[platform.strip().lower()] = url.strip()
                
        except Exception as e:
            logger.error(f"Error parsing streaming profiles: {str(e)}")
            await update.message.reply_text(
                "I couldn't understand some of your streaming profiles. You can:\n"
                "• Paste the full URLs directly\n"
                "• Enter them one per line\n"
                "• Use format 'platform: url'\n"
                "• Separate multiple profiles with commas\n\n"
                "Example:\n"
                "https://open.spotify.com/artist/...\n"
                "https://music.apple.com/artist/..."
            )
            return AWAITING_STREAMING_PROFILES
        
        if not streaming_profiles:
            await update.message.reply_text(
                "I couldn't detect any streaming profiles. Please try again with at least one profile."
            )
            return AWAITING_STREAMING_PROFILES
        
        context.user_data['streaming_profiles'] = streaming_profiles
        
        # Show what was understood and ask for confirmation
        platforms_str = "\n".join(f"• {platform}: {url}" for platform, url in streaming_profiles.items())
        await update.message.reply_text(
            f"I understood these streaming profiles:\n\n{platforms_str}\n\n"
            "Is this correct? (yes/no)\n"
            "If yes, I'll show you your complete profile summary.\n"
            "If no, please enter your profiles again."
        )
        
        if update.message.text.lower() == 'no':
            return AWAITING_STREAMING_PROFILES
        
        # Show profile summary
        profile_text = self._generate_profile_summary(context.user_data)
        await update.message.reply_text(
            f"Here's your complete profile summary:\n\n{profile_text}\n\n"
            "Is everything correct? (yes/no)"
        )
        return CONFIRM_PROFILE

    def _generate_profile_summary(self, data: Dict[str, Any]) -> str:
        """Generate a summary of the profile data."""
        summary = [
            f"🎤 Artist Name: {data.get('name', 'Not set')}",
            f"🎵 Genre: {data.get('genre', 'Not set')}",
            f"📈 Career Stage: {data.get('career_stage', 'Not set')}",
            f"🎯 Goals: {', '.join(data.get('goals', []))}",
            f"💪 Strengths: {', '.join(data.get('strengths', []))}",
            f"📚 Areas for Improvement: {', '.join(data.get('areas_for_improvement', []))}",
            f"🏆 Achievements: {', '.join(data.get('achievements', []))}",
            f"📱 Social Media: {', '.join(f'{k}: {v}' for k, v in data.get('social_media', {}).items())}",
            f"🎧 Streaming Profiles: {', '.join(f'{k}: {v}' for k, v in data.get('streaming_profiles', {}).items())}"
        ]
        return "\n".join(summary)

    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle final profile confirmation."""
        if update.message.text.lower() == 'yes':
            user_id = update.effective_user.id
            
            # Create the artist profile
            profile = ArtistProfile(
                id=str(user_id),  # Use user_id as profile id
                name=context.user_data.get('name', 'Artist'),
                genre=context.user_data.get('genre', ''),
                career_stage=context.user_data.get('career_stage', 'emerging'),
                goals=context.user_data.get('goals', []),
                strengths=context.user_data.get('strengths', []),
                areas_for_improvement=context.user_data.get('improvements', []),
                achievements=context.user_data.get('achievements', []),
                social_media=context.user_data.get('social_media', {}),
                streaming_profiles=context.user_data.get('streaming_profiles', {}),
                brand_guidelines={}
            )
            
            try:
                # Save profile data to persistence
                profile_dict = profile.dict()
                context.user_data['profile_data'] = profile_dict
                context.user_data['profile_confirmed'] = True
                
                # Update bot's profile storage
                self.agent.set_user_profile(user_id, profile)
                
                # Save to bot's persistence
                if not hasattr(self.agent.persistence.bot_data, 'profiles'):
                    self.agent.persistence.bot_data['profiles'] = {}
                self.agent.persistence.bot_data['profiles'][user_id] = profile_dict
                
                # Force persistence update
                await self.agent.persistence.update_bot_data(self.agent.persistence.bot_data)
                await self.agent.persistence._backup_data()
                
                logger.info(f"Profile confirmed and saved for user {user_id}")
                
                # Send welcome message with available commands
                await update.message.reply_text(
                    f"Great! Your profile has been saved. Welcome {profile.name}!\n\n"
                    "Here are the commands you can use:\n"
                    "/goals - View and manage your goals\n"
                    "/tasks - View and manage your tasks\n"
                    "/events - View and manage your events\n"
                    "/contracts - View and manage your contracts\n"
                    "/auto - Toggle autonomous mode\n"
                    "/help - Show all available commands"
                )
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"Error saving profile for user {user_id}: {str(e)}")
                await update.message.reply_text(
                    "There was an error saving your profile. Please try again or contact support."
                )
                return ConversationHandler.END
                
        else:
            keyboard = [
                ["Name", "Genre", "Career Stage"],
                ["Goals", "Strengths", "Areas for Improvement"],
                ["Achievements", "Social Media", "Streaming Profiles"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "What would you like to edit?",
                reply_markup=reply_markup
            )
            return EDIT_CHOICE

    async def handle_edit_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the edit choice."""
        try:
            choice = int(update.message.text)
            if not 1 <= choice <= 9:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please enter a number between 1 and 9.")
            return EDIT_CHOICE
        
        prompts = {
            1: ("What's your artist name?", AWAITING_NAME),
            2: ("What genre best describes your music?", AWAITING_GENRE),
            3: ("What's your current career stage?\nChoose from: emerging, established, or veteran", AWAITING_CAREER_STAGE),
            4: (
                "What are your main goals as an artist?\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Release an EP by end of year\n"
                "Reach 10k monthly listeners\n"
                "Book 5 live shows",
                AWAITING_GOALS
            ),
            5: (
                "What are your strengths as an artist?\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Strong vocal range\n"
                "Experienced with live performances\n"
                "Good at social media engagement",
                AWAITING_STRENGTHS
            ),
            6: (
                "What areas would you like to improve?\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Music theory knowledge\n"
                "Studio recording techniques\n"
                "Marketing strategy",
                AWAITING_IMPROVEMENTS
            ),
            7: (
                "What are your notable achievements?\n"
                "You can:\n"
                "• List them one per line\n"
                "• Separate them with commas\n"
                "• Use bullet points\n\n"
                "Example:\n"
                "Released debut EP in 2023\n"
                "Performed at SXSW\n"
                "100k+ streams on Spotify",
                AWAITING_ACHIEVEMENTS
            ),
            8: (
                "Let's add your social media profiles.\n"
                "You can:\n"
                "• Paste full profile URLs\n"
                "• Use @handles (optionally followed by platform name)\n"
                "• Use format 'platform - handle'\n"
                "• Separate multiple profiles with commas or new lines\n\n"
                "Example inputs:\n"
                "https://instagram.com/artistname\n"
                "@artistname twitter\n"
                "instagram - @artistname\n"
                "facebook: fb.com/artistpage",
                AWAITING_SOCIAL_MEDIA
            ),
            9: (
                "Please share your streaming profiles.\n"
                "You can:\n"
                "• Paste the URLs directly\n"
                "• Enter them one per line\n"
                "• Separate them with commas\n\n"
                "Example:\n"
                "https://open.spotify.com/artist/...\n"
                "https://music.apple.com/artist/...",
                AWAITING_STREAMING_PROFILES
            )
        }
        
        prompt, next_state = prompts[choice]
        await update.message.reply_text(prompt)
        return next_state

    async def handle_edit_section(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle editing a specific section of the profile."""
        choice = update.message.text.lower()
        
        # Map choices to states
        choice_map = {
            "name": AWAITING_NAME,
            "genre": AWAITING_GENRE,
            "career stage": AWAITING_CAREER_STAGE,
            "goals": AWAITING_GOALS,
            "strengths": AWAITING_STRENGTHS,
            "areas for improvement": AWAITING_IMPROVEMENTS,
            "achievements": AWAITING_ACHIEVEMENTS,
            "social media": AWAITING_SOCIAL_MEDIA,
            "streaming profiles": AWAITING_STREAMING_PROFILES
        }
        
        if choice in choice_map:
            await update.message.reply_text(f"Please enter your new {choice}:")
            return choice_map[choice]
        else:
            await update.message.reply_text(
                "Please select a valid section to edit:\n"
                "• Name\n"
                "• Genre\n"
                "• Career Stage\n"
                "• Goals\n"
                "• Strengths\n"
                "• Areas for Improvement\n"
                "• Achievements\n"
                "• Social Media\n"
                "• Streaming Profiles"
            )
            return EDIT_CHOICE

    async def cancel_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the onboarding process."""
        await update.message.reply_text(
            "Onboarding cancelled. You can start again with /start or /onboard when you're ready."
        )
        return ConversationHandler.END

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for the onboarding process."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_onboarding),
                CommandHandler("onboard", self.start_onboarding)
            ],
            states={
                AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_name)],
                AWAITING_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_genre)],
                AWAITING_CAREER_STAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_career_stage)],
                AWAITING_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_goals)],
                AWAITING_GOALS_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_goals_confirmation)],
                AWAITING_STRENGTHS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_strengths)],
                AWAITING_STRENGTHS_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_strengths_confirmation)],
                AWAITING_IMPROVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_improvements)],
                AWAITING_IMPROVEMENTS_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_improvements_confirmation)],
                AWAITING_ACHIEVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_achievements)],
                AWAITING_SOCIAL_MEDIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_social_media)],
                AWAITING_STREAMING_PROFILES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_streaming_profiles)],
                CONFIRM_PROFILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_confirmation)],
                EDIT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_choice)],
                EDIT_SECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_section)]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_onboarding),
                CommandHandler("restart", self.start_onboarding)
            ],
            name="onboarding",
            persistent=True,
            allow_reentry=True
        ) 