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
            "Great! Now, please share your streaming profile links.\n\n"
            "Simply paste your profile links, one per line. For example:\n\n"
            "https://open.spotify.com/artist/...\n"
            "https://music.apple.com/artist/...\n"
            "https://soundcloud.com/...\n\n"
            "I'll automatically detect which platforms they're from."
        )
        return AWAITING_STREAMING_PROFILES

    async def handle_streaming(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle streaming profiles input."""
        lines = update.message.text.strip().split("\n")
        streaming_profiles = {}
        
        # Platform detection patterns
        platform_patterns = {
            "spotify": ["spotify.com", "spotify:"],
            "apple_music": ["apple.com/music", "music.apple.com"],
            "youtube_music": ["music.youtube.com"],
            "soundcloud": ["soundcloud.com"],
            "tidal": ["tidal.com"],
            "deezer": ["deezer.com"],
            "bandcamp": ["bandcamp.com"],
            "amazon_music": ["music.amazon.com"]
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Auto-detect platform from URL
            detected_platform = None
            for platform, patterns in platform_patterns.items():
                if any(pattern in line.lower() for pattern in patterns):
                    detected_platform = platform
                    break
            
            if detected_platform:
                streaming_profiles[detected_platform] = line
            else:
                # If no platform detected, try to parse old format for backward compatibility
                if ":" in line:
                    platform, link = line.split(":", 1)
                    streaming_profiles[platform.strip().lower()] = link.strip()
        
        self.temp_data["streaming_profiles"] = streaming_profiles
        
        # Prepare profile summary
        summary = self._generate_profile_summary()
        
        # Show confirmation with edit option
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data="confirm_profile"),
             InlineKeyboardButton("✏️ Edit", callback_data="edit_profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Here's a summary of your profile:\n\n"
            f"{summary}\n\n"
            "Please confirm your profile or choose to edit specific sections.",
            reply_markup=reply_markup
        )
        return CONFIRM_PROFILE

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "confirm_profile":
            try:
                # Validate required fields
                required_fields = ["name", "genre", "career_stage", "goals", "strengths", 
                                "areas_for_improvement", "achievements", "social_media", 
                                "streaming_profiles"]
                
                missing_fields = [field for field in required_fields 
                                if field not in self.temp_data or not self.temp_data[field]]
                
                if missing_fields:
                    missing_list = "\n".join(f"• {field.replace('_', ' ').title()}" 
                                           for field in missing_fields)
                    keyboard = [[InlineKeyboardButton("✏️ Edit Profile", 
                                                    callback_data="edit_profile")]]
                    await query.edit_message_text(
                        f"❌ The following required fields are missing:\n\n{missing_list}\n\n"
                        "Please click Edit Profile to complete these sections.",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return CONFIRM_PROFILE
                
                # Update artist profile
                for field in required_fields:
                    setattr(self.agent.artist_profile, field, self.temp_data[field])
                
                # Set profile confirmation in user data
                context.user_data['profile_confirmed'] = True
                context.user_data['artist_profile'] = self.agent.artist_profile
                
                # Save the data immediately
                if context.application.persistence:
                    await context.application.persistence.update_user_data(
                        user_id=update.effective_user.id,
                        data=context.user_data
                    )
                
                await query.edit_message_text(
                    "✅ Perfect! Your profile has been set up. I'm ready to help manage your career!\n"
                    "Use /help to see available commands."
                )
                return ConversationHandler.END
                
            except Exception as e:
                keyboard = [
                    [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")],
                    [InlineKeyboardButton("🔄 Start Over", callback_data="start_over")]
                ]
                await query.edit_message_text(
                    f"❌ Error saving profile: {str(e)}\n\n"
                    "Please choose an option below:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return CONFIRM_PROFILE
                
        elif query.data == "edit_profile":
            sections = [
                "Artist Name", "Manager Name", "Genre", "Subgenre", 
                "Style Description", "Influences", "Career Stage",
                "Goals", "Goal Timeline", "Strengths", "Areas for Improvement",
                "Achievements", "Social Media", "Streaming Profiles"
            ]
            
            # Create inline keyboard with sections
            keyboard = []
            for i, section in enumerate(sections, 1):
                keyboard.append([InlineKeyboardButton(
                    f"{i}. {section}", 
                    callback_data=f"edit_section_{i}"
                )])
            
            await query.edit_message_text(
                "Which section would you like to edit?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return EDIT_SECTION
            
        elif query.data.startswith("edit_section_"):
            section_num = int(query.data.split("_")[-1])
            section_map = {
                1: (AWAITING_NAME, "What's your artist name?"),
                2: (AWAITING_MANAGER_NAME, "What would you like to call your manager?"),
                3: (AWAITING_GENRE, "What's your primary genre?"),
                4: (AWAITING_SUBGENRE, "What subgenre(s) do you specialize in?"),
                5: (AWAITING_STYLE_DESCRIPTION, "Describe your musical style in a few sentences."),
                6: (AWAITING_INFLUENCES, "Who are your main musical influences?"),
                7: (AWAITING_CAREER_STAGE, "How would you describe your current career stage?"),
                8: (AWAITING_GOALS, "What are your main career goals?"),
                9: (AWAITING_GOAL_TIMELINE, "When would you like to achieve these goals?"),
                10: (AWAITING_STRENGTHS, "What are your greatest strengths as an artist?"),
                11: (AWAITING_IMPROVEMENTS, "What areas would you like to improve in?"),
                12: (AWAITING_ACHIEVEMENTS, "What are your notable achievements so far?"),
                13: (AWAITING_SOCIAL_MEDIA, "Please share your social media handles."),
                14: (AWAITING_STREAMING_PROFILES, "Please share your streaming profile links - one link per line.")
            }
            
            next_state, prompt = section_map[section_num]
            await query.edit_message_text(prompt)
            return next_state
            
        elif query.data == "start_over":
            self.temp_data = {}
            await query.edit_message_text("Let's start over. What's your artist name?")
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
            f" Achievements:\n" + "\n".join(f"  • {achievement}" for achievement in self.temp_data['achievements']),
            f"📱 Social Media:\n" + "\n".join(f"  • {platform}: {handle}" for platform, handle in self.temp_data['social_media'].items()),
            f"🎧 Streaming Profiles:\n" + "\n".join(f"  • {platform}: {link}" for platform, link in self.temp_data['streaming_profiles'].items())
        ]
        return "\n\n".join(summary)

    async def handle_edit_section(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle editing a specific section of the artist profile."""
        user_input = update.message.text
        section_to_edit = context.user_data.get("section_to_edit")
        
        if not section_to_edit:
            await update.message.reply_text(
                "I'm not sure which section you want to edit. Please use the buttons below to select a section.",
                reply_markup=self.get_edit_sections_keyboard()
            )
            return CONFIRM_PROFILE

        # Update the appropriate section based on user input
        artist_context = context.user_data.get("artist_context", ArtistContext())
        
        if section_to_edit == "name":
            artist_context.name = user_input
        elif section_to_edit == "genre":
            artist_context.genre = user_input
        elif section_to_edit == "subgenre":
            artist_context.subgenre = user_input
        elif section_to_edit == "style":
            artist_context.style_description = user_input
        elif section_to_edit == "influences":
            artist_context.influences = user_input
        elif section_to_edit == "career_stage":
            artist_context.career_stage = user_input
        elif section_to_edit == "goals":
            artist_context.goals = user_input
        elif section_to_edit == "goal_timeline":
            artist_context.goal_timeline = user_input
        elif section_to_edit == "strengths":
            artist_context.strengths = user_input
        elif section_to_edit == "improvements":
            artist_context.improvements = user_input
        elif section_to_edit == "achievements":
            artist_context.achievements = user_input
        elif section_to_edit == "social_media":
            artist_context.social_media = user_input
        elif section_to_edit == "streaming":
            # Use the existing streaming handler logic
            return await self.handle_streaming(update, context)
            
        context.user_data["artist_context"] = artist_context
        
        # Show updated profile summary
        await update.message.reply_text(
            f"Great! I've updated the {section_to_edit} section.\n\n"
            "Here's your updated profile summary:\n\n"
            f"{self.format_artist_summary(artist_context)}\n\n"
            "Is everything correct now?",
            reply_markup=self.get_confirmation_keyboard()
        )
        
        return CONFIRM_PROFILE

    def get_edit_sections_keyboard(self) -> InlineKeyboardMarkup:
        """Create keyboard with buttons for each editable section."""
        keyboard = [
            [
                InlineKeyboardButton("Artist Name", callback_data="edit_name"),
                InlineKeyboardButton("Genre", callback_data="edit_genre"),
            ],
            [
                InlineKeyboardButton("Subgenre", callback_data="edit_subgenre"),
                InlineKeyboardButton("Style", callback_data="edit_style"),
            ],
            [
                InlineKeyboardButton("Influences", callback_data="edit_influences"),
                InlineKeyboardButton("Career Stage", callback_data="edit_career_stage"),
            ],
            [
                InlineKeyboardButton("Goals", callback_data="edit_goals"),
                InlineKeyboardButton("Goal Timeline", callback_data="edit_goal_timeline"),
            ],
            [
                InlineKeyboardButton("Strengths", callback_data="edit_strengths"),
                InlineKeyboardButton("Areas for Improvement", callback_data="edit_improvements"),
            ],
            [
                InlineKeyboardButton("Achievements", callback_data="edit_achievements"),
                InlineKeyboardButton("Social Media", callback_data="edit_social_media"),
            ],
            [
                InlineKeyboardButton("Streaming Profiles", callback_data="edit_streaming"),
            ],
            [
                InlineKeyboardButton("✅ Confirm Profile", callback_data="confirm"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def format_artist_summary(self, artist_context: ArtistContext) -> str:
        """Format the artist summary for display."""
        summary = [
            f"🎤 Artist Name: {artist_context.name}",
            f"👔 Manager Name: {artist_context.manager_name}",
            f"🎵 Genre: {artist_context.genre}",
            f"📝 Subgenre: {artist_context.subgenre}",
            f"🎨 Style: {artist_context.style_description}",
            f"🌟 Influences: {', '.join(artist_context.influences)}",
            f"📈 Career Stage: {artist_context.career_stage}",
            f"🎯 Goals:\n" + "\n".join(f"  • {goal}" for goal in artist_context.goals),
            f"💪 Strengths:\n" + "\n".join(f"  • {strength}" for strength in artist_context.strengths),
            f"📚 Areas for Improvement:\n" + "\n".join(f"  • {area}" for area in artist_context.areas_for_improvement),
            f" Achievements:\n" + "\n".join(f"  • {achievement}" for achievement in artist_context.achievements),
            f"📱 Social Media:\n" + "\n".join(f"  • {platform}: {handle}" for platform, handle in artist_context.social_media.items()),
            f"🎧 Streaming Profiles:\n" + "\n".join(f"  • {platform}: {link}" for platform, link in artist_context.streaming_profiles.items())
        ]
        return "\n\n".join(summary)

    def get_confirmation_keyboard(self) -> InlineKeyboardMarkup:
        """Create keyboard with confirmation options."""
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
             InlineKeyboardButton("✏️ Edit", callback_data="edit_profile")]
        ]
        return InlineKeyboardMarkup(keyboard) 