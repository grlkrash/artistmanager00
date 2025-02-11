"""Handler for name change functionality."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters
)

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
NAME_INPUT = 1

async def start_name_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the name change process."""
    logger.info("Starting name change process")
    
    # Clear any existing state
    context.user_data.pop('name_change_state', None)
    
    # Get current name from context or use default
    current_name = context.bot_data.get('manager_name', 'Kennedy Young')
    
    # Store current name in conversation state
    context.user_data['name_change_state'] = {
        'current_name': current_name,
        'step': 'awaiting_choice'
    }
    
    # Send message with inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("Keep Current Name", callback_data="name_keep"),
            InlineKeyboardButton("Enter New Name", callback_data="name_change")
        ]
    ]
    
    if update.message:
        await update.message.reply_text(
            f"I'm currently set as {current_name}. Would you like me to use a different name?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.callback_query.message.reply_text(
            f"I'm currently set as {current_name}. Would you like me to use a different name?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return NAME_INPUT

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the name input from user."""
    if 'name_change_state' not in context.user_data:
        await update.message.reply_text(
            "Sorry, something went wrong. Please try the name change process again."
        )
        return ConversationHandler.END
        
    user_input = update.message.text.strip()
    
    if user_input.lower() == 'keep':
        current_name = context.user_data['name_change_state']['current_name']
        await update.message.reply_text(
            f"Alright, I'll keep my name as {current_name}. What would you like to do next?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
            ])
        )
        # Clear state
        context.user_data.pop('name_change_state', None)
        return ConversationHandler.END
        
    # Update the name
    context.bot_data['manager_name'] = user_input
    
    # Clear state
    context.user_data.pop('name_change_state', None)
    
    # Confirm the change
    await update.message.reply_text(
        f"Perfect! I'll now go by {user_input}. What would you like to do next?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ])
    )
    
    return ConversationHandler.END

async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button callbacks for name change."""
    query = update.callback_query
    await query.answer()
    
    if 'name_change_state' not in context.user_data:
        await query.message.reply_text(
            "Sorry, something went wrong. Please try the name change process again."
        )
        return ConversationHandler.END
        
    if query.data == "name_keep":
        current_name = context.user_data['name_change_state']['current_name']
        # Clear state
        context.user_data.pop('name_change_state', None)
        
        await query.message.edit_text(
            f"Alright, I'll keep my name as {current_name}. What would you like to do next?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
            ])
        )
        return ConversationHandler.END
        
    elif query.data == "name_change":
        await query.message.edit_text(
            "Please type the new name you'd like me to use:",
            reply_markup=None
        )
        context.user_data['name_change_state']['step'] = 'awaiting_input'
        return NAME_INPUT
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the name change process."""
    # Clear state
    context.user_data.pop('name_change_state', None)
    
    await update.message.reply_text(
        "Name change cancelled. What would you like to do next?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ])
    )
    return ConversationHandler.END

def get_name_change_handler() -> ConversationHandler:
    """Create and return the name change conversation handler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler('change_name', start_name_change),
            CallbackQueryHandler(start_name_change, pattern="^change_manager_name$")
        ],
        states={
            NAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input),
                CallbackQueryHandler(handle_button_callback, pattern="^name_(keep|change)$")
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$")
        ],
        name="name_change_conversation",
        persistent=True
    ) 