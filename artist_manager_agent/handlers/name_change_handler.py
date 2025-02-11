"""Name change handlers for the Artist Manager Bot."""
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    BaseHandler
)
from .base_handler import BaseBotHandler

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
NAME_INPUT = 1
NAME_CONFIRM = 2

class NameChangeHandlers(BaseBotHandler):
    """Handlers for name change functionality."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.group = 10  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get name change-related handlers."""
        return [
            self.get_conversation_handler()
        ]

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for name changes."""
        return ConversationHandler(
            entry_points=[
                CommandHandler('change_name', self.start_name_change),
                CallbackQueryHandler(self.start_name_change, pattern="^change_manager_name$")
            ],
            states={
                NAME_INPUT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_name_input),
                    CallbackQueryHandler(self.handle_button_callback, pattern="^name_(keep|change|cancel)$")
                ],
                NAME_CONFIRM: [
                    CallbackQueryHandler(self.handle_button_callback, pattern="^name_(confirm|change|cancel)$")
                ]
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^cancel$")
            ],
            name="name_change_conversation",
            persistent=True
        )

    async def start_name_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the name change process."""
        logger.info("Starting name change process")
        
        # Clear any existing state
        context.user_data.pop('name_change_state', None)
        
        # Get current name from context or use default
        current_name = context.bot_data.get('manager_name', 'Kennedy Young')
        
        # Store current name in conversation state
        context.user_data['name_change_state'] = {
            'current_name': current_name,
            'step': 'awaiting_input'
        }
        
        # Create keyboard with options
        keyboard = [
            [InlineKeyboardButton("Keep Current Name", callback_data="name_keep")],
            [InlineKeyboardButton("Change Name", callback_data="name_change")]
        ]
        
        # Send message with buttons only - no redundant text question
        message = f"I'm currently set as {current_name}."
        
        await self._send_or_edit_message(
            update,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return NAME_INPUT

    async def handle_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the name input from user."""
        if 'name_change_state' not in context.user_data:
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try the name change process again."
            )
            return ConversationHandler.END
            
        user_input = update.message.text.strip()
        
        # Store the proposed name for confirmation
        context.user_data['name_change_state']['proposed_name'] = user_input
        
        # Ask for confirmation with simple buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="name_confirm"),
                InlineKeyboardButton("🔄 Try Again", callback_data="name_change")
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="name_cancel")]
        ]
        
        await self._send_or_edit_message(
            update,
            f"Change name to: {user_input}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return NAME_CONFIRM

    async def handle_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle button callbacks for name change."""
        query = update.callback_query
        await query.answer()
        
        if 'name_change_state' not in context.user_data:
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try the name change process again."
            )
            return ConversationHandler.END
            
        if query.data == "name_keep":
            current_name = context.user_data['name_change_state']['current_name']
            # Clear state
            context.user_data.pop('name_change_state', None)
            
            await self._send_or_edit_message(
                update,
                f"I'll keep my name as {current_name}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
                ])
            )
            return ConversationHandler.END
            
        elif query.data == "name_change":
            await self._send_or_edit_message(
                update,
                "What name would you like me to use?",
                reply_markup=None
            )
            context.user_data['name_change_state']['step'] = 'awaiting_input'
            return NAME_INPUT
            
        elif query.data == "name_confirm":
            new_name = context.user_data['name_change_state']['proposed_name']
            # Update the name
            context.bot_data['manager_name'] = new_name
            # Clear state
            context.user_data.pop('name_change_state', None)
            
            await self._send_or_edit_message(
                update,
                f"Perfect! I'll now go by {new_name}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
                ])
            )
            return ConversationHandler.END
            
        elif query.data == "name_cancel":
            # Clear state
            context.user_data.pop('name_change_state', None)
            
            await self._send_or_edit_message(
                update,
                "Name change cancelled.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
                ])
            )
            return ConversationHandler.END
            
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the name change process."""
        # Clear state
        context.user_data.pop('name_change_state', None)
        
        await self._send_or_edit_message(
            update,
            "Name change cancelled. What would you like to do next?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
            ])
        )
        return ConversationHandler.END 