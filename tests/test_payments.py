import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from telegram import Bot, Update, Message, Chat, User
from telegram.ext import ContextTypes
from artist_manager_agent.main import ArtistManagerBot
from artist_manager_agent.team_management import PaymentRequest, PaymentMethod, PaymentStatus

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
def bot(mock_bot):
    bot = ArtistManagerBot(token="test_token")
    bot.bot = mock_bot
    return bot

@pytest.mark.asyncio
async def test_setup_payment(bot, mock_update, mock_context):
    """Test setting up payment method."""
    mock_context.args = ["crypto"]
    await bot.setup_payment(mock_update, mock_context)
    assert mock_context.user_data["payment_method"] == PaymentMethod.CRYPTO

@pytest.mark.asyncio
async def test_request_payment_success(bot, mock_update, mock_context):
    """Test successful payment request."""
    mock_context.args = ["100", "USD", "Test payment"]
    mock_context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    # Mock successful payment request
    mock_result = {
        "id": "payment123",
        "payment_url": "https://test.com/pay",
        "status": "pending"
    }
    bot.team_manager.create_payment_request = AsyncMock(return_value=mock_result)
    
    await bot.request_payment(mock_update, mock_context)
    
    # Verify payment request was created
    bot.team_manager.create_payment_request.assert_called_once()

@pytest.mark.asyncio
async def test_request_payment_invalid_args(bot, mock_update, mock_context):
    """Test payment request with invalid arguments."""
    mock_context.args = ["invalid", "USD"]
    await bot.request_payment(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Invalid amount format. Please use numbers only."
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
    
    # Verify payment request was created with default payment method
    bot.team_manager.create_payment_request.assert_called_once()

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
    
    # Mock currency validation error
    bot.team_manager.create_payment_request = AsyncMock(
        side_effect=ValueError("Invalid currency")
    )
    
    await bot.request_payment(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Error creating payment request: Invalid currency"
    ) 