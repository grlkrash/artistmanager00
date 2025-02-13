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
from .base_handler import BaseBotHandler
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
AWAITING_MEMBER_NAME = "AWAITING_MEMBER_NAME"
AWAITING_MEMBER_ROLE = "AWAITING_MEMBER_ROLE"
AWAITING_MEMBER_EMAIL = "AWAITING_MEMBER_EMAIL"
AWAITING_MEMBER_RATE = "AWAITING_MEMBER_RATE"
AWAITING_MEMBER_SKILLS = "AWAITING_MEMBER_SKILLS"
AWAITING_PAYMENT_AMOUNT = "AWAITING_PAYMENT_AMOUNT"
AWAITING_PAYMENT_DESCRIPTION = "AWAITING_PAYMENT_DESCRIPTION"

class TeamHandlers(BaseBotHandler):
    """Handlers for team-related functionality."""
    
    def __init__(self, bot):
        """Initialize team handlers."""
        super().__init__(bot)
        self.group = 8  # Set handler group

    def get_handlers(self) -> List[BaseHandler]:
        """Get team-related handlers."""
        return [
            CommandHandler("team", self.show_menu),
            CallbackQueryHandler(self.handle_callback, pattern="^(menu_team|team_.*|team_menu)$")
        ]

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle team-related callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Handle both team_ and menu_team patterns
            action = query.data.replace("menu_team", "menu").replace("team_", "").strip("_")
            logger.info(f"Team handler processing callback: {query.data} -> {action}")
            
            if action == "menu" or action == "":
                await self.show_menu(update, context)
            elif action == "add":
                await self._show_add_member(update, context)
            elif action == "view_all":
                await self._show_all_members(update, context)
            elif action == "analytics":
                await self._show_team_analytics(update, context)
            elif action == "roles":
                await self._show_role_management(update, context)
            elif action.startswith("manage_"):
                member_id = action.replace("manage_", "")
                await self._show_member_management(update, context, member_id)
            else:
                logger.warning(f"Unknown team action: {action}")
                await self.show_menu(update, context)
                
        except Exception as e:
            logger.error(f"Error in team callback handler: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                update,
                "Sorry, something went wrong. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="team_menu")
                ]])
            )

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the team menu."""
        keyboard = [
            [
                InlineKeyboardButton("Add Member", callback_data="team_add"),
                InlineKeyboardButton("View Team", callback_data="team_view_all")
            ],
            [
                InlineKeyboardButton("Team Analytics", callback_data="team_analytics"),
                InlineKeyboardButton("Manage Roles", callback_data="team_roles")
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="menu_main")]
        ]
        
        await self._send_or_edit_message(
            update,
            "👥 *Team Management*\n\n"
            "What would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def _show_add_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show member addition interface."""
        keyboard = [
            [
                InlineKeyboardButton("Producer", callback_data="team_role_producer"),
                InlineKeyboardButton("Engineer", callback_data="team_role_engineer")
            ],
            [
                InlineKeyboardButton("Manager", callback_data="team_role_manager"),
                InlineKeyboardButton("Custom Role", callback_data="team_role_custom")
            ],
            [InlineKeyboardButton("« Back", callback_data="team_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "What role would you like to add to your team?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_all_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all team members."""
        # Get team members
        members = await self.bot.team_manager.get_team_members()
        
        if not members:
            keyboard = [
                [InlineKeyboardButton("Add Member", callback_data="team_add")],
                [InlineKeyboardButton("« Back", callback_data="team_menu")]
            ]
            await self._send_or_edit_message(
                update,
                "Your team is empty. Would you like to add a member?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        # Format team message
        message = "👥 Your Team:\n\n"
        keyboard = []
        
        for member in members:
            message += f"👤 {member.name}\n"
            message += f"Role: {member.role}\n"
            message += f"Rate: ${member.rate}/hr\n"
            message += f"Skills: {', '.join(member.skills)}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"Manage: {member.name[:20]}...", callback_data=f"team_manage_{member.id}")
            ])
            
        keyboard.append([InlineKeyboardButton("« Back", callback_data="team_menu")])
        
        await self._send_or_edit_message(
            update,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_team_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show team analytics."""
        try:
            analytics = await self.bot.team_manager.get_team_analytics()
            
            message = (
                "📊 *Team Analytics*\n\n"
                f"Total Members: {analytics['total_members']}\n"
                f"Active Projects: {analytics['active_projects']}\n"
                f"Total Hours: {analytics['total_hours']}\n"
                f"Total Cost: ${analytics['total_cost']:,.2f}\n\n"
                "*Team Composition:*\n"
            )
            
            for role, count in analytics['roles'].items():
                message += f"• {role}: {count}\n"
                
            message += "\n*Project Distribution:*\n"
            for project in analytics['project_distribution']:
                message += f"• {project['name']}: {project['members']} members\n"
                
            keyboard = [[InlineKeyboardButton("« Back", callback_data="team_menu")]]
            
            await self._send_or_edit_message(
                update,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error showing team analytics: {str(e)}")
            await self._handle_error(update)

    async def _show_role_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show role management options."""
        keyboard = [
            [
                InlineKeyboardButton("Add Role", callback_data="team_role_add"),
                InlineKeyboardButton("Edit Roles", callback_data="team_role_edit")
            ],
            [
                InlineKeyboardButton("Role Analytics", callback_data="team_role_analytics"),
                InlineKeyboardButton("Role Permissions", callback_data="team_role_permissions")
            ],
            [InlineKeyboardButton("« Back", callback_data="team_menu")]
        ]
        
        await self._send_or_edit_message(
            update,
            "Manage team roles and permissions:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_member_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, member_id: str) -> None:
        """Show management options for a specific team member."""
        try:
            member = await self.bot.team_manager.get_team_member(member_id)
            if not member:
                await self._send_or_edit_message(
                    update,
                    "Team member not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="team_menu")
                    ]])
                )
                return
                
            # Format member details
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
                    InlineKeyboardButton("Edit Details", callback_data=f"team_edit_{member.id}"),
                    InlineKeyboardButton("Change Role", callback_data=f"team_role_{member.id}")
                ],
                [
                    InlineKeyboardButton("Update Rate", callback_data=f"team_rate_{member.id}"),
                    InlineKeyboardButton("View Projects", callback_data=f"team_projects_{member.id}")
                ],
                [
                    InlineKeyboardButton("Remove Member", callback_data=f"team_remove_{member.id}"),
                    InlineKeyboardButton("View Analytics", callback_data=f"team_member_analytics_{member.id}")
                ],
                [InlineKeyboardButton("« Back", callback_data="team_menu")]
            ]
            
            await self._send_or_edit_message(
                update,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing member management: {str(e)}")
            await self._handle_error(update)

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

    async def handle_payment_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Handle payment amount input."""
        try:
            amount = float(update.message.text.strip().replace("$", "").replace(",", ""))
            
            if not context.user_data.get('temp_payment'):
                context.user_data['temp_payment'] = {}
                
            context.user_data['temp_payment']['amount'] = amount
            
            await update.message.reply_text(
                "Please provide a description for this payment:",
                reply_markup=ForceReply(selective=True)
            )
            return AWAITING_PAYMENT_DESCRIPTION
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid amount (e.g. 1000 or 1000.50):"
            )
            return AWAITING_PAYMENT_AMOUNT
            
    async def handle_payment_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle payment description input."""
        description = update.message.text.strip()
        
        if not context.user_data.get('temp_payment'):
            context.user_data['temp_payment'] = {}
            
        context.user_data['temp_payment']['description'] = description
        
        # Create payment request
        payment_data = context.user_data['temp_payment']
        payment_request = PaymentRequest(
            id=str(uuid.uuid4()),
            amount=payment_data['amount'],
            description=payment_data['description'],
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save payment request
        self.bot.team_manager.add_payment_request(payment_request)
        
        # Clear temporary data
        context.user_data.pop('temp_payment', None)
        
        # Show confirmation
        await update.message.reply_text(
            f"✅ Payment request for ${payment_request.amount:,.2f} has been created.\n\n"
            f"Description: {payment_request.description}\n"
            f"Status: {payment_request.status.title()}\n\n"
            "Use /payments to view and manage payments.",
            parse_mode="Markdown"
        )
        
        return ConversationHandler.END 