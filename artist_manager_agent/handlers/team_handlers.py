"""Team management handlers for the Artist Manager Bot."""
from datetime import datetime
import uuid
import logging
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, ForceReply
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    BaseHandler
)
from ..models import CollaboratorProfile, PaymentRequest
from .base_handler import BaseHandlerMixin

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_MEMBER_NAME = "AWAITING_MEMBER_NAME"
AWAITING_MEMBER_ROLE = "AWAITING_MEMBER_ROLE"
AWAITING_MEMBER_EMAIL = "AWAITING_MEMBER_EMAIL"
AWAITING_MEMBER_RATE = "AWAITING_MEMBER_RATE"
AWAITING_MEMBER_SKILLS = "AWAITING_MEMBER_SKILLS"
AWAITING_PAYMENT_AMOUNT = "AWAITING_PAYMENT_AMOUNT"
AWAITING_PAYMENT_DESCRIPTION = "AWAITING_PAYMENT_DESCRIPTION"

class TeamHandlers(BaseHandlerMixin):
    """Team management handlers."""
    
    group = "team"  # Handler group for registration
    
    def __init__(self, bot):
        self.bot = bot

    def get_handlers(self) -> List[BaseHandler]:
        """Get team-related handlers."""
        return [
            CommandHandler("team", self.show_team),
            CommandHandler("addmember", self.start_member_addition),
            CommandHandler("payments", self.show_payments),
            self.get_conversation_handler(),
            CallbackQueryHandler(self.handle_team_callback, pattern="^team_")
        ]

    def get_conversation_handler(self) -> ConversationHandler:
        """Get the conversation handler for team management."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_member_addition, pattern="^team_add$"),
                CommandHandler("addmember", self.start_member_addition)
            ],
            states={
                AWAITING_MEMBER_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_member_name)
                ],
                AWAITING_MEMBER_ROLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_member_role)
                ],
                AWAITING_MEMBER_EMAIL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_member_email)
                ],
                AWAITING_MEMBER_RATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_member_rate)
                ],
                AWAITING_MEMBER_SKILLS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_member_skills)
                ],
                AWAITING_PAYMENT_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_payment_amount)
                ],
                AWAITING_PAYMENT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_payment_description)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_team_action)
            ],
            name="team_management",
            persistent=True
        )

    async def show_team(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all team members."""
        try:
            user_id = update.effective_user.id
            profile = self.bot.profiles.get(user_id)
            
            if not profile:
                await update.message.reply_text(
                    "Please complete your profile setup first using /me"
                )
                return

            # Get all team members
            team_members = list(self.bot.team_manager.collaborators.values())
            
            if not team_members:
                keyboard = [[InlineKeyboardButton("Add Team Member", callback_data="team_add")]]
                await update.message.reply_text(
                    "No team members found. Would you like to add one?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            # Create team list with buttons
            message = "👥 Your Team:\n\n"
            keyboard = []
            
            for member in team_members:
                message += (
                    f"👤 {member.name}\n"
                    f"Role: {member.role}\n"
                    f"Rate: ${member.rate}/hr\n"
                    f"Skills: {', '.join(member.skills)}\n\n"
                )
                
                keyboard.append([
                    InlineKeyboardButton(f"Manage {member.name}", callback_data=f"team_manage_{member.id}")
                ])

            keyboard.append([InlineKeyboardButton("➕ Add Team Member", callback_data="team_add")])
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
                
        except Exception as e:
            logger.error(f"Error showing team: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error loading your team. Please try again."
            )

    async def start_member_addition(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start team member addition flow."""
        try:
            await update.message.reply_text(
                "Let's add a new team member!\n\n"
                "What's their name?",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_MEMBER_NAME
            
        except Exception as e:
            logger.error(f"Error starting member addition: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error starting member addition. Please try again."
            )
            return ConversationHandler.END

    async def handle_member_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle team member name input."""
        name = update.message.text.strip()
        context.user_data["member_name"] = name
        
        # Create keyboard for common roles
        keyboard = [
            ["Producer", "Engineer", "Manager"],
            ["Musician", "Designer", "Marketer"],
            ["Other (type custom role)"]
        ]
        
        await update.message.reply_text(
            f"Great! What's {name}'s role in the team?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return AWAITING_MEMBER_ROLE

    async def handle_member_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle team member role input."""
        role = update.message.text.strip()
        context.user_data["member_role"] = role
        
        await update.message.reply_text(
            "What's their email address?",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_MEMBER_EMAIL

    async def handle_member_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle team member email input."""
        email = update.message.text.strip()
        context.user_data["member_email"] = email
        
        await update.message.reply_text(
            "What's their hourly rate? (Enter a number in USD)",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_MEMBER_RATE

    async def handle_member_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle team member rate input."""
        try:
            rate = float(update.message.text.strip().replace("$", "").replace(",", ""))
            context.user_data["member_rate"] = rate
            
            await update.message.reply_text(
                "What are their skills? List them one per line or separate with commas.",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_MEMBER_SKILLS
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for the rate (e.g. 50):"
            )
            return AWAITING_MEMBER_RATE

    async def handle_member_skills(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle team member skills input."""
        skills = [s.strip() for s in update.message.text.split(",")]
        
        # Create the team member
        member_id = str(uuid.uuid4())
        member = CollaboratorProfile(
            id=member_id,
            name=context.user_data["member_name"],
            role=context.user_data["member_role"],
            email=context.user_data["member_email"],
            rate=context.user_data["member_rate"],
            skills=skills,
            joined_date=datetime.now()
        )
        
        # Add to team
        success = await self.bot.team_manager.add_collaborator(member)
        
        if not success:
            await update.message.reply_text(
                "Sorry, there was an error adding the team member. Please try again."
            )
            return ConversationHandler.END
            
        # Clear conversation data
        context.user_data.clear()
        
        # Show success message
        keyboard = [
            [
                InlineKeyboardButton("Add Another Member", callback_data="team_add"),
                InlineKeyboardButton("View Team", callback_data="team_view")
            ]
        ]
        
        await update.message.reply_text(
            f"✨ Team member '{member.name}' added successfully!\n\n"
            f"Role: {member.role}\n"
            f"Rate: ${member.rate}/hr\n"
            f"Skills: {', '.join(member.skills)}\n\n"
            "What would you like to do next?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    async def show_payments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show payment requests and history."""
        try:
            # Get all payment requests
            payment_requests = await self.bot.team_manager.get_payment_requests()
            
            if not payment_requests:
                message = "No payment requests found."
                keyboard = [[InlineKeyboardButton("Create Payment Request", callback_data="team_payment_create")]]
            else:
                message = "💰 Payment Requests:\n\n"
                keyboard = []
                
                for request in payment_requests:
                    status_emoji = {
                        "pending": "⏳",
                        "approved": "✅",
                        "rejected": "❌",
                        "paid": "💸"
                    }.get(request.status, "❓")
                    
                    message += (
                        f"{status_emoji} Amount: ${request.amount:,.2f}\n"
                        f"For: {request.description}\n"
                        f"Status: {request.status.title()}\n"
                        f"Requested: {request.created_at.strftime('%Y-%m-%d')}\n\n"
                    )
                    
                    if request.status == "pending":
                        keyboard.append([
                            InlineKeyboardButton(
                                f"Review {request.description[:20]}...",
                                callback_data=f"team_payment_review_{request.id}"
                            )
                        ])
                        
                keyboard.append([InlineKeyboardButton("Create Payment Request", callback_data="team_payment_create")])
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing payments: {str(e)}")
            await update.message.reply_text(
                "Sorry, there was an error loading payments. Please try again."
            )

    async def handle_team_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle team-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("team_", "")
        
        if action == "add":
            await self.start_member_addition(update, context)
            
        elif action == "view":
            await self.show_team(update, context)
            
        elif action.startswith("manage_"):
            member_id = action.replace("manage_", "")
            await self._show_member_management(update, context, member_id)
            
        elif action.startswith("payment_"):
            payment_action = action.replace("payment_", "")
            if payment_action == "create":
                await self._start_payment_request(update, context)
            elif payment_action.startswith("review_"):
                payment_id = payment_action.replace("review_", "")
                await self._review_payment_request(update, context, payment_id)

    async def _show_member_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, member_id: str) -> None:
        """Show member management options."""
        try:
            member = await self.bot.team_manager.get_collaborator(member_id)
            if not member:
                await update.callback_query.edit_message_text(
                    "Team member not found. They may have been removed."
                )
                return
                
            message = (
                f"👤 {member.name}\n\n"
                f"Role: {member.role}\n"
                f"Email: {member.email}\n"
                f"Rate: ${member.rate}/hr\n"
                f"Skills: {', '.join(member.skills)}\n"
                f"Joined: {member.joined_date.strftime('%Y-%m-%d')}\n"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("Edit Details", callback_data=f"team_edit_{member_id}"),
                    InlineKeyboardButton("Remove Member", callback_data=f"team_remove_{member_id}")
                ],
                [
                    InlineKeyboardButton("Create Payment", callback_data=f"team_payment_create_{member_id}"),
                    InlineKeyboardButton("View History", callback_data=f"team_history_{member_id}")
                ],
                [InlineKeyboardButton("Back to Team", callback_data="team_view")]
            ]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing member management: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error loading the team member. Please try again."
            )

    async def _start_payment_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Start payment request creation."""
        await update.callback_query.edit_message_text(
            "How much is this payment request for? (Enter amount in USD)",
            reply_markup=ForceReply(selective=True)
        )
        return AWAITING_PAYMENT_AMOUNT

    async def _review_payment_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str) -> None:
        """Review a payment request."""
        try:
            # Get the payment request
            payment_requests = await self.bot.team_manager.get_payment_requests()
            payment = next((p for p in payment_requests if p.id == payment_id), None)
            
            if not payment:
                await update.callback_query.edit_message_text(
                    "Payment request not found. It may have been processed already."
                )
                return
                
            message = (
                f"💰 Payment Request Review\n\n"
                f"Amount: ${payment.amount:,.2f}\n"
                f"Description: {payment.description}\n"
                f"Requested by: {payment.collaborator_id}\n"
                f"Date: {payment.created_at.strftime('%Y-%m-%d')}\n"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("Approve", callback_data=f"team_payment_approve_{payment_id}"),
                    InlineKeyboardButton("Reject", callback_data=f"team_payment_reject_{payment_id}")
                ],
                [InlineKeyboardButton("Back to Payments", callback_data="team_payments")]
            ]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error reviewing payment: {str(e)}")
            await update.callback_query.edit_message_text(
                "Sorry, there was an error reviewing the payment. Please try again."
            )

    async def cancel_team_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel team action."""
        context.user_data.clear()
        await update.message.reply_text(
            "Action cancelled. You can use /team to view your team or /addmember to add a new member."
        )
        return ConversationHandler.END 