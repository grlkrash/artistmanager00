import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes, CallbackContext

from artist_manager_agent.team_management import PaymentMethod, PaymentStatus, PaymentRequest
from artist_manager_agent.main import ArtistManagerBot

@pytest.fixture
def bot():
    return ArtistManagerBot()

@pytest.fixture
def update():
    update = MagicMock(spec=Update)
    update.effective_user = User(id=123, first_name="Test", is_bot=False)
    update.message = Message(1, datetime.now(), Chat(1, "private"))
    return update

@pytest.fixture
def context():
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    return context

@pytest.mark.asyncio
async def test_setup_payment(bot, update, context):
    """Test payment setup command."""
    await bot.setup_payment(update, context)
    update.message.reply_text.assert_called_once()
    assert "Choose your preferred payment method" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_payment_method(bot, update, context):
    """Test payment method selection."""
    query = AsyncMock(spec=CallbackQuery)
    query.data = "payment_crypto"
    update.callback_query = query
    
    await bot.handle_payment_method(update, context)
    
    assert context.user_data["payment_method"] == PaymentMethod.CRYPTO
    query.edit_message_text.assert_called_once()
    assert "Crypto payments enabled" in query.edit_message_text.call_args[0][0]

@pytest.mark.asyncio
async def test_request_payment_success(bot, update, context):
    """Test successful payment request creation."""
    context.args = ["100", "USD", "Test", "payment"]
    context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    # Mock team manager create_payment_request
    mock_result = {"payment_url": "https://test.com/pay", "status": "pending"}
    bot.team_manager.create_payment_request = AsyncMock(return_value=mock_result)
    
    await bot.request_payment(update, context)
    
    bot.team_manager.create_payment_request.assert_called_once()
    update.message.reply_text.assert_called_once()
    assert "Payment request created" in update.message.reply_text.call_args[0][0]
    assert "https://test.com/pay" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_request_payment_invalid_args(bot, update, context):
    """Test payment request with invalid arguments."""
    context.args = ["invalid", "USD"]
    
    await bot.request_payment(update, context)
    
    update.message.reply_text.assert_called_once()
    assert "Usage: /request_payment" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_check_payment_success(bot, update, context):
    """Test successful payment status check."""
    context.args = ["payment123"]
    
    mock_status = {
        "status": "paid",
        "paid": True,
        "amount_paid": 100,
        "currency": "USD"
    }
    bot.team_manager.check_payment_status = AsyncMock(return_value=mock_status)
    
    await bot.check_payment(update, context)
    
    bot.team_manager.check_payment_status.assert_called_once_with("payment123")
    update.message.reply_text.assert_called_once()
    assert "Status: paid" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_list_payments_empty(bot, update, context):
    """Test listing payments when none exist."""
    bot.team_manager.payments = {}
    
    await bot.list_payments(update, context)
    
    update.message.reply_text.assert_called_once_with("No payment requests found.")

@pytest.mark.asyncio
async def test_list_payments_with_data(bot, update, context):
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
    
    await bot.list_payments(update, context)
    
    update.message.reply_text.assert_called_once()
    response = update.message.reply_text.call_args[0][0]
    assert "Payment Requests:" in response
    assert "Amount: 100 USD" in response
    assert "Status: pending" in response

@pytest.mark.asyncio
async def test_request_payment_no_payment_method(bot, update, context):
    """Test payment request without setting payment method."""
    context.args = ["100", "USD", "Test payment"]
    # Don't set payment_method in user_data
    
    await bot.request_payment(update, context)
    
    # Should default to bank transfer
    assert any(call.kwargs.get("payment_method", None) == PaymentMethod.BANK_TRANSFER 
              for call in bot.team_manager.create_payment_request.mock_calls)

@pytest.mark.asyncio
async def test_request_payment_missing_description(bot, update, context):
    """Test payment request with missing description."""
    context.args = ["100", "USD"]
    context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    await bot.request_payment(update, context)
    
    update.message.reply_text.assert_called_once()
    assert "Usage: /request_payment" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_check_payment_no_id(bot, update, context):
    """Test payment status check without payment ID."""
    context.args = []
    
    await bot.check_payment(update, context)
    
    update.message.reply_text.assert_called_once()
    assert "Usage: /check_payment" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_check_payment_not_found(bot, update, context):
    """Test payment status check for non-existent payment."""
    context.args = ["nonexistent"]
    
    # Mock payment not found
    bot.team_manager.check_payment_status = AsyncMock(side_effect=Exception("Payment not found"))
    
    await bot.check_payment(update, context)
    
    update.message.reply_text.assert_called_once()
    assert "Error checking payment status" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_payment_method_invalid(bot, update, context):
    """Test handling invalid payment method selection."""
    query = AsyncMock(spec=CallbackQuery)
    query.data = "payment_invalid"
    update.callback_query = query
    
    with pytest.raises(KeyError):
        await bot.handle_payment_method(update, context)

@pytest.mark.asyncio
async def test_request_payment_negative_amount(bot, update, context):
    """Test payment request with negative amount."""
    context.args = ["-100", "USD", "Test payment"]
    context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    await bot.request_payment(update, context)
    
    update.message.reply_text.assert_called_once()
    assert "Invalid amount" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_request_payment_invalid_currency(bot, update, context):
    """Test payment request with invalid currency."""
    context.args = ["100", "INVALID", "Test payment"]
    context.user_data["payment_method"] = PaymentMethod.CRYPTO
    
    # Mock currency validation error
    bot.team_manager.create_payment_request = AsyncMock(
        side_effect=ValueError("Invalid currency")
    )
    
    await bot.request_payment(update, context)
    
    update.message.reply_text.assert_called_once()
    assert "Error creating payment request" in update.message.reply_text.call_args[0][0] 