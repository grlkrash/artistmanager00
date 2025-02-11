"""Handler for name change functionality."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from ..states import NameChangeStates
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
NAME_INPUT = 1

async def start_name_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the name change process."""
    logger.info("Starting name change process")
    
    # Get current name from context or use default
    current_name = context.bot_data.get('manager_name', 'Kennedy Young')
    
    # Store current name in conversation state
    context.user_data['current_name'] = current_name
    
    # Send message with inline keyboard
    await update.message.reply_text(
        f"Great! I'm currently set as {current_name}. Would you like me to use a different name?\n\n"
        "Just type a new name, or say 'keep' if you're happy with this one.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Keep Current Name", callback_data="keep_name")],
            [InlineKeyboardButton("Enter New Name", callback_data="new_name")]
        ])
    )
    
    return NAME_INPUT

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the name input from user."""
    user_input = update.message.text.strip()
    
    if user_input.lower() == 'keep':
        current_name = context.user_data.get('current_name', 'Kennedy Young')
        await update.message.reply_text(
            f"Alright, I'll keep my name as {current_name}. What would you like to do next?"
        )
        return ConversationHandler.END
        
    # Update the name
    context.bot_data['manager_name'] = user_input
    
    # Confirm the change
    await update.message.reply_text(
        f"Perfect! I'll now go by {user_input}. What would you like to do next?"
    )
    
    return ConversationHandler.END

async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button callbacks for name change."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "keep_name":
        current_name = context.user_data.get('current_name', 'Kennedy Young')
        await query.message.reply_text(
            f"Alright, I'll keep my name as {current_name}. What would you like to do next?"
        )
        return ConversationHandler.END
        
    elif query.data == "new_name":
        await query.message.reply_text(
            "Please type the new name you'd like me to use."
        )
        return NAME_INPUT
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the name change process."""
    await update.message.reply_text(
        "Name change cancelled. What would you like to do next?"
    )
    return ConversationHandler.END

def get_name_change_handler() -> ConversationHandler:
    """Create and return the name change conversation handler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler('change_name', start_name_change),
            MessageHandler(filters.Regex(r'^Change Manager Name$'), start_name_change)
        ],
        states={
            NAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input),
                CallbackQueryHandler(handle_button_callback)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="name_change_conversation",
        persistent=True
    ) 