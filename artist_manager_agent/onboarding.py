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

# Add manager name state
(
    AWAITING_NAME,
    AWAITING_MANAGER_NAME,  # New state
    AWAITING_GENRE,
    AWAITING_SUBGENRE,
    AWAITING_STYLE_DESCRIPTION,
    AWAITING_INFLUENCES,
    AWAITING_CAREER_STAGE,
    AWAITING_GOALS,
    AWAITING_GOAL_TIMELINE,
    AWAITING_STRENGTHS,
    AWAITING_IMPROVEMENTS,
    AWAITING_ACHIEVEMENTS,
    AWAITING_SOCIAL_MEDIA,
    AWAITING_STREAMING_PROFILES,
    CONFIRM_PROFILE,
    EDIT_CHOICE,
    EDIT_SECTION,
) = range(17)  # Updated to 17 states

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

class OnboardingWizard:
    def __init__(self, agent: Any):
        self.agent = agent
        self.temp_data: Dict[str, Any] = {}
        self._load_name_data()

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
        await update.message.reply_text(
            "Let's get started with setting up your artist profile! "
            "First, what's your artist name?"
        )
        return AWAITING_NAME

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the artist name input."""
        name = update.message.text
        context.user_data['name'] = name
        await update.message.reply_text(
            f"Great to meet you, {name}! What genre best describes your music?"
        )
        return AWAITING_GENRE

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
            
        context.user_data['goals'] = goals
        
        # Show what was understood
        goals_str = "\n".join(f"• {goal}" for goal in goals)
        await update.message.reply_text(
            f"I understood these goals:\n\n{goals_str}\n\n"
            "Is this correct? (yes/no)\n"
            "If yes, let's move on to your strengths.\n"
            "If no, please enter your goals again."
        )
        
        if update.message.text.lower() == 'no':
            return AWAITING_GOALS
            
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
                "• Use bullet points\n\n"
                "Example:\n"
                "Strong vocal range\n"
                "Experienced with live performances\n"
                "Good at social media engagement"
            )
            return AWAITING_STRENGTHS
            
        context.user_data['strengths'] = strengths
        
        # Show what was understood
        strengths_str = "\n".join(f"• {strength}" for strength in strengths)
        await update.message.reply_text(
            f"I understood these strengths:\n\n{strengths_str}\n\n"
            "Is this correct? (yes/no)\n"
            "If yes, let's move on to areas you'd like to improve.\n"
            "If no, please enter your strengths again."
        )
        
        if update.message.text.lower() == 'no':
            return AWAITING_STRENGTHS
            
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
                "• Use bullet points\n\n"
                "Example:\n"
                "Music theory knowledge\n"
                "Studio recording techniques\n"
                "Marketing strategy"
            )
            return AWAITING_IMPROVEMENTS
            
        context.user_data['areas_for_improvement'] = improvements
        
        # Show what was understood
        improvements_str = "\n".join(f"• {improvement}" for improvement in improvements)
        await update.message.reply_text(
            f"I understood these areas for improvement:\n\n{improvements_str}\n\n"
            "Is this correct? (yes/no)\n"
            "If yes, let's move on to your achievements.\n"
            "If no, please enter the areas again."
        )
        
        if update.message.text.lower() == 'no':
            return AWAITING_IMPROVEMENTS
            
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

    async def handle_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the achievements input."""
        text = update.message.text.strip()
        
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
        
        # Show what was understood
        achievements_str = "\n".join(f"• {achievement}" for achievement in achievements)
        await update.message.reply_text(
            f"I understood these achievements:\n\n{achievements_str}\n\n"
            "Is this correct? (yes/no)\n"
            "If yes, let's move on to your social media profiles.\n"
            "If no, please enter your achievements again."
        )
        
        if update.message.text.lower() == 'no':
            return AWAITING_ACHIEVEMENTS
            
        await update.message.reply_text(
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
        """Handle the profile confirmation."""
        if update.message.text.lower() == 'yes':
            # Create the artist profile
            profile = self.agent.artist_profile
            profile.name = context.user_data['name']
            profile.genre = context.user_data['genre']
            profile.career_stage = context.user_data['career_stage']
            profile.goals = context.user_data['goals']
            profile.strengths = context.user_data['strengths']
            profile.areas_for_improvement = context.user_data['areas_for_improvement']
            profile.achievements = context.user_data['achievements']
            profile.social_media = context.user_data['social_media']
            profile.streaming_profiles = context.user_data['streaming_profiles']
            profile.updated_at = datetime.now()
            
            # Mark profile as confirmed
            context.user_data['profile_confirmed'] = True
            
            await update.message.reply_text(
                "Perfect! Your profile has been saved. You can now use /help to see available commands."
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "What would you like to edit?\n"
                "1. Artist Name\n"
                "2. Genre\n"
                "3. Career Stage\n"
                "4. Goals\n"
                "5. Strengths\n"
                "6. Areas for Improvement\n"
                "7. Achievements\n"
                "8. Social Media\n"
                "9. Streaming Profiles\n"
                "Please enter the number of the section you want to edit."
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

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for the onboarding process."""
        return ConversationHandler(
            entry_points=[CommandHandler("start", self.start_onboarding)],
            states={
                AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_name)],
                AWAITING_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_genre)],
                AWAITING_CAREER_STAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_career_stage)],
                AWAITING_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_goals)],
                AWAITING_STRENGTHS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_strengths)],
                AWAITING_IMPROVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_improvements)],
                AWAITING_ACHIEVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_achievements)],
                AWAITING_SOCIAL_MEDIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_social_media)],
                AWAITING_STREAMING_PROFILES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_streaming_profiles)],
                CONFIRM_PROFILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_confirmation)],
                EDIT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_choice)],
            },
            fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
            name="onboarding",
            persistent=True
        ) 