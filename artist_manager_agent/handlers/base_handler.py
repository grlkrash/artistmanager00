"""Base handler class for all bot handlers."""
from abc import ABC, abstractmethod
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import BaseHandler, ContextTypes
from ..utils.logger import get_logger

logger = get_logger(__name__)

class BaseBotHandler(ABC):
    """Abstract base class for all handlers."""
    
    def __init__(self, bot):
        """Initialize the handler."""
        self.bot = bot
        # Remove default group initialization - each handler must specify its own
        logger.info(f"Initializing {self.__class__.__name__}")

    @abstractmethod
    def get_handlers(self) -> List[BaseHandler]:
        """Get all handlers for this module."""
        pass

    @abstractmethod
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries."""
        pass

    @abstractmethod
    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the main menu for this module."""
        pass

    async def _send_or_edit_message(self, update: Update, text: str, reply_markup=None, parse_mode=None) -> None:
        """Helper to consistently send or edit messages."""
        try:
            handler_name = self.__class__.__name__
            logger.info(f"{handler_name}: Processing message operation")
            
            if update.callback_query:
                logger.debug(f"{handler_name}: Editing message via callback")
                await update.callback_query.edit_message_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                logger.debug(f"{handler_name}: Sending new message")
                await update.effective_message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                
            logger.info(f"{handler_name}: Message operation completed successfully")
            
        except Exception as e:
            logger.error(f"{handler_name}: Error in message operation: {str(e)}")
            try:
                # Try to send a new message if edit fails
                logger.info(f"{handler_name}: Attempting fallback message send")
                await update.effective_message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as e2:
                logger.error(f"{handler_name}: Fallback message also failed: {str(e2)}")
                # If both attempts fail, try to send a simple error message
                try:
                    await update.effective_message.reply_text(
                        "Sorry, something went wrong. Please try again."
                    )
                except:
                    logger.critical(f"{handler_name}: All message attempts failed")

    async def _handle_error(self, update: Update, error_message: str = None) -> None:
        """Standardized error handling."""
        if error_message is None:
            error_message = "Sorry, something went wrong. Please try again."
            
        await self._send_or_edit_message(
            update,
            error_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data=f"{self.__class__.__name__.lower()}_menu")
            ]])
        ) 