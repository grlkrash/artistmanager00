"""Music management handlers for the Artist Manager Bot."""
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    BaseHandler
)
from ..core.base_handler import BaseBotHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MusicHandlers(BaseBotHandler):
    """Handlers for music-related functionality."""
    
    def __init__(self, bot):
        """Initialize music handlers."""
        super().__init__(bot)
        self.group = 5  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get music-related handlers."""
        return [
            CommandHandler("music", self.show_menu),
            CallbackQueryHandler(self.handle_callback, pattern="^(menu_music|music_.*|music_menu)$")
        ]

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle music-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both music_ and menu_music patterns
            action = query.data.replace("menu_music", "menu").replace("music_", "").strip("_")
            logger.info(f"Music handler processing callback: {query.data} -> {action}")
            
            if action == "menu" or action == "":
                await self.show_menu(update, context)
            elif action == "upload":
                await self._show_upload_options(update, context)
            elif action == "catalog":
                await self._show_catalog(update, context)
            elif action == "analytics":
                await self._show_music_analytics(update, context)
            elif action == "distribution":
                await self._show_distribution_options(update, context)
            elif action.startswith("track_"):
                track_id = action.replace("track_", "")
                await self._show_track_management(update, context, track_id)
            else:
                logger.warning(f"Unknown music action: {action}")
                await self.show_menu(update, context)
                
        except Exception as e:
            logger.error(f"Error in music callback handler: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="music_menu")
                ]])
            )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the music menu."""
        keyboard = [
            [
                InlineKeyboardButton("Upload Music", callback_data="music_upload"),
                InlineKeyboardButton("Music Catalog", callback_data="music_catalog")
            ],
            [
                InlineKeyboardButton("Analytics", callback_data="music_analytics"),
                InlineKeyboardButton("Distribution", callback_data="music_distribution")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            "🎵 *Music Management*\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def _show_upload_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show music upload options."""
        keyboard = [
            [
                InlineKeyboardButton("Single Track", callback_data="music_upload_single"),
                InlineKeyboardButton("Album", callback_data="music_upload_album")
            ],
            [
                InlineKeyboardButton("EP", callback_data="music_upload_ep"),
                InlineKeyboardButton("Remix", callback_data="music_upload_remix")
            ],
            [InlineKeyboardButton("« Back", callback_data="music_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "What type of music would you like to upload?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_catalog(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show music catalog."""
        # Get user's tracks
        user_id = update.effective_user.id
        tracks = await self.bot.task_manager_integration.get_tracks(user_id)
        
        if not tracks:
            keyboard = [
                [InlineKeyboardButton("Upload Music", callback_data="music_upload")],
                [InlineKeyboardButton("« Back", callback_data="music_menu")]
            ]
            await self._send_or_edit_message(
                update,
                "Your music catalog is empty. Would you like to upload some music?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        # Format catalog message
        message = "🎵 Your Music Catalog:\n\n"
        keyboard = []
        
        for track in tracks:
            message += f"🎧 {track.title}\n"
            if track.release_date:
                message += f"Released: {track.release_date.strftime('%Y-%m-%d')}\n"
            message += f"Type: {track.type}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"Manage: {track.title[:20]}...", callback_data=f"music_track_{track.id}")
            ])
            
        keyboard.append([InlineKeyboardButton("« Back", callback_data="music_menu")])
        
        await self._send_or_edit_message(
            update,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_music_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show music analytics."""
        try:
            analytics = await self.bot.task_manager_integration.get_music_analytics()
            
            message = (
                "📊 *Music Analytics*\n\n"
                f"Total Tracks: {analytics['total_tracks']}\n"
                f"Total Albums: {analytics['total_albums']}\n"
                f"Total Streams: {analytics['total_streams']:,}\n"
                f"Total Revenue: ${analytics['total_revenue']:,.2f}\n\n"
                "*Top Performing Tracks:*\n"
            )
            
            for track in analytics['top_tracks'][:5]:
                message += f"• {track['title']} - {track['streams']:,} streams\n"
                
            message += "\n*Platform Performance:*\n"
            for platform, stats in analytics['platform_stats'].items():
                message += f"• {platform}: {stats['streams']:,} streams (${stats['revenue']:,.2f})\n"
                
            keyboard = [[InlineKeyboardButton("« Back", callback_data="music_menu")]]
            
            await self._send_or_edit_message(
                update,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error showing music analytics: {str(e)}")
            await self._handle_error(update)

    async def _show_distribution_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show music distribution options."""
        keyboard = [
            [
                InlineKeyboardButton("Submit Release", callback_data="music_distribute_new"),
                InlineKeyboardButton("View Releases", callback_data="music_distribute_view")
            ],
            [
                InlineKeyboardButton("Distribution Stats", callback_data="music_distribute_stats"),
                InlineKeyboardButton("Manage Platforms", callback_data="music_distribute_platforms")
            ],
            [InlineKeyboardButton("« Back", callback_data="music_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "🌐 *Music Distribution*\n\n"
            "Manage your music distribution across platforms:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def _show_track_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, track_id: str) -> None:
        """Show management options for a specific track."""
        try:
            track = await self.bot.task_manager_integration.get_track(track_id)
            if not track:
                await self._send_or_edit_message(
                    update,
                    "Track not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="music_menu")
                    ]])
                )
                return
                
            # Format track details
            message = (
                f"🎵 {track.title}\n\n"
                f"Artist: {track.artist}\n"
                f"Type: {track.type}\n"
                f"Genre: {track.genre}\n"
                f"Duration: {track.duration}\n"
            )
            if track.release_date:
                message += f"Released: {track.release_date.strftime('%Y-%m-%d')}\n"
                
            keyboard = [
                [
                    InlineKeyboardButton("Edit Details", callback_data=f"music_edit_{track.id}"),
                    InlineKeyboardButton("View Stats", callback_data=f"music_stats_{track.id}")
                ],
                [
                    InlineKeyboardButton("Distribution", callback_data=f"music_distribute_{track.id}"),
                    InlineKeyboardButton("Promotion", callback_data=f"music_promote_{track.id}")
                ],
                [
                    InlineKeyboardButton("Archive Track", callback_data=f"music_archive_{track.id}"),
                    InlineKeyboardButton("Delete Track", callback_data=f"music_delete_{track.id}")
                ],
                [InlineKeyboardButton("« Back", callback_data="music_menu")]
            ]
            
            await self._send_or_edit_message(
                update,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing track management: {str(e)}")
            await self._handle_error(update) 