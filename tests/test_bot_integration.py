import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from telegram import Bot, Update, Message, Chat, User
from telegram.ext import ContextTypes

from artist_manager_agent.agent import ArtistManagerAgent, ArtistProfile
from artist_manager_agent.bot_commands import BotCommandHandler
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.models import ArtistProfile

@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot

@pytest.fixture
def mock_update():
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.effective_chat.id = 123456789
    return update

@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    return context

@pytest.fixture
def artist_profile():
    return ArtistProfile(
        id="test-artist",
        name="Test Artist",
        email="test@example.com",
        genre="Pop",
        genres=["pop", "rock"],
        career_stage="Emerging",
        goals=["Increase streaming numbers", "Book more live shows"],
        strengths=["Vocal ability", "Stage presence"],
        areas_for_improvement=["Social media presence", "Networking"],
        achievements=["Released debut EP", "100k Spotify streams"],
        social_media={
            "twitter": "@testartist",
            "instagram": "@testartist"
        },
        streaming_profiles={
            "spotify": "spotify:artist:123",
            "apple_music": "apple:artist:123"
        },
        brand_guidelines={
            "colors": ["#000000", "#FFFFFF"],
            "fonts": ["Helvetica", "Arial"]
        }
    )

@pytest_asyncio.fixture
async def bot(artist_profile):
    bot = ArtistManagerBot(
        artist_profile=artist_profile,
        openai_api_key="test_key",
        model="gpt-3.5-turbo",
        db_url="sqlite:///:memory:",
        telegram_token="mock_token_123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    )
    return bot

@pytest.mark.asyncio
async def test_start_command(bot, mock_update, mock_context):
    """Test the start command."""
    await bot.start(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_help_command(bot, mock_update, mock_context):
    """Test the help command."""
    await bot.help(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_goals_command(bot, mock_update, mock_context):
    """Test the goals command."""
    await bot.goals(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_tasks_command(bot, mock_update, mock_context):
    """Test the tasks command."""
    await bot.tasks(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_health_command(bot, mock_update, mock_context):
    """Test the health command."""
    await bot.health(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once() 