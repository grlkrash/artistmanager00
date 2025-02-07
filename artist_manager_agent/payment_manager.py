from typing import Optional, Dict, List, Union, Any
from datetime import datetime
import uuid
from enum import Enum
from pydantic import BaseModel

class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentMethod(str, Enum):
    """Payment methods."""
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"

class PaymentRequest(BaseModel):
    """Payment request model."""
    id: str = str(uuid.uuid4())
    collaborator_id: str
    amount: float
    currency: str = "USD"
    description: str
    due_date: Optional[datetime] = None
    payment_method: Optional[PaymentMethod] = None
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = datetime.now()
    paid_at: Optional[datetime] = None
    invoice_link: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None

class FinancialAccount:
    """Financial account information."""
    pass

class EnhancedTransaction:
    """Enhanced transaction information."""
    pass

class BudgetTracking:
    """Budget tracking information."""
    pass

class PaymentManager:
    def __init__(self, payments_dict: Optional[Dict[str, PaymentRequest]] = None):
        """Initialize the payment manager.
        
        Args:
            payments_dict: Optional dictionary to use for storing payments.
                         If provided, this will be used instead of creating a new one.
        """
        # Use provided dictionary or create new one
        self.payments = payments_dict if payments_dict is not None else {}
        
        # Initialize other attributes
        self.accounts: Dict[str, FinancialAccount] = {}
        self.transactions: Dict[str, EnhancedTransaction] = {}
        self.budgets: Dict[str, BudgetTracking] = {}

    async def generate_receipt(self, payment_id: str) -> Optional[str]:
        """Generate a receipt for a payment.

        Args:
            payment_id (str): The ID of the payment to generate a receipt for.

        Returns:
            Optional[str]: The formatted receipt, or None if the payment is not found.
        """
        payment = self.payments.get(payment_id)
        if not payment:
            return None

        # Generate receipt for any payment regardless of status
        receipt_template = f"""Receipt #{payment_id}
Amount: {int(payment.amount) if payment.amount.is_integer() else payment.amount} {payment.currency}
Description: {payment.description}
Status: {payment.status.value.upper()}
Payment Method: {payment.payment_method.value.upper() if payment.payment_method else 'N/A'}
Date: {payment.paid_at.strftime('%Y-%m-%d %H:%M:%S') if payment.paid_at else 'Not paid yet'}
"""
        return receipt_template

    async def send_payment_reminder(self, payment_id: str) -> bool:
        """Send a reminder for a payment.

        Args:
            payment_id (str): The ID of the payment to send a reminder for.

        Returns:
            bool: True if the reminder was sent successfully, False otherwise.
        """
        payment = self.payments.get(payment_id)
        if not payment:
            return False

        # Only send reminders for payments that aren't paid or cancelled
        if payment.status not in [PaymentStatus.PAID, PaymentStatus.CANCELLED]:
            # Format the reminder message
            amount_str = f"{payment.amount:.2f} {payment.currency}"
            reminder_message = f"Payment Reminder: {amount_str}\nDescription: {payment.description}"

            # In a real implementation, this would send an email or notification
            # For now, we'll just update the payment notes
            timestamp = datetime.now()
            if payment.notes:
                payment.notes += f"\nReminder sent at {timestamp}"
            else:
                payment.notes = f"Reminder sent at {timestamp}"

            return True

        return False

    async def process_batch_payments(self, payment_ids: List[str]) -> Dict[str, List[Union[str, Dict[str, Any]]]]:
        """Process a batch of payments.

        Args:
            payment_ids (List[str]): List of payment IDs to process.

        Returns:
            Dict[str, List[Union[str, Dict[str, Any]]]]: Dictionary containing successful, failed, and skipped payments.
        """
        results = {
            "successful": [],
            "failed": [],
            "skipped": []
        }

        for payment_id in payment_ids:
            payment = self.payments.get(payment_id)
            if not payment:
                results["skipped"].append(payment_id)
                continue

            if payment.status in [PaymentStatus.PAID, PaymentStatus.CANCELLED]:
                results["skipped"].append(payment_id)
                continue

            try:
                # Process the payment
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.now()
                transaction_id = str(uuid.uuid4())

                # Add to successful payments with details
                results["successful"].append({
                    "payment_id": payment_id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "transaction_id": transaction_id
                })

            except Exception as e:
                payment.status = PaymentStatus.FAILED
                results["failed"].append(payment_id)

        return results

    async def get_payment_analytics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get analytics for payments within a date range.

        Args:
            start_date (Optional[datetime]): Start date for analytics.
            end_date (Optional[datetime]): End date for analytics.

        Returns:
            Dict[str, Any]: Dictionary containing various payment analytics.
        """
        analytics = {
            "total_volume": 0.0,
            "successful_payments": 0,
            "failed_payments": 0,
            "pending_payments": 0,
            "average_amount": 0.0,
            "by_payment_method": {},
            "by_currency": {},
            "daily_volume": {},
            "average_processing_time": 0.0
        }

        total_amount = 0.0
        payment_count = 0
        processing_times = []

        for payment in self.payments.values():
            # Check if payment is within the date range
            if start_date and payment.created_at < start_date:
                continue
            if end_date and payment.created_at > end_date:
                continue

            # Include all payments in total volume
            total_amount += payment.amount
            payment_count += 1

            # Update payment status counts
            if payment.status == PaymentStatus.PAID:
                analytics["successful_payments"] += 1
                if payment.paid_at and payment.created_at:
                    processing_time = (payment.paid_at - payment.created_at).total_seconds()
                    processing_times.append(processing_time)
            elif payment.status == PaymentStatus.FAILED:
                analytics["failed_payments"] += 1
            elif payment.status == PaymentStatus.PENDING:
                analytics["pending_payments"] += 1

            # Update payment method statistics
            if payment.payment_method:
                method = payment.payment_method.value
                analytics["by_payment_method"][method] = analytics["by_payment_method"].get(method, 0) + 1

            # Update currency statistics
            analytics["by_currency"][payment.currency] = analytics["by_currency"].get(payment.currency, 0) + 1

            # Update daily volume
            date_str = payment.created_at.strftime('%Y-%m-%d')
            analytics["daily_volume"][date_str] = analytics["daily_volume"].get(date_str, 0.0) + payment.amount

        # Calculate final statistics
        analytics["total_volume"] = total_amount
        if payment_count > 0:
            analytics["average_amount"] = total_amount / payment_count
        if processing_times:
            analytics["average_processing_time"] = sum(processing_times) / len(processing_times)

        return analytics 