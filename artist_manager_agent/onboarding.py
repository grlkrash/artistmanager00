from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from pydantic import BaseModel
import random

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
) = range(15)

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
        welcome_text = """
🎵 Welcome to your Artist Manager Setup!

Let's start by getting to know each other.
What's your artist name?
        """
        await update.message.reply_text(welcome_text)
        return AWAITING_NAME

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle artist name input."""
        self.temp_data["name"] = update.message.text

        # Offer manager naming options
        keyboard = [
            [
                InlineKeyboardButton("Generate Random Name", callback_data="generate_manager_name"),
                InlineKeyboardButton("Choose My Own", callback_data="choose_manager_name")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Great! Now, let's personalize your experience.\n"
            "Would you like to choose a name for your manager, or should I generate one?",
            reply_markup=reply_markup
        )
        return AWAITING_MANAGER_NAME

    async def handle_manager_name_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle manager name selection."""
        query = update.callback_query
        await query.answer()

        if query.data == "generate_manager_name":
            manager_name = self._generate_manager_name()
            self.temp_data["manager_name"] = manager_name
            await query.edit_message_text(
                f"I'll be {manager_name}, your dedicated artist manager! 😊\n\n"
                "Now, what's your primary genre?"
            )
            return AWAITING_GENRE
        else:
            await query.edit_message_text(
                "What would you like to call me? Choose a name that feels right!"
            )
            return AWAITING_MANAGER_NAME

    async def handle_custom_manager_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle custom manager name input."""
        self.temp_data["manager_name"] = update.message.text

        genre_keyboard = [
            ["Pop", "Hip-Hop", "R&B"],
            ["Rock", "Electronic", "Jazz"],
            ["Classical", "Folk", "Other"]
        ]
        reply_markup = ReplyKeyboardMarkup(genre_keyboard, one_time_keyboard=True)
        
        await update.message.reply_text(
            f"Nice to meet you! I'm {self.temp_data['manager_name']}, "
            "and I'm excited to help manage your career!\n\n"
            "What's your primary genre?",
            reply_markup=reply_markup
        )
        return AWAITING_GENRE

    async def handle_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle genre input."""
        self.temp_data["genre"] = update.message.text
        
        await update.message.reply_text(
            "Great choice! Now, let's get more specific.\n"
            "What subgenre(s) do you specialize in? (e.g., for Rock: Alternative, Metal, Indie)"
        )
        return AWAITING_SUBGENRE

    async def handle_subgenre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle subgenre input."""
        self.temp_data["subgenre"] = update.message.text
        
        await update.message.reply_text(
            "Perfect! Now, describe your musical style in a few sentences.\n"
            "What makes your sound unique?"
        )
        return AWAITING_STYLE_DESCRIPTION

    async def handle_style(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle style description input."""
        self.temp_data["style_description"] = update.message.text
        
        await update.message.reply_text(
            "Who are your main musical influences?\n"
            "List a few artists that have shaped your sound."
        )
        return AWAITING_INFLUENCES

    async def handle_influences(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle influences input."""
        self.temp_data["influences"] = [x.strip() for x in update.message.text.split(",")]
        
        career_stages = [
            ["Emerging", "Developing"],
            ["Established", "Professional"],
            ["Veteran", "Legacy"]
        ]
        reply_markup = ReplyKeyboardMarkup(career_stages, one_time_keyboard=True)
        
        await update.message.reply_text(
            "How would you describe your current career stage?",
            reply_markup=reply_markup
        )
        return AWAITING_CAREER_STAGE

    async def handle_career_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle career stage input."""
        self.temp_data["career_stage"] = update.message.text
        
        await update.message.reply_text(
            "What are your main career goals for the next 1-2 years?\n"
            "List them one per line, starting with the most important."
        )
        return AWAITING_GOALS

    async def handle_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle goals input."""
        self.temp_data["goals"] = [x.strip() for x in update.message.text.split("\n")]
        
        await update.message.reply_text(
            "When would you like to achieve these goals?\n"
            "Give me a rough timeline for each goal."
        )
        return AWAITING_GOAL_TIMELINE

    async def handle_goal_timeline(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle goal timeline input."""
        self.temp_data["goal_timeline"] = update.message.text
        
        await update.message.reply_text(
            "What would you say are your greatest strengths as an artist?\n"
            "List them one per line."
        )
        return AWAITING_STRENGTHS

    async def handle_strengths(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle strengths input."""
        self.temp_data["strengths"] = [x.strip() for x in update.message.text.split("\n")]
        
        await update.message.reply_text(
            "What areas would you like to improve in?\n"
            "List them one per line."
        )
        return AWAITING_IMPROVEMENTS

    async def handle_improvements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle improvements input."""
        self.temp_data["areas_for_improvement"] = [x.strip() for x in update.message.text.split("\n")]
        
        await update.message.reply_text(
            "What are your notable achievements so far?\n"
            "List them one per line."
        )
        return AWAITING_ACHIEVEMENTS

    async def handle_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle achievements input."""
        self.temp_data["achievements"] = [x.strip() for x in update.message.text.split("\n")]
        
        await update.message.reply_text(
            "Please share your social media handles.\n"
            "Format: platform: username\n"
            "Example:\n"
            "instagram: @myhandle\n"
            "twitter: @myhandle"
        )
        return AWAITING_SOCIAL_MEDIA

    async def handle_social_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle social media input."""
        lines = update.message.text.strip().split("\n")
        social_media = {}
        for line in lines:
            if ":" in line:
                platform, handle = line.split(":", 1)
                social_media[platform.strip().lower()] = handle.strip()
        self.temp_data["social_media"] = social_media
        
        await update.message.reply_text(
            "Great! Now, please share your streaming profile links.\n"
            "Format: platform: link\n"
            "Example:\n"
            "spotify: spotify:artist:123\n"
            "apple_music: artist/456"
        )
        return AWAITING_STREAMING_PROFILES

    async def handle_streaming(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle streaming profiles input."""
        lines = update.message.text.strip().split("\n")
        streaming_profiles = {}
        for line in lines:
            if ":" in line:
                platform, link = line.split(":", 1)
                streaming_profiles[platform.strip().lower()] = link.strip()
        self.temp_data["streaming_profiles"] = streaming_profiles
        
        # Prepare profile summary
        summary = self._generate_profile_summary()
        
        await update.message.reply_text(
            "Here's a summary of your profile:\n\n"
            f"{summary}\n\n"
            "Is this correct? Type 'yes' to confirm or 'no' to start over."
        )
        return CONFIRM_PROFILE

    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle profile confirmation."""
        if update.message.text.lower() == "yes":
            # Update artist profile
            self.agent.artist_profile.name = self.temp_data["name"]
            self.agent.artist_profile.genre = self.temp_data["genre"]
            self.agent.artist_profile.career_stage = self.temp_data["career_stage"]
            self.agent.artist_profile.goals = self.temp_data["goals"]
            self.agent.artist_profile.strengths = self.temp_data["strengths"]
            self.agent.artist_profile.areas_for_improvement = self.temp_data["areas_for_improvement"]
            self.agent.artist_profile.achievements = self.temp_data["achievements"]
            self.agent.artist_profile.social_media = self.temp_data["social_media"]
            self.agent.artist_profile.streaming_profiles = self.temp_data["streaming_profiles"]
            
            await update.message.reply_text(
                "Perfect! Your profile has been set up. I'm ready to help manage your career!\n"
                "Use /help to see available commands."
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "Let's start over. What's your artist name?"
            )
            self.temp_data = {}
            return AWAITING_NAME

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation."""
        await update.message.reply_text(
            "Setup cancelled. You can start over anytime with /start."
        )
        return ConversationHandler.END

    def _generate_profile_summary(self) -> str:
        """Generate a summary of the profile data."""
        summary = [
            f"🎤 Artist Name: {self.temp_data['name']}",
            f"👔 Manager Name: {self.temp_data['manager_name']}",
            f"🎵 Genre: {self.temp_data['genre']}",
            f"📝 Subgenre: {self.temp_data['subgenre']}",
            f"🎨 Style: {self.temp_data['style_description']}",
            f"🌟 Influences: {', '.join(self.temp_data['influences'])}",
            f"📈 Career Stage: {self.temp_data['career_stage']}",
            f"🎯 Goals:\n" + "\n".join(f"  • {goal}" for goal in self.temp_data['goals']),
            f"💪 Strengths:\n" + "\n".join(f"  • {strength}" for strength in self.temp_data['strengths']),
            f"📚 Areas for Improvement:\n" + "\n".join(f"  • {area}" for area in self.temp_data['areas_for_improvement']),
            f"🏆 Achievements:\n" + "\n".join(f"  • {achievement}" for achievement in self.temp_data['achievements']),
            f"📱 Social Media:\n" + "\n".join(f"  • {platform}: {handle}" for platform, handle in self.temp_data['social_media'].items()),
            f"🎧 Streaming Profiles:\n" + "\n".join(f"  • {platform}: {link}" for platform, link in self.temp_data['streaming_profiles'].items())
        ]
        return "\n\n".join(summary) 