from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from typing import Dict, Any
import os
import logging
from datetime import datetime

from .team_management import TeamManager, PaymentRequest, PaymentMethod, PaymentStatus
from .onboarding import OnboardingWizard

class ArtistManagerBot:
    def __init__(self):
        self.team_manager = TeamManager(
            coinbase_api_key=os.getenv("COINBASE_API_KEY"),
            coinbase_api_secret=os.getenv("COINBASE_API_SECRET")
        )
        self.onboarding = OnboardingWizard(self)
        
    async def setup_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Configure payment preferences."""
        keyboard = [
            [
                InlineKeyboardButton("Crypto (Coinbase)", callback_data="payment_crypto"),
                InlineKeyboardButton("Bank Transfer", callback_data="payment_bank"),
                InlineKeyboardButton("Credit Card", callback_data="payment_card")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Choose your preferred payment method:",
            reply_markup=reply_markup
        )

    async def handle_payment_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle payment method selection."""
        query = update.callback_query
        await query.answer()
        
        method = query.data.replace("payment_", "").upper()
        context.user_data["payment_method"] = PaymentMethod[method]
        
        if method == "CRYPTO":
            await query.edit_message_text(
                "Crypto payments enabled via Coinbase! You can now create payment requests."
            )
        else:
            await query.edit_message_text(
                f"{method.title()} payments enabled! You can now create payment requests."
            )

    async def request_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Create a new payment request."""
        try:
            # Parse command args: /request_payment amount currency description
            args = context.args
            if len(args) < 3:
                await update.message.reply_text(
                    "Usage: /request_payment <amount> <currency> <description>"
                )
                return
                
            amount = float(args[0])
            currency = args[1].upper()
            description = " ".join(args[2:])
            
            payment_method = context.user_data.get("payment_method", PaymentMethod.BANK_TRANSFER)
            
            request = PaymentRequest(
                collaborator_id=str(update.effective_user.id),
                amount=amount,
                currency=currency,
                description=description,
                due_date=datetime.now(),  # You may want to make this configurable
                payment_method=payment_method
            )
            
            result = await self.team_manager.create_payment_request(request)
            
            if result.get("payment_url"):
                await update.message.reply_text(
                    f"Payment request created!\nAmount: {amount} {currency}\n"
                    f"Description: {description}\nPayment URL: {result['payment_url']}"
                )
            else:
                await update.message.reply_text(
                    f"Payment request created!\nAmount: {amount} {currency}\n"
                    f"Description: {description}\nStatus: {result['status']}"
                )
                
        except ValueError:
            await update.message.reply_text("Invalid amount format. Please use numbers only.")
        except Exception as e:
            await update.message.reply_text(f"Error creating payment request: {str(e)}")

    async def check_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check status of a payment."""
        if not context.args:
            await update.message.reply_text("Usage: /check_payment <payment_id>")
            return
            
        payment_id = context.args[0]
        try:
            status = await self.team_manager.check_payment_status(payment_id)
            await update.message.reply_text(
                f"Payment Status:\n"
                f"Status: {status['status']}\n"
                f"Paid: {'Yes' if status.get('paid') else 'No'}\n"
                f"Amount Paid: {status.get('amount_paid', 0)} {status.get('currency', '')}"
            )
        except Exception as e:
            await update.message.reply_text(f"Error checking payment status: {str(e)}")

    async def list_payments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List all payment requests."""
        payments = self.team_manager.payments.values()
        if not payments:
            await update.message.reply_text("No payment requests found.")
            return
            
        response = "Payment Requests:\n\n"
        for payment in payments:
            response += (
                f"ID: {payment.id}\n"
                f"Amount: {payment.amount} {payment.currency}\n"
                f"Status: {payment.status}\n"
                f"Description: {payment.description}\n"
                f"Created: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{'Payment URL: ' + payment.invoice_link if payment.invoice_link else ''}\n\n"
            )
            
        await update.message.reply_text(response)

    def register_handlers(self, application: Application) -> None:
        """Register command handlers."""
        # Existing handlers...
        
        # Payment handlers
        application.add_handler(CommandHandler("setup_payment", self.setup_payment))
        application.add_handler(CallbackQueryHandler(self.handle_payment_method, pattern="^payment_"))
        application.add_handler(CommandHandler("request_payment", self.request_payment))
        application.add_handler(CommandHandler("check_payment", self.check_payment))
        application.add_handler(CommandHandler("list_payments", self.list_payments)) 