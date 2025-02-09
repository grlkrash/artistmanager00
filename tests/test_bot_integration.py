import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from telegram import Bot, Update, Message, Chat, User
from telegram.ext import ContextTypes

from artist_manager_agent.agent import ArtistManagerAgent, ArtistProfile
from artist_manager_agent.bot_commands import BotCommandHandler

@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123
    update.effective_user.first_name = "Test"
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 456
    return update

@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = mock_bot()
    return context

@pytest.fixture
def artist_profile():
    return ArtistProfile(
        id="test-profile-123",
        name="Test Artist",
        genre="Pop",
        career_stage="emerging",
        goals=[
            "Release album",
            "Grow social media following",
            "Book live shows"
        ],
        strengths=[
            "Vocals",
            "Songwriting",
            "Stage presence"
        ],
        areas_for_improvement=[
            "Marketing",
            "Time management",
            "Networking"
        ],
        achievements=[
            "Released debut EP",
            "100K streams on Spotify"
        ],
        social_media={
            "instagram": "@test_artist",
            "twitter": "@test_artist",
            "tiktok": "@test_artist"
        },
        streaming_profiles={
            "spotify": "spotify:artist:test",
            "apple_music": "artist/test",
            "soundcloud": "test_artist"
        },
        health_notes=[],
        brand_guidelines={
            "colors": ["#FF0000", "#00FF00"],
            "fonts": ["Helvetica", "Arial"],
            "tone": ["Authentic", "Energetic", "Professional"],
            "values": ["Creativity", "Authenticity", "Connection"]
        },
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def agent(artist_profile):
    return ArtistManagerAgent(
        artist_profile=artist_profile,
        openai_api_key="test_key"
    )

@pytest.mark.asyncio
async def test_start_command(agent, mock_update, mock_context):
    """Test the /start command."""
    handler = BotCommandHandler(agent)
    await handler.handle_start(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "Welcome" in mock_update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_help_command(agent, mock_update, mock_context):
    """Test the /help command."""
    handler = BotCommandHandler(agent)
    await handler.handle_help(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "Commands" in mock_update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_goals_command(agent, mock_update, mock_context):
    """Test the /goals command."""
    handler = BotCommandHandler(agent)
    await handler.handle_goals(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "goals" in mock_update.message.reply_text.call_args[0][0].lower()

@pytest.mark.asyncio
async def test_tasks_command(agent, mock_update, mock_context):
    """Test the /tasks command."""
    handler = BotCommandHandler(agent)
    await handler.handle_tasks(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "tasks" in mock_update.message.reply_text.call_args[0][0].lower()

@pytest.mark.asyncio
async def test_health_command(agent, mock_update, mock_context):
    """Test the /health command."""
    handler = BotCommandHandler(agent)
    await handler.handle_health(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "health" in mock_update.message.reply_text.call_args[0][0].lower() 