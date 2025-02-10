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

# Conversation states for promotion
AWAITING_CAMPAIGN_TITLE = "AWAITING_CAMPAIGN_TITLE"
AWAITING_CAMPAIGN_TYPE = "AWAITING_CAMPAIGN_TYPE"
AWAITING_CAMPAIGN_PLATFORMS = "AWAITING_CAMPAIGN_PLATFORMS"
AWAITING_CAMPAIGN_BUDGET = "AWAITING_CAMPAIGN_BUDGET"
AWAITING_CAMPAIGN_START_DATE = "AWAITING_CAMPAIGN_START_DATE"
AWAITING_CAMPAIGN_END_DATE = "AWAITING_CAMPAIGN_END_DATE"

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
            CallbackQueryHandler(self.handle_music_callback, pattern="^music_"),
            CommandHandler("analytics", self.show_analytics),
            CommandHandler("promotion", self.manage_promotion),
            CommandHandler("newcampaign", self.start_promotion_campaign)
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

    async def start_mastering(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start mastering flow."""
        try:
            # Initialize mastering data
            context.user_data["mastering_job"] = {
                "id": str(uuid.uuid4())
            }
            
            await update.message.reply_text(
                "🎚 Let's master your track!\n\n"
                "Send me the audio file you want to master:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_MASTER_TRACK
            
        except Exception as e:
            logger.error(f"Error starting mastering: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting mastering. Please try again."
            )
            return ConversationHandler.END

    async def handle_master_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle master track upload."""
        try:
            file = update.message.audio or update.message.document
            if not file:
                await update.message.reply_text(
                    "Please send an audio file in a supported format (WAV preferred):"
                )
                return AWAITING_MASTER_TRACK
                
            # Save file info
            file_info = await file.get_file()
            file_path = Path(f"uploads/masters/{file.file_id}")
            await file_info.download(file_path)
            
            context.user_data["mastering_job"]["track_path"] = file_path
            
            # Show preset options
            keyboard = [
                [
                    InlineKeyboardButton("Balanced", callback_data="master_preset_balanced"),
                    InlineKeyboardButton("Warm", callback_data="master_preset_warm")
                ],
                [
                    InlineKeyboardButton("Bright", callback_data="master_preset_bright"),
                    InlineKeyboardButton("Aggressive", callback_data="master_preset_aggressive")
                ],
                [
                    InlineKeyboardButton("Bass Heavy", callback_data="master_preset_bass_heavy"),
                    InlineKeyboardButton("Vocal Focus", callback_data="master_preset_vocal_focus")
                ]
            ]
            
            await update.message.reply_text(
                "Choose a mastering preset that best fits your track:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_MASTER_PRESET
            
        except Exception as e:
            logger.error(f"Error handling master track: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your track. Please try again."
            )
            return AWAITING_MASTER_TRACK

    async def handle_master_preset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle mastering preset selection."""
        query = update.callback_query
        await query.answer()
        
        preset = query.data.replace("master_preset_", "")
        if preset not in [p.value for p in MasteringPreset]:
            await query.message.reply_text(
                "Please select a valid mastering preset"
            )
            return AWAITING_MASTER_PRESET
            
        context.user_data["mastering_job"]["preset"] = preset
        
        await query.message.reply_text(
            "Would you like to upload a reference track?\n\n"
            "A reference track helps achieve a similar sound.\n"
            "Send an audio file, or type 'skip' to continue:",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_REFERENCE_TRACK

    async def handle_reference_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle reference track upload."""
        try:
            file = update.message.audio or update.message.document
            if not file:
                await update.message.reply_text(
                    "Please send an audio file or type 'skip':"
                )
                return AWAITING_REFERENCE_TRACK
                
            # Save file info
            file_info = await file.get_file()
            file_path = Path(f"uploads/references/{file.file_id}")
            await file_info.download(file_path)
            
            context.user_data["mastering_job"]["reference_path"] = file_path
            
            await update.message.reply_text(
                "What's your target loudness in LUFS?\n"
                "Common values:\n"
                "• Streaming: -14 LUFS\n"
                "• Club: -8 LUFS\n"
                "• CD: -9 LUFS\n\n"
                "Enter a number or type 'auto' for automatic detection:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_TARGET_LOUDNESS
            
        except Exception as e:
            logger.error(f"Error handling reference track: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error processing your reference track. Please try again."
            )
            return AWAITING_REFERENCE_TRACK

    async def handle_reference_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle skipping reference track."""
        if update.message.text.lower() == "skip":
            await update.message.reply_text(
                "What's your target loudness in LUFS?\n"
                "Common values:\n"
                "• Streaming: -14 LUFS\n"
                "• Club: -8 LUFS\n"
                "• CD: -9 LUFS\n\n"
                "Enter a number or type 'auto' for automatic detection:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_TARGET_LOUDNESS
        else:
            await update.message.reply_text(
                "Please send an audio file or type 'skip':"
            )
            return AWAITING_REFERENCE_TRACK

    async def handle_target_loudness(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle target loudness input and start mastering."""
        try:
            loudness_input = update.message.text.strip().lower()
            
            if loudness_input == "auto":
                target_loudness = None
            else:
                try:
                    target_loudness = float(loudness_input)
                except ValueError:
                    await update.message.reply_text(
                        "Please enter a valid number or type 'auto':"
                    )
                    return AWAITING_TARGET_LOUDNESS
            
            # Create mastering job
            job_data = context.user_data.pop("mastering_job")
            job = MasteringJob(
                track=Track(
                    title="Master",  # Temporary title
                    artist="",  # Will be set from profile
                    file_path=job_data["track_path"],
                    genre="",  # Will be detected
                    release_date=datetime.now()
                ),
                preset=MasteringPreset(job_data["preset"]),
                reference_track=job_data.get("reference_path"),
                target_loudness=target_loudness
            )
            
            # Submit for mastering
            result = await self.bot.music_services.submit_for_mastering(job)
            
            # Show processing message
            keyboard = [
                [
                    InlineKeyboardButton("Check Status", callback_data=f"music_master_status_{result['job_id']}"),
                    InlineKeyboardButton("Cancel", callback_data=f"music_master_cancel_{result['job_id']}")
                ]
            ]
            
            await update.message.reply_text(
                "🎚 Mastering in progress!\n\n"
                "Your track is being processed with:\n"
                f"• Preset: {job.preset.value.title()}\n"
                f"• Target Loudness: {job.target_loudness or 'Auto'} LUFS\n"
                f"• Reference Track: {'Yes' if job.reference_track else 'No'}\n\n"
                "I'll notify you when it's ready!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error handling target loudness: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting the mastering process. Please try again."
            )
            return ConversationHandler.END

    async def cancel_mastering(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel mastering process."""
        if "mastering_job" in context.user_data:
            # Clean up any uploaded files
            job_data = context.user_data.pop("mastering_job")
            for key in ["track_path", "reference_path"]:
                if key in job_data and job_data[key].exists():
                    job_data[key].unlink()
                    
        await update.message.reply_text(
            "Mastering cancelled. You can start over with /newmaster"
        )
        return ConversationHandler.END

    async def start_distribution(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start distribution setup flow."""
        try:
            # Initialize distribution data
            context.user_data["distributing_release"] = {
                "id": str(uuid.uuid4()),
                "platforms": [],
                "territories": []
            }
            
            # Show platform options
            keyboard = []
            for platform in DistributionPlatform:
                keyboard.append([
                    InlineKeyboardButton(
                        platform.value.replace("_", " ").title(),
                        callback_data=f"distribute_platform_{platform.value}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("Done", callback_data="distribute_platforms_done")])
            
            await update.message.reply_text(
                "🌐 Let's set up distribution!\n\n"
                "Select the platforms you want to distribute to:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_DISTRIBUTION_PLATFORMS
            
        except Exception as e:
            logger.error(f"Error starting distribution: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting distribution setup. Please try again."
            )
            return ConversationHandler.END

    async def handle_distribution_platforms(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle platform selection."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "distribute_platforms_done":
            if not context.user_data["distributing_release"]["platforms"]:
                await query.message.reply_text(
                    "Please select at least one platform:"
                )
                return AWAITING_DISTRIBUTION_PLATFORMS
                
            # Show territory options
            keyboard = [
                [
                    InlineKeyboardButton("Worldwide", callback_data="distribute_territory_worldwide"),
                    InlineKeyboardButton("Select Regions", callback_data="distribute_territory_select")
                ]
            ]
            
            await query.message.edit_text(
                "Where would you like to distribute your music?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_DISTRIBUTION_TERRITORIES
            
        else:
            platform = query.data.replace("distribute_platform_", "")
            if platform in [p.value for p in DistributionPlatform]:
                platforms = context.user_data["distributing_release"]["platforms"]
                if platform in platforms:
                    platforms.remove(platform)
                    await query.message.edit_text(
                        f"Removed {platform.replace('_', ' ').title()} from distribution"
                    )
                else:
                    platforms.append(platform)
                    await query.message.edit_text(
                        f"Added {platform.replace('_', ' ').title()} to distribution"
                    )
            return AWAITING_DISTRIBUTION_PLATFORMS

    async def handle_distribution_territories(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle territory selection."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "distribute_territory_worldwide":
            context.user_data["distributing_release"]["territories"] = ["worldwide"]
            
            await query.message.edit_text(
                "When would you like to release?\n"
                "Enter the date in YYYY-MM-DD format:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_DISTRIBUTION_DATE
            
        elif query.data == "distribute_territory_select":
            # Show region selection
            keyboard = [
                [
                    InlineKeyboardButton("North America", callback_data="distribute_region_na"),
                    InlineKeyboardButton("Europe", callback_data="distribute_region_eu")
                ],
                [
                    InlineKeyboardButton("Asia", callback_data="distribute_region_asia"),
                    InlineKeyboardButton("Oceania", callback_data="distribute_region_oceania")
                ],
                [
                    InlineKeyboardButton("South America", callback_data="distribute_region_sa"),
                    InlineKeyboardButton("Africa", callback_data="distribute_region_africa")
                ],
                [InlineKeyboardButton("Done", callback_data="distribute_regions_done")]
            ]
            
            await query.message.edit_text(
                "Select regions for distribution:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_DISTRIBUTION_TERRITORIES
            
        elif query.data == "distribute_regions_done":
            if not context.user_data["distributing_release"]["territories"]:
                await query.message.reply_text(
                    "Please select at least one region:"
                )
                return AWAITING_DISTRIBUTION_TERRITORIES
                
            await query.message.edit_text(
                "When would you like to release?\n"
                "Enter the date in YYYY-MM-DD format:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_DISTRIBUTION_DATE
            
        else:
            region = query.data.replace("distribute_region_", "")
            territories = context.user_data["distributing_release"]["territories"]
            if region in territories:
                territories.remove(region)
                await query.message.edit_text(
                    f"Removed {region.upper()} from distribution"
                )
            else:
                territories.append(region)
                await query.message.edit_text(
                    f"Added {region.upper()} to distribution"
                )
            return AWAITING_DISTRIBUTION_TERRITORIES

    async def handle_distribution_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle distribution date input."""
        try:
            release_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
            context.user_data["distributing_release"]["release_date"] = release_date
            
            # Show pricing options
            keyboard = [
                [
                    InlineKeyboardButton("Free", callback_data="distribute_price_0"),
                    InlineKeyboardButton("$0.99", callback_data="distribute_price_0.99")
                ],
                [
                    InlineKeyboardButton("$1.29", callback_data="distribute_price_1.29"),
                    InlineKeyboardButton("Custom", callback_data="distribute_price_custom")
                ]
            ]
            
            await update.message.reply_text(
                "Set your release price:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_DISTRIBUTION_PRICE
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid date in YYYY-MM-DD format:"
            )
            return AWAITING_DISTRIBUTION_DATE

    async def handle_distribution_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle distribution price selection and complete setup."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "distribute_price_custom":
                await query.message.edit_text(
                    "Enter your custom price in USD (e.g. 2.99):",
                    reply_markup=ForceReply(selective=True)
                )
                return AWAITING_DISTRIBUTION_PRICE
                
            # Get price from callback data
            price = float(query.data.replace("distribute_price_", ""))
            context.user_data["distributing_release"]["price"] = price
            
            # Create distribution setup
            distribution_data = context.user_data.pop("distributing_release")
            
            # Show summary and confirmation
            platforms_text = "\n".join(
                f"• {p.replace('_', ' ').title()}"
                for p in distribution_data["platforms"]
            )
            
            territories_text = (
                "Worldwide"
                if "worldwide" in distribution_data["territories"]
                else "\n".join(f"• {t.upper()}" for t in distribution_data["territories"])
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("Confirm", callback_data=f"distribute_confirm_{distribution_data['id']}"),
                    InlineKeyboardButton("Cancel", callback_data="distribute_cancel")
                ]
            ]
            
            await query.message.edit_text(
                "📝 Distribution Summary\n\n"
                "Platforms:\n"
                f"{platforms_text}\n\n"
                "Territories:\n"
                f"{territories_text}\n\n"
                f"Release Date: {distribution_data['release_date'].strftime('%Y-%m-%d')}\n"
                f"Price: ${distribution_data['price']:.2f}\n\n"
                "Ready to submit?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error handling distribution price: {str(e)}")
            await update.effective_message.reply_text(
                "Sorry, there was an error setting up distribution. Please try again."
            )
            return ConversationHandler.END

    async def cancel_distribution(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel distribution setup."""
        if "distributing_release" in context.user_data:
            context.user_data.pop("distributing_release")
            
        await update.message.reply_text(
            "Distribution setup cancelled. You can start over with /newdistribution"
        )
        return ConversationHandler.END

    async def show_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show music analytics dashboard."""
        try:
            # Get all tracks
            tracks = list(self.bot.music_services.tracks.values())
            
            if not tracks:
                await update.message.reply_text(
                    "No tracks found to analyze. Create a release first!"
                )
                return

            # Get analytics for each track
            analytics = []
            for track in tracks:
                # Get streaming stats
                stats = await self.bot.music_services.get_streaming_stats(track.id)
                
                # Get playlist analytics
                playlists = await self.bot.music_services.get_playlist_analytics(track.id)
                
                # Get demographics
                demographics = await self.bot.music_services.get_audience_demographics(track.id)
                
                analytics.append({
                    "track": track,
                    "stats": stats,
                    "playlists": playlists,
                    "demographics": demographics
                })
                
            # Create summary message
            message = "📊 Music Analytics\n\n"
            
            for data in analytics:
                track = data["track"]
                stats = data["stats"]
                playlists = data["playlists"]
                demographics = data["demographics"]
                
                message += f"🎵 {track.title}\n"
                
                # Streaming stats
                total_streams = sum(s.streams for s in stats)
                total_revenue = sum(s.revenue for s in stats)
                message += (
                    f"Streams: {total_streams:,}\n"
                    f"Revenue: ${total_revenue:,.2f}\n"
                )
                
                # Playlist stats
                message += (
                    f"Playlists: {playlists['total_playlists']}\n"
                    f"Playlist Streams: {playlists['total_streams_from_playlists']}\n"
                )
                
                # Top countries
                top_countries = sorted(
                    demographics["top_countries"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                message += "Top Countries: " + ", ".join(
                    f"{country} ({streams:,})"
                    for country, streams in top_countries
                ) + "\n\n"
                
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("Detailed Stats", callback_data="music_analytics_detailed"),
                    InlineKeyboardButton("Export Data", callback_data="music_analytics_export")
                ],
                [
                    InlineKeyboardButton("Revenue Report", callback_data="music_analytics_revenue"),
                    InlineKeyboardButton("Demographics", callback_data="music_analytics_demographics")
                ],
                [InlineKeyboardButton("Back to Music", callback_data="music_menu")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing analytics: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error loading analytics. Please try again later."
            )

    async def manage_promotion(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle promotion campaigns."""
        try:
            # Get active campaigns
            campaigns = list(self.bot.music_services.promotion_campaigns.values())
            active_campaigns = [c for c in campaigns if c.end_date > datetime.now()]
            
            message = "🚀 Promotion Campaigns\n\n"
            
            if active_campaigns:
                message += "Active Campaigns:\n"
                for campaign in active_campaigns:
                    message += (
                        f"📈 {campaign.title}\n"
                        f"Type: {campaign.type}\n"
                        f"Budget: ${campaign.budget:,.2f}\n"
                        f"Platforms: {', '.join(campaign.target_platforms)}\n"
                        f"Status: {campaign.status}\n\n"
                    )
            else:
                message += "No active campaigns.\n\n"
                
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("New Campaign", callback_data="music_promo_new"),
                    InlineKeyboardButton("View History", callback_data="music_promo_history")
                ],
                [
                    InlineKeyboardButton("Campaign Analytics", callback_data="music_promo_analytics"),
                    InlineKeyboardButton("Best Practices", callback_data="music_promo_tips")
                ],
                [InlineKeyboardButton("Back to Music", callback_data="music_menu")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error managing promotion: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error loading promotion data. Please try again later."
            )

    async def start_promotion_campaign(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start promotion campaign creation."""
        try:
            # Initialize campaign data
            context.user_data["creating_campaign"] = {
                "id": str(uuid.uuid4())
            }
            
            await update.message.reply_text(
                "🚀 Let's create a new promotion campaign!\n\n"
                "What's the title of your campaign?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_CAMPAIGN_TITLE
            
        except Exception as e:
            logger.error(f"Error starting campaign creation: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting campaign creation. Please try again."
            )
            return ConversationHandler.END

    async def handle_campaign_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle campaign title input."""
        title = update.message.text.strip()
        context.user_data["creating_campaign"]["title"] = title
        
        # Show campaign type options
        keyboard = [
            ["Social Media", "Playlist Pitching"],
            ["Press Release", "Influencer Outreach"],
            ["Paid Ads", "Email Marketing"]
        ]
        
        await update.message.reply_text(
            f"What type of campaign is '{title}'?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_CAMPAIGN_TYPE

    async def handle_campaign_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle campaign type selection."""
        campaign_type = update.message.text.strip().lower()
        context.user_data["creating_campaign"]["type"] = campaign_type
        
        # Show platform options
        keyboard = []
        for platform in DistributionPlatform:
            keyboard.append([
                InlineKeyboardButton(
                    platform.value.replace("_", " ").title(),
                    callback_data=f"promo_platform_{platform.value}"
                )
            ])
        keyboard.append([InlineKeyboardButton("Done", callback_data="promo_platforms_done")])
        
        await update.message.reply_text(
            "Select the platforms to target:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAITING_CAMPAIGN_PLATFORMS

    async def handle_campaign_platforms(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle campaign platform selection."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "promo_platforms_done":
            if not context.user_data["creating_campaign"].get("platforms"):
                await query.message.reply_text(
                    "Please select at least one platform:"
                )
                return AWAITING_CAMPAIGN_PLATFORMS
                
            await query.message.reply_text(
                "What's your budget for this campaign? (Enter amount in USD)",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_CAMPAIGN_BUDGET
            
        else:
            platform = query.data.replace("promo_platform_", "")
            if platform in [p.value for p in DistributionPlatform]:
                platforms = context.user_data["creating_campaign"].get("platforms", [])
                if platform in platforms:
                    platforms.remove(platform)
                    await query.message.edit_text(
                        f"Removed {platform.replace('_', ' ').title()} from campaign"
                    )
                else:
                    platforms.append(platform)
                    await query.message.edit_text(
                        f"Added {platform.replace('_', ' ').title()} to campaign"
                    )
                context.user_data["creating_campaign"]["platforms"] = platforms
            return AWAITING_CAMPAIGN_PLATFORMS

    async def handle_campaign_budget(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle campaign budget input."""
        try:
            budget = float(update.message.text.strip().replace("$", "").replace(",", ""))
            context.user_data["creating_campaign"]["budget"] = budget
            
            await update.message.reply_text(
                "When should the campaign start?\n"
                "Enter the date in YYYY-MM-DD format:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_CAMPAIGN_START_DATE
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for the budget (e.g. 1000):"
            )
            return AWAITING_CAMPAIGN_BUDGET

    async def handle_campaign_start_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle campaign start date input."""
        try:
            start_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
            context.user_data["creating_campaign"]["start_date"] = start_date
            
            await update.message.reply_text(
                "When should the campaign end?\n"
                "Enter the date in YYYY-MM-DD format:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_CAMPAIGN_END_DATE
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid date in YYYY-MM-DD format:"
            )
            return AWAITING_CAMPAIGN_START_DATE

    async def handle_campaign_end_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle campaign end date input and create campaign."""
        try:
            end_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
            campaign_data = context.user_data.pop("creating_campaign")
            
            # Create campaign
            campaign = await self.bot.music_services.create_promotion_campaign(
                title=campaign_data["title"],
                campaign_type=campaign_data["type"],
                target_platforms=campaign_data["platforms"],
                budget=campaign_data["budget"],
                start_date=campaign_data["start_date"],
                end_date=end_date
            )
            
            # Show success message
            keyboard = [
                [
                    InlineKeyboardButton("View Campaign", callback_data=f"music_promo_view_{campaign.id}"),
                    InlineKeyboardButton("Edit Campaign", callback_data=f"music_promo_edit_{campaign.id}")
                ],
                [InlineKeyboardButton("Back to Promotion", callback_data="music_promo")]
            ]
            
            await update.message.reply_text(
                f"✨ Campaign '{campaign.title}' created successfully!\n\n"
                f"Type: {campaign.type}\n"
                f"Budget: ${campaign.budget:,.2f}\n"
                f"Platforms: {', '.join(campaign.target_platforms)}\n"
                f"Duration: {campaign.start_date.strftime('%Y-%m-%d')} to {campaign.end_date.strftime('%Y-%m-%d')}\n\n"
                "What would you like to do next?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid date in YYYY-MM-DD format:"
            )
            return AWAITING_CAMPAIGN_END_DATE
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error creating your campaign. Please try again."
            )
            return ConversationHandler.END

    async def cancel_campaign_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel campaign creation."""
        if "creating_campaign" in context.user_data:
            context.user_data.pop("creating_campaign")
            
        await update.message.reply_text(
            "Campaign creation cancelled. You can start over with /newcampaign"
        )
        return ConversationHandler.END 