"""Music management handlers."""
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, BaseHandler
from .base_handler import BaseBotHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MusicHandlers(BaseBotHandler):
    """Handlers for music-related functionality."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 5  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get music-related handlers."""
        return [
            CommandHandler("music", self.show_menu),
            CallbackQueryHandler(self.handle_music_callback, pattern="^(menu_music|music_.*|music_menu)$")
        ]

    async def handle_music_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle music-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both music_ and menu_music patterns
            original_data = query.data
            action = query.data.replace("music_", "").replace("menu_music", "menu").replace("music_menu", "menu")
            logger.info(f"Music handler processing callback: {original_data} -> {action}")
            
            if action == "menu":
                logger.info("Showing music menu")
                await self.show_menu(update, context)
            elif action == "release":
                logger.info("Showing release options")
                await self._show_release_options(update, context)
            elif action == "analytics":
                logger.info("Showing analytics")
                await self._show_analytics(update, context)
            elif action == "back":
                logger.info("Returning to main menu")
                await self.bot.show_menu(update, context)
            else:
                logger.warning(f"Unknown action in music handler: {action}")
                await self._send_or_edit_message(
                    update,
                    "This feature is coming soon!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="music_menu")
                    ]])
                )
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
                InlineKeyboardButton("New Release", callback_data="music_release"),
                InlineKeyboardButton("Analytics", callback_data="music_analytics")
            ],
            [
                InlineKeyboardButton("Catalog", callback_data="music_catalog"),
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

    async def _show_release_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show release options."""
        keyboard = [
            [
                InlineKeyboardButton("Single", callback_data="music_release_single"),
                InlineKeyboardButton("EP", callback_data="music_release_ep")
            ],
            [
                InlineKeyboardButton("Album", callback_data="music_release_album"),
                InlineKeyboardButton("Remix", callback_data="music_release_remix")
            ],
            [InlineKeyboardButton("« Back", callback_data="music_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "What type of release would you like to create?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show music analytics."""
        keyboard = [[InlineKeyboardButton("« Back", callback_data="music_menu")]]
        
        await self._send_or_edit_message(
            update,
            "Your music analytics will appear here soon!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        ) 