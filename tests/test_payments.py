import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from telegram import Bot, Update, Message, Chat, User
from telegram.ext import ContextTypes
from artist_manager_agent.agent import (
    ArtistManagerAgent,
    FinancialRecord
)
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.models import (
    PaymentMethod,
    PaymentRequest,
    PaymentStatus,
    ArtistProfile
)

@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=Bot)
    bot.defaults = None
    return bot

@pytest.fixture
def mock_message(mock_bot):
    message = MagicMock(spec=Message)
    message._bot = mock_bot
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 123
    return message

@pytest.fixture
def mock_update(mock_message):
    update = MagicMock(spec=Update)
    update.message = mock_message
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 456
    return update

@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context

@pytest.fixture
def agent():
    return ArtistManagerAgent()

@pytest.fixture
def sample_payment():
    return FinancialRecord(
        record_id="payment_1",
        type="income",
        amount=100.0,
        description="Test payment",
        date=datetime.now(),
        category="service_fee",
        status="pending",
        payment_method="crypto",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.mark.asyncio
async def test_add_payment(agent, sample_payment):
    """Test adding a payment record."""
    await agent.add_financial_record(sample_payment)
    records = await agent.get_financial_records()
    assert len(records) == 1
    assert records[0].record_id == "payment_1"
    assert records[0].amount == 100.0
    assert records[0].status == "pending"

@pytest.mark.asyncio
async def test_update_payment_status(agent, sample_payment):
    """Test updating payment status."""
    await agent.add_financial_record(sample_payment)
    updated_payment = sample_payment.copy()
    updated_payment.status = "completed"
    await agent.update_financial_record(updated_payment)
    records = await agent.get_financial_records()
    assert records[0].status == "completed"

@pytest.mark.asyncio
async def test_get_pending_payments(agent):
    """Test getting pending payments."""
    # Add pending payment
    pending_payment = FinancialRecord(
        record_id="payment_1",
        type="income",
        amount=100.0,
        description="Pending payment",
        date=datetime.now(),
        category="service_fee",
        status="pending",
        payment_method="crypto",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_financial_record(pending_payment)
    
    # Add completed payment
    completed_payment = FinancialRecord(
        record_id="payment_2",
        type="income",
        amount=200.0,
        description="Completed payment",
        date=datetime.now(),
        category="service_fee",
        status="completed",
        payment_method="crypto",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_financial_record(completed_payment)
    
    # Get pending payments
    pending = await agent.get_pending_payments()
    assert len(pending) == 1
    assert pending[0].record_id == "payment_1"
    assert pending[0].status == "pending"

@pytest.mark.asyncio
async def test_get_payment_history(agent):
    """Test getting payment history."""
    # Add multiple payments
    payment1 = FinancialRecord(
        record_id="payment_1",
        type="income",
        amount=100.0,
        description="First payment",
        date=datetime.now() - timedelta(days=1),
        category="service_fee",
        status="completed",
        payment_method="crypto",
        created_at=datetime.now() - timedelta(days=1),
        updated_at=datetime.now() - timedelta(days=1)
    )
    await agent.add_financial_record(payment1)
    
    payment2 = FinancialRecord(
        record_id="payment_2",
        type="income",
        amount=200.0,
        description="Second payment",
        date=datetime.now(),
        category="service_fee",
        status="completed",
        payment_method="crypto",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_financial_record(payment2)
    
    # Get payment history
    history = await agent.get_payment_history()
    assert len(history) == 2
    assert history[0].record_id == "payment_2"  # Most recent first
    assert history[1].record_id == "payment_1"

@pytest.mark.asyncio
async def test_get_payment_summary(agent):
    """Test getting payment summary."""
    # Add income payment
    income = FinancialRecord(
        record_id="payment_1",
        type="income",
        amount=1000.0,
        description="Service fee",
        date=datetime.now(),
        category="service_fee",
        status="completed",
        payment_method="crypto",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_financial_record(income)
    
    # Add expense payment
    expense = FinancialRecord(
        record_id="payment_2",
        type="expense",
        amount=500.0,
        description="Studio time",
        date=datetime.now(),
        category="studio_expenses",
        status="completed",
        payment_method="bank_transfer",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_financial_record(expense)
    
    # Get payment summary
    summary = await agent.get_payment_summary()
    assert summary["total_income"] == 1000.0
    assert summary["total_expenses"] == 500.0
    assert summary["net_income"] == 500.0
    assert summary["by_category"]["service_fee"] == 1000.0
    assert summary["by_category"]["studio_expenses"] == -500.0
    assert summary["by_payment_method"]["crypto"] == 1000.0

async def test_request_payment_success(bot, mock_update, mock_context):
    """Test successful payment request."""
    mock_context.args = ["100", "USD", "Test payment"]
    mock_context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    # Mock successful payment request
    mock_response = {
        "id": "payment123",
        "payment_url": "https://stripe.com/pay/test",
        "status": "pending",
        "expires_at": datetime.now() + timedelta(days=7),
        "payment_method": PaymentMethod.CRYPTO
    }
    bot.team_manager.payment_manager.create_payment_request = AsyncMock(return_value=mock_response)
    
    await bot.request_payment(mock_update, mock_context)
    
    # Verify payment request was created
    bot.team_manager.payment_manager.create_payment_request.assert_called_once_with(
        amount=100.0,
        currency="USD",
        description="Test payment",
        payment_method=PaymentMethod.CRYPTO
    )
    mock_update.message.reply_text.assert_called_with(
        "Payment request created!\nAmount: 100 USD\n"
        "Description: Test payment\nStatus: pending"
    )

@pytest.mark.asyncio
async def test_request_payment_invalid_args(bot, mock_update, mock_context):
    """Test payment request with invalid arguments."""
    mock_context.args = []  # No arguments
    await bot.request_payment(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Usage: /request_payment <amount> <currency> <description>"
    )

@pytest.mark.asyncio
async def test_check_payment_success(bot, mock_update, mock_context):
    """Test successful payment status check."""
    mock_context.args = ["payment123"]
    
    mock_status = {
        "status": "paid",
        "paid": True,
        "amount_paid": 100,
        "currency": "USD"
    }
    bot.team_manager.check_payment_status = AsyncMock(return_value=mock_status)
    
    await bot.check_payment(mock_update, mock_context)
    
    # Verify status was checked
    bot.team_manager.check_payment_status.assert_called_with("payment123")
    mock_update.message.reply_text.assert_called_with(
        "Payment Status:\n"
        "Status: paid\n"
        "Paid: Yes\n"
        "Amount Paid: 100 USD"
    )

@pytest.mark.asyncio
async def test_list_payments_empty(bot, mock_update, mock_context):
    """Test listing payments when none exist."""
    bot.team_manager.payments = {}
    await bot.list_payments(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with("No payment requests found.")

@pytest.mark.asyncio
async def test_list_payments_with_data(bot, mock_update, mock_context):
    """Test listing existing payments."""
    payment = PaymentRequest(
        collaborator_id="123",
        amount=100,
        currency="USD",
        description="Test payment",
        due_date=datetime.now(),
        payment_method=PaymentMethod.CRYPTO,
        status=PaymentStatus.PENDING
    )
    bot.team_manager.payments = {"payment123": payment}
    
    await bot.list_payments(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_request_payment_no_payment_method(bot, mock_update, mock_context):
    """Test payment request without setting payment method."""
    mock_context.args = ["100", "USD", "Test payment"]
    # Don't set payment_method in user_data
    
    await bot.request_payment(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_with(
        "Please set up your payment method first using /setup_payment"
    )

@pytest.mark.asyncio
async def test_request_payment_missing_description(bot, mock_update, mock_context):
    """Test payment request with missing description."""
    mock_context.args = ["100", "USD"]
    mock_context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    await bot.request_payment(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Usage: /request_payment <amount> <currency> <description>"
    )

@pytest.mark.asyncio
async def test_check_payment_no_id(bot, mock_update, mock_context):
    """Test payment status check without payment ID."""
    mock_context.args = []
    await bot.check_payment(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Usage: /check_payment <payment_id>"
    )

@pytest.mark.asyncio
async def test_check_payment_not_found(bot, mock_update, mock_context):
    """Test payment status check for non-existent payment."""
    mock_context.args = ["nonexistent"]
    
    # Mock payment not found
    bot.team_manager.check_payment_status = AsyncMock(
        side_effect=Exception("Payment not found")
    )
    
    await bot.check_payment(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Error checking payment status: Payment not found"
    )

@pytest.mark.asyncio
async def test_request_payment_negative_amount(bot, mock_update, mock_context):
    """Test payment request with negative amount."""
    mock_context.args = ["-100", "USD", "Test payment"]
    mock_context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    await bot.request_payment(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Error creating payment request: Amount must be positive"
    )

@pytest.mark.asyncio
async def test_request_payment_invalid_currency(bot, mock_update, mock_context):
    """Test payment request with invalid currency."""
    mock_context.args = ["100", "INVALID", "Test payment"]
    mock_context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    await bot.request_payment(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Error creating payment request: Invalid currency"
    )

@pytest.mark.asyncio
async def test_generate_receipt(bot, mock_update, mock_context):
    """Test receipt generation for completed payment."""
    # Create a completed payment
    payment = PaymentRequest(
        collaborator_id="123",
        amount=100,
        currency="USD",
        description="Test payment",
        due_date=datetime.now(),
        payment_method=PaymentMethod.CRYPTO,
        status=PaymentStatus.PAID,
        paid_at=datetime.now()
    )
    bot.team_manager.set_payments({"payment123": payment})
    
    receipt = await bot.team_manager.payment_manager.generate_receipt("payment123")
    assert receipt is not None
    assert "Receipt #" in receipt
    assert "100 USD" in receipt
    assert "Test payment" in receipt
    assert "PAID" in receipt
    assert "CRYPTO" in receipt

@pytest.mark.asyncio
async def test_send_payment_reminder(bot, mock_update, mock_context):
    """Test sending payment reminder."""
    # Create a pending payment
    payment = PaymentRequest(
        collaborator_id="123",
        amount=100,
        currency="USD",
        description="Test payment",
        due_date=datetime.now(),
        payment_method=PaymentMethod.CRYPTO,
        status=PaymentStatus.PENDING
    )
    bot.team_manager.set_payments({"payment123": payment})
    
    success = await bot.team_manager.payment_manager.send_payment_reminder("payment123")
    assert success is True

@pytest.mark.asyncio
async def test_process_batch_payments(bot, mock_update, mock_context):
    """Test batch payment processing."""
    # Create multiple payments
    payments = {
        "payment1": PaymentRequest(
            collaborator_id="123",
            amount=100,
            currency="USD",
            description="Test payment 1",
            due_date=datetime.now(),
            payment_method=PaymentMethod.CRYPTO,
            status=PaymentStatus.PENDING
        ),
        "payment2": PaymentRequest(
            collaborator_id="124",
            amount=200,
            currency="USD",
            description="Test payment 2",
            due_date=datetime.now(),
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PENDING
        )
    }
    bot.team_manager.set_payments(payments)
    
    results = await bot.team_manager.payment_manager.process_batch_payments(["payment1", "payment2", "nonexistent"])
    assert len(results["successful"]) > 0
    assert "nonexistent" in results["skipped"]

@pytest.mark.asyncio
async def test_get_payment_analytics(bot, mock_update, mock_context):
    """Test payment analytics generation."""
    # Create payments with different statuses and methods
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    payments = {
        "payment1": PaymentRequest(
            collaborator_id="123",
            amount=100,
            currency="USD",
            description="Test payment 1",
            due_date=now,
            payment_method=PaymentMethod.CRYPTO,
            status=PaymentStatus.PAID,
            created_at=week_ago,
            paid_at=now
        ),
        "payment2": PaymentRequest(
            collaborator_id="124",
            amount=200,
            currency="EUR",
            description="Test payment 2",
            due_date=now,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PENDING,
            created_at=week_ago
        ),
        "payment3": PaymentRequest(
            collaborator_id="125",
            amount=150,
            currency="USD",
            description="Test payment 3",
            due_date=now,
            payment_method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.FAILED,
            created_at=week_ago
        )
    }
    bot.team_manager.set_payments(payments)
    
    analytics = await bot.team_manager.payment_manager.get_payment_analytics(
        start_date=week_ago,
        end_date=now
    )
    
    assert analytics["total_volume"] == 450.0
    assert analytics["successful_payments"] == 1
    assert analytics["failed_payments"] == 1
    assert analytics["pending_payments"] == 1
    assert analytics["average_amount"] == 150.0
    assert len(analytics["by_payment_method"]) == 3
    assert len(analytics["by_currency"]) == 2
    assert len(analytics["daily_volume"]) > 0
    assert "average_processing_time" in analytics 