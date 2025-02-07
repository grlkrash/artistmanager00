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

# ... rest of the existing OnboardingWizard class ... 