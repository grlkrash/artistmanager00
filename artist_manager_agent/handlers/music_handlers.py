"""Music service handlers for the Artist Manager Bot."""
from datetime import datetime
import uuid
import logging
from typing import Dict, Optional, List
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, ForceReply, CallbackQuery, ReplyKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    BaseHandler
)
from ..models import Track, Release, ReleaseType, MasteringPreset, DistributionPlatform
from .base_handler import BaseHandlerMixin

logger = logging.getLogger(__name__)

# Conversation states for release creation
AWAITING_RELEASE_TITLE = "AWAITING_RELEASE_TITLE"
AWAITING_RELEASE_TYPE = "AWAITING_RELEASE_TYPE"
AWAITING_RELEASE_GENRE = "AWAITING_RELEASE_GENRE"
AWAITING_RELEASE_DATE = "AWAITING_RELEASE_DATE"
AWAITING_TRACK_UPLOAD = "AWAITING_TRACK_UPLOAD"
AWAITING_TRACK_TITLE = "AWAITING_TRACK_TITLE"
AWAITING_TRACK_GENRE = "AWAITING_TRACK_GENRE"
AWAITING_ARTWORK_UPLOAD = "AWAITING_ARTWORK_UPLOAD"

# Conversation states for mastering
AWAITING_MASTER_TRACK = "AWAITING_MASTER_TRACK"
AWAITING_MASTER_PRESET = "AWAITING_MASTER_PRESET"
AWAITING_REFERENCE_TRACK = "AWAITING_REFERENCE_TRACK"
AWAITING_TARGET_LOUDNESS = "AWAITING_TARGET_LOUDNESS"

# Conversation states for distribution
AWAITING_DISTRIBUTION_PLATFORMS = "AWAITING_DISTRIBUTION_PLATFORMS"
AWAITING_DISTRIBUTION_TERRITORIES = "AWAITING_DISTRIBUTION_TERRITORIES"
AWAITING_DISTRIBUTION_DATE = "AWAITING_DISTRIBUTION_DATE"
AWAITING_DISTRIBUTION_PRICE = "AWAITING_DISTRIBUTION_PRICE"

class MusicHandlers(BaseHandlerMixin):
    """Handlers for music-related functionality."""
    
    group = "music"  # Handler group for registration
    
    def __init__(self, bot):
        self.bot = bot

    def get_handlers(self) -> List[BaseHandler]:
        """Get music-related handlers."""
        return [
            CommandHandler("music", self.show_music_options),
            CommandHandler("release", self.manage_release),
            CommandHandler("master", self.manage_mastering),
            CommandHandler("distribute", self.manage_distribution),
            self.get_release_conversation_handler(),
            self.get_mastering_conversation_handler(),
            self.get_distribution_conversation_handler(),
            CallbackQueryHandler(self.handle_music_callback, pattern="^music_")
        ]

    def get_release_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for release creation."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_release_creation, pattern="^music_release_new$"),
                CommandHandler("newrelease", self.start_release_creation)
            ],
            states={
                AWAITING_RELEASE_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_release_title)
                ],
                AWAITING_RELEASE_TYPE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_release_type)
                ],
                AWAITING_RELEASE_GENRE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_release_genre)
                ],
                AWAITING_RELEASE_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_release_date)
                ],
                AWAITING_TRACK_UPLOAD: [
                    MessageHandler(filters.AUDIO | filters.DOCUMENT, self.handle_track_upload)
                ],
                AWAITING_TRACK_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_track_title)
                ],
                AWAITING_TRACK_GENRE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_track_genre)
                ],
                AWAITING_ARTWORK_UPLOAD: [
                    MessageHandler(filters.PHOTO | filters.DOCUMENT, self.handle_artwork_upload)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_release_creation)
            ],
            name="release_creation",
            persistent=True
        )

    def get_mastering_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for mastering."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_mastering, pattern="^music_master_new$"),
                CommandHandler("newmaster", self.start_mastering)
            ],
            states={
                AWAITING_MASTER_TRACK: [
                    MessageHandler(filters.AUDIO | filters.DOCUMENT, self.handle_master_track)
                ],
                AWAITING_MASTER_PRESET: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_master_preset)
                ],
                AWAITING_REFERENCE_TRACK: [
                    MessageHandler(filters.AUDIO | filters.DOCUMENT, self.handle_reference_track),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_reference_skip)
                ],
                AWAITING_TARGET_LOUDNESS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_target_loudness)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_mastering)
            ],
            name="mastering",
            persistent=True
        )

    def get_distribution_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for distribution setup."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_distribution, pattern="^music_distribute_new$"),
                CommandHandler("newdistribution", self.start_distribution)
            ],
            states={
                AWAITING_DISTRIBUTION_PLATFORMS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_distribution_platforms)
                ],
                AWAITING_DISTRIBUTION_TERRITORIES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_distribution_territories)
                ],
                AWAITING_DISTRIBUTION_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_distribution_date)
                ],
                AWAITING_DISTRIBUTION_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_distribution_price)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_distribution)
            ],
            name="distribution",
            persistent=True
        )

    async def show_music_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show music-related options."""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("Release", callback_data="music_release"),
                    InlineKeyboardButton("Mastering", callback_data="music_master")
                ],
                [
                    InlineKeyboardButton("Distribution", callback_data="music_distribute"),
                    InlineKeyboardButton("Analytics", callback_data="music_analytics")
                ]
            ]
            
            await update.message.reply_text(
                "🎵 Music Services:\n\n"
                "• Manage releases\n"
                "• Master your tracks\n"
                "• Set up distribution\n"
                "• View analytics",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing music options: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error loading music options. Please try again later."
            )

    async def manage_release(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle release management."""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("New Release", callback_data="music_release_new"),
                    InlineKeyboardButton("Schedule", callback_data="music_release_schedule")
                ],
                [
                    InlineKeyboardButton("Promotion", callback_data="music_release_promo"),
                    InlineKeyboardButton("Analytics", callback_data="music_release_analytics")
                ]
            ]
            
            await update.message.reply_text(
                "📀 Release Management:\n\n"
                "Select an option to manage your releases:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error handling release management: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error accessing release functions. Please try again later."
            )

    async def manage_mastering(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle mastering services."""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("Upload Track", callback_data="music_master_upload"),
                    InlineKeyboardButton("Presets", callback_data="music_master_presets")
                ],
                [
                    InlineKeyboardButton("Review", callback_data="music_master_review"),
                    InlineKeyboardButton("Download", callback_data="music_master_download")
                ]
            ]
            
            await update.message.reply_text(
                "🎚 Mastering Services:\n\n"
                "Master your tracks professionally:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error handling mastering services: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error with mastering services. Please try again later."
            )

    async def manage_distribution(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle distribution management."""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("New Distribution", callback_data="music_distribute_new"),
                    InlineKeyboardButton("Platforms", callback_data="music_distribute_platforms")
                ],
                [
                    InlineKeyboardButton("Reports", callback_data="music_distribute_reports"),
                    InlineKeyboardButton("Settings", callback_data="music_distribute_settings")
                ]
            ]
            
            await update.message.reply_text(
                "🌐 Distribution Management:\n\n"
                "Manage your music distribution:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error handling distribution: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error with distribution management. Please try again later."
            )

    async def handle_music_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle music-related callbacks."""
        try:
            query = update.callback_query
            await query.answer()
            
            action = query.data.replace("music_", "")
            
            if action.startswith("release_"):
                await self._handle_release_action(query, action)
            elif action.startswith("master_"):
                await self._handle_master_action(query, action)
            elif action.startswith("distribute_"):
                await self._handle_distribute_action(query, action)
            else:
                await query.message.reply_text("This feature is coming soon!")
                
        except Exception as e:
            logger.error(f"Error handling music callback: {str(e)}")
            await update.effective_message.reply_text(
                "Sorry, there was an error processing your request. Please try again later."
            )

    async def _handle_release_action(self, query: CallbackQuery, action: str) -> None:
        """Handle release-specific actions."""
        action = action.replace("release_", "")
        # Implement release actions (new, schedule, promo, analytics)
        await query.message.reply_text(f"Release {action} feature coming soon!")

    async def _handle_master_action(self, query: CallbackQuery, action: str) -> None:
        """Handle mastering-specific actions."""
        action = action.replace("master_", "")
        # Implement mastering actions (upload, presets, review, download)
        await query.message.reply_text(f"Mastering {action} feature coming soon!")

    async def _handle_distribute_action(self, query: CallbackQuery, action: str) -> None:
        """Handle distribution-specific actions."""
        action = action.replace("distribute_", "")
        # Implement distribution actions (new, platforms, reports, settings)
        await query.message.reply_text(f"Distribution {action} feature coming soon!")

    async def start_release_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start release creation flow."""
        try:
            # Initialize release data
            context.user_data["creating_release"] = {
                "tracks": [],
                "id": str(uuid.uuid4())
            }
            
            await update.message.reply_text(
                "🎵 Let's create a new release!\n\n"
                "What's the title of your release?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_RELEASE_TITLE
            
        except Exception as e:
            logger.error(f"Error starting release creation: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting release creation. Please try again."
            )
            return ConversationHandler.END

    async def handle_release_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle release title input."""
        title = update.message.text.strip()
        context.user_data["creating_release"]["title"] = title
        
        # Show release type options
        keyboard = [
            ["Single", "EP"],
            ["Album", "Remix"]
        ]
        
        await update.message.reply_text(
            f"Great! What type of release is '{title}'?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_RELEASE_TYPE

    async def handle_release_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle release type selection."""
        release_type = update.message.text.lower()
        if release_type not in [t.value for t in ReleaseType]:
            await update.message.reply_text(
                "Please select a valid release type: single, ep, album, or remix"
            )
            return AWAITING_RELEASE_TYPE
            
        context.user_data["creating_release"]["type"] = release_type
        
        # Common genres keyboard
        keyboard = [
            ["Pop", "Rock", "Hip Hop"],
            ["Electronic", "R&B", "Jazz"],
            ["Classical", "Folk", "Other"]
        ]
        
        await update.message.reply_text(
            "What's the primary genre of this release?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_RELEASE_GENRE

    async def handle_release_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle release genre input."""
        genre = update.message.text.strip()
        context.user_data["creating_release"]["genre"] = genre
        
        await update.message.reply_text(
            "When do you want to release this?\n"
            "Enter the date in YYYY-MM-DD format:",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_RELEASE_DATE

    async def handle_release_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle release date input."""
        try:
            release_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
            context.user_data["creating_release"]["release_date"] = release_date
            
            await update.message.reply_text(
                "Great! Now let's add tracks to your release.\n\n"
                "Send me the first audio file:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_TRACK_UPLOAD
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid date in YYYY-MM-DD format:"
            )
            return AWAITING_RELEASE_DATE

    async def handle_track_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle track file upload."""
        try:
            file = update.message.audio or update.message.document
            if not file:
                await update.message.reply_text(
                    "Please send an audio file in a supported format (MP3, WAV, FLAC):"
                )
                return AWAITING_TRACK_UPLOAD
                
            # Save file info
            file_info = await file.get_file()
            file_path = Path(f"uploads/tracks/{file.file_id}")
            await file_info.download(file_path)
            
            context.user_data["current_track"] = {
                "file_path": file_path,
                "duration": getattr(file, "duration", None)
            }
            
            await update.message.reply_text(
                "What's the title of this track?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_TRACK_TITLE
            
        except Exception as e:
            logger.error(f"Error handling track upload: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your track. Please try again."
            )
            return AWAITING_TRACK_UPLOAD

    async def handle_track_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle track title input."""
        title = update.message.text.strip()
        context.user_data["current_track"]["title"] = title
        
        # Use release genre as default, but allow override
        release_genre = context.user_data["creating_release"]["genre"]
        keyboard = [
            [f"Same as release ({release_genre})"],
            ["Different genre"]
        ]
        
        await update.message.reply_text(
            "What's the genre of this track?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_TRACK_GENRE

    async def handle_track_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle track genre input."""
        genre_input = update.message.text.strip()
        
        if genre_input.startswith("Same as release"):
            genre = context.user_data["creating_release"]["genre"]
        else:
            genre = genre_input
            
        # Create track
        track_data = context.user_data.pop("current_track")
        track = Track(
            title=track_data["title"],
            artist=context.user_data["creating_release"]["artist"],
            genre=genre,
            file_path=track_data["file_path"],
            duration=track_data["duration"],
            release_date=context.user_data["creating_release"]["release_date"]
        )
        
        # Add to release
        context.user_data["creating_release"]["tracks"].append(track)
        
        # Check if we need more tracks based on release type
        release_type = context.user_data["creating_release"]["type"]
        current_tracks = len(context.user_data["creating_release"]["tracks"])
        
        if release_type == "single" and current_tracks >= 1:
            await update.message.reply_text(
                "Great! Now send me the cover artwork for your release\n"
                "(Send as an image or document):",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_ARTWORK_UPLOAD
        elif release_type == "ep" and current_tracks >= 3:
            await update.message.reply_text(
                "You've added enough tracks for an EP.\n"
                "Would you like to add another track or proceed to artwork?\n\n"
                "Send another audio file to add more tracks, or send artwork to continue.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_ARTWORK_UPLOAD
        else:
            await update.message.reply_text(
                f"Track {current_tracks} added successfully!\n"
                "Send me the next audio file:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_TRACK_UPLOAD

    async def handle_artwork_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle artwork upload and complete release creation."""
        try:
            file = update.message.photo[-1] if update.message.photo else update.message.document
            if not file:
                await update.message.reply_text(
                    "Please send the cover artwork as an image or document:"
                )
                return AWAITING_ARTWORK_UPLOAD
                
            # Save artwork
            file_info = await file.get_file()
            artwork_path = Path(f"uploads/artwork/{file.file_id}")
            await file_info.download(artwork_path)
            
            # Create release
            release_data = context.user_data.pop("creating_release")
            release = Release(
                id=release_data["id"],
                title=release_data["title"],
                artist=release_data["artist"],
                type=ReleaseType(release_data["type"]),
                genre=release_data["genre"],
                release_date=release_data["release_date"],
                tracks=release_data["tracks"],
                artwork_path=artwork_path
            )
            
            # Save to music services
            await self.bot.music_services.create_release(release)
            
            # Show success message
            keyboard = [
                [
                    InlineKeyboardButton("Master Tracks", callback_data=f"music_master_release_{release.id}"),
                    InlineKeyboardButton("Set Up Distribution", callback_data=f"music_distribute_release_{release.id}")
                ],
                [
                    InlineKeyboardButton("View Release", callback_data=f"music_release_view_{release.id}"),
                    InlineKeyboardButton("Back to Music", callback_data="music_menu")
                ]
            ]
            
            await update.message.reply_text(
                f"✨ Release '{release.title}' created successfully!\n\n"
                f"Type: {release.type.value.title()}\n"
                f"Genre: {release.genre}\n"
                f"Release Date: {release.release_date.strftime('%Y-%m-%d')}\n"
                f"Tracks: {len(release.tracks)}\n\n"
                "What would you like to do next?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error handling artwork upload: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your artwork. Please try again."
            )
            return AWAITING_ARTWORK_UPLOAD

    async def cancel_release_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel release creation."""
        if "creating_release" in context.user_data:
            # Clean up any uploaded files
            release_data = context.user_data.pop("creating_release")
            for track in release_data.get("tracks", []):
                if track.file_path.exists():
                    track.file_path.unlink()
                    
        await update.message.reply_text(
            "Release creation cancelled. You can start over with /newrelease"
        )
        return ConversationHandler.END 