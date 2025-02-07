from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from pydantic import BaseModel

# Onboarding states
(
    AWAITING_NAME,
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
) = range(14)

class ArtistContext(BaseModel):
    """Extended artist context for better guidance."""
    influences: List[str] = []
    style_description: str = ""
    target_audience: List[str] = []
    similar_artists: List[str] = []
    preferred_collaboration_types: List[str] = []
    creative_process: str = ""
    production_preferences: Dict[str, Any] = {}

class OnboardingWizard:
    def __init__(self, agent: Any):
        self.agent = agent
        self.temp_data: Dict[str, Any] = {}

    async def start_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the onboarding process."""
        welcome_text = """
🎵 Welcome to your AI Artist Manager Setup!

I'll help you create your artist profile and understand your goals better.
This will help me provide more personalized guidance and strategy.

Let's start with the basics.

What's your artist name?
        """
        await update.message.reply_text(welcome_text)
        return AWAITING_NAME

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle artist name input."""
        self.temp_data["name"] = update.message.text

        genre_keyboard = [
            ["Pop", "Hip-Hop", "R&B"],
            ["Rock", "Electronic", "Jazz"],
            ["Classical", "Folk", "Other"]
        ]
        reply_markup = ReplyKeyboardMarkup(genre_keyboard, one_time_keyboard=True)
        
        await update.message.reply_text(
            "Great! What's your primary genre?",
            reply_markup=reply_markup
        )
        return AWAITING_GENRE

    async def handle_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle genre input."""
        self.temp_data["genre"] = update.message.text

        await update.message.reply_text(
            "Tell me more about your style. How would you describe your sound?\n"
            "Include elements like:\n"
            "- Subgenres you blend\n"
            "- Mood/vibe of your music\n"
            "- Unique elements of your sound"
        )
        return AWAITING_STYLE_DESCRIPTION

    async def handle_style_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle style description input."""
        self.temp_data["style_description"] = update.message.text

        await update.message.reply_text(
            "Who are your main musical influences? List 3-5 artists that inspire your sound.\n"
            "This helps me understand your direction and find relevant opportunities."
        )
        return AWAITING_INFLUENCES

    async def handle_influences(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle influences input."""
        self.temp_data["influences"] = [
            name.strip() for name in update.message.text.split(",")
        ]

        stage_keyboard = [
            ["Just Starting", "Building Fanbase"],
            ["Emerging", "Established"],
            ["Professional", "Major Label"]
        ]
        reply_markup = ReplyKeyboardMarkup(stage_keyboard, one_time_keyboard=True)
        
        await update.message.reply_text(
            "What stage are you at in your career?",
            reply_markup=reply_markup
        )
        return AWAITING_CAREER_STAGE

    async def handle_career_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle career stage input."""
        self.temp_data["career_stage"] = update.message.text

        await update.message.reply_text(
            "What are your main goals for the next 6-12 months?\n"
            "List them one by one. Send 'done' when finished.\n\n"
            "Example goals:\n"
            "- Release an EP\n"
            "- Reach 10k monthly listeners\n"
            "- Book first tour"
        )
        self.temp_data["goals"] = []
        return AWAITING_GOALS

    async def handle_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle goals input."""
        if update.message.text.lower() == "done":
            await update.message.reply_text(
                "What are your greatest strengths as an artist?\n"
                "List them one by one. Send 'done' when finished."
            )
            return AWAITING_STRENGTHS

        self.temp_data.setdefault("goals", []).append(update.message.text)
        return AWAITING_GOALS

    async def handle_strengths(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle strengths input."""
        if update.message.text.lower() == "done":
            await update.message.reply_text(
                "What areas would you like to improve?\n"
                "List them one by one. Send 'done' when finished."
            )
            return AWAITING_IMPROVEMENTS

        self.temp_data.setdefault("strengths", []).append(update.message.text)
        return AWAITING_STRENGTHS

    async def handle_improvements(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle areas for improvement input."""
        if update.message.text.lower() == "done":
            await update.message.reply_text(
                "Share your social media handles (or type 'skip'):\n"
                "Format: platform: handle\n"
                "Example:\n"
                "instagram: @myhandle\n"
                "twitter: @myhandle"
            )
            return AWAITING_SOCIAL_MEDIA

        self.temp_data.setdefault("areas_for_improvement", []).append(update.message.text)
        return AWAITING_IMPROVEMENTS

    async def handle_social_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle social media input."""
        if update.message.text.lower() != "skip":
            social_media = {}
            for line in update.message.text.split("\n"):
                if ":" in line:
                    platform, handle = line.split(":", 1)
                    social_media[platform.strip().lower()] = handle.strip()
            self.temp_data["social_media"] = social_media

        # Create profile summary
        summary = self._create_profile_summary()
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="profile_confirm"),
                InlineKeyboardButton("🔄 Start Over", callback_data="profile_restart")
            ],
            [
                InlineKeyboardButton("✏️ Edit Goals", callback_data="profile_edit_goals"),
                InlineKeyboardButton("✏️ Edit Style", callback_data="profile_edit_style")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Here's your profile summary:\n\n" + summary,
            reply_markup=reply_markup
        )
        return CONFIRM_PROFILE

    def _create_profile_summary(self) -> str:
        """Create a formatted profile summary."""
        summary = f"""
🎨 Artist Profile

Name: {self.temp_data['name']}
Genre: {self.temp_data['genre']}
Stage: {self.temp_data['career_stage']}

🎵 Style:
{self.temp_data['style_description']}

✨ Influences:
{', '.join(self.temp_data['influences'])}

🎯 Goals:
{"".join(f"• {goal}\n" for goal in self.temp_data.get('goals', []))}

💪 Strengths:
{"".join(f"• {strength}\n" for strength in self.temp_data.get('strengths', []))}

📈 Areas for Growth:
{"".join(f"• {area}\n" for area in self.temp_data.get('areas_for_improvement', []))}

🌐 Social Media:
{"".join(f"• {platform}: {handle}\n" for platform, handle in self.temp_data.get('social_media', {}).items())}
        """
        return summary

    async def finalize_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Create the artist profile and context."""
        # Create artist profile
        profile = {
            "name": self.temp_data["name"],
            "genre": self.temp_data["genre"],
            "career_stage": self.temp_data["career_stage"],
            "goals": self.temp_data.get("goals", []),
            "strengths": self.temp_data.get("strengths", []),
            "areas_for_improvement": self.temp_data.get("areas_for_improvement", []),
            "achievements": [],
            "social_media": self.temp_data.get("social_media", {}),
            "streaming_profiles": {},
            "health_notes": []
        }

        # Create artist context
        context = {
            "influences": self.temp_data["influences"],
            "style_description": self.temp_data["style_description"],
            "target_audience": [],  # To be analyzed by the agent
            "similar_artists": [],  # To be analyzed by the agent
            "preferred_collaboration_types": [],
            "creative_process": "",
            "production_preferences": {}
        }

        # Update agent
        self.agent.artist = profile
        self.agent.artist_context = context

        await update.message.reply_text(
            "✨ Profile created! I'll now analyze your style and goals to create a personalized strategy.\n\n"
            "Use /help to see available commands and get started!"
        )
        return ConversationHandler.END 