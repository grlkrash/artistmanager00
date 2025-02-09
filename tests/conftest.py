import pytest
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from langchain_community.chat_models import ChatOpenAI
from artist_manager_agent.models import ArtistProfile
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.agent import ArtistManagerAgent

# Load test environment variables
load_dotenv(".env.test")

@pytest.fixture(autouse=True)
def test_env():
    """Set up test environment variables."""
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
    os.environ["OPENAI_API_KEY"] = "test_key"
    os.environ["SUPABASE_URL"] = "test_url"
    os.environ["SUPABASE_KEY"] = "test_key"
    os.environ["AI_MASTERING_KEY"] = "test_key"

@pytest.fixture
def test_data_dir():
    """Get the test data directory."""
    return Path(__file__).parent / "data"

@pytest.fixture
def artist_profile():
    """Create a test artist profile."""
    return ArtistProfile(
        id="test-artist",
        name="Test Artist",
        genre="Pop",
        career_stage="Emerging",
        goals=["Increase streaming numbers", "Book more live shows"],
        strengths=["Vocal ability", "Stage presence"],
        areas_for_improvement=["Social media presence", "Networking"],
        achievements=["Released debut EP", "100k Spotify streams"],
        social_media={
            "instagram": "@testartist",
            "twitter": "@testartist"
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

@pytest.fixture
def agent(artist_profile):
    """Create a test agent."""
    return ArtistManagerAgent(
        artist_profile=artist_profile,
        openai_api_key="test-key",
        model="gpt-3.5-turbo",
        db_url="sqlite:///:memory:",
        telegram_token="test-token",
        ai_mastering_key="test-key"
    )

@pytest.fixture
def mock_wallet():
    """Create a mock wallet."""
    mock = MagicMock()
    mock.deploy_nft = AsyncMock()
    mock.invoke_contract = AsyncMock()
    mock.deploy_token = AsyncMock()
    mock.transfer = AsyncMock()
    mock.faucet = AsyncMock()
    return mock

@pytest.fixture
def mock_bot(agent):
    """Create a mock bot."""
    return agent

@pytest.fixture
def profile():
    """Create a test artist profile."""
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
def bot(profile):
    """Create a test bot instance."""
    return ArtistManagerBot(
        artist_profile=profile,
        openai_api_key="test-key-123",
        model="gpt-3.5-turbo",
        db_url="sqlite:///test.db",
        telegram_token="test-telegram-token",
        ai_mastering_key="test-mastering-key"
    )

@pytest.fixture
def update():
    """Create a mock Telegram update."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "/start"
    update.message.chat_id = 123456789
    return update

@pytest.fixture
def context():
    """Create a mock Telegram context."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    return context

@pytest.fixture(autouse=True)
def mock_aiohttp_session(monkeypatch):
    """Mock aiohttp ClientSession to prevent actual HTTP requests."""
    import aiohttp
    
    class MockClientSession:
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
        async def close(self):
            pass
    
    monkeypatch.setattr(aiohttp, "ClientSession", MockClientSession) 