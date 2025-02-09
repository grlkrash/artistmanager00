import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from telegram import Bot, Update, Message, Chat, User
from telegram.ext import ContextTypes
from artist_manager_agent.agent import (
    ArtistManagerAgent,
    Event
)
from artist_manager_agent.models import ArtistProfile
import time

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

@pytest.fixture
def agent(artist_profile):
    return ArtistManagerAgent(
        artist_profile=artist_profile,
        openai_api_key="test_key",
        model="gpt-3.5-turbo",
        database_url="sqlite:///:memory:"
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
def sample_event():
    return Event(
        event_id="event_1",
        title="Team Meeting",
        description="Weekly team sync",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        location="Virtual",
        attendees=["John Doe", "Jane Smith"],
        status="scheduled",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.mark.asyncio
async def test_add_event(agent):
    """Test adding an event."""
    event = Event(
        id=f"event_{int(time.time())}",
        title="Test Event",
        description="Test event description",
        type="concert",
        date=datetime.now() + timedelta(days=1),
        venue="Test Venue",
        capacity=100,
        budget=1000.0,
        status="scheduled"
    )
    
    added_event = await agent.add_event(event)
    assert added_event.id == event.id
    assert added_event.title == event.title

@pytest.mark.asyncio
async def test_update_event(agent):
    """Test updating an event."""
    event = Event(
        id=f"event_{int(time.time())}",
        title="Test Event",
        description="Test event description",
        type="concert",
        date=datetime.now() + timedelta(days=1),
        venue="Test Venue",
        capacity=100,
        budget=1000.0,
        status="scheduled"
    )
    
    await agent.add_event(event)
    event.title = "Updated Event"
    updated_event = await agent.update_event(event)
    assert updated_event.title == "Updated Event"

@pytest.mark.asyncio
async def test_cancel_event(agent):
    """Test canceling an event."""
    event = Event(
        id=f"event_{int(time.time())}",
        title="Test Event",
        description="Test event description",
        type="concert",
        date=datetime.now() + timedelta(days=1),
        venue="Test Venue",
        capacity=100,
        budget=1000.0,
        status="scheduled"
    )
    
    await agent.add_event(event)
    event.status = "cancelled"
    updated_event = await agent.update_event(event)
    assert updated_event.status == "cancelled"

@pytest.mark.asyncio
async def test_get_upcoming_events(agent):
    """Test getting upcoming events."""
    event = Event(
        id=f"event_{int(time.time())}",
        title="Test Event",
        description="Test event description",
        type="concert",
        date=datetime.now() + timedelta(days=1),
        venue="Test Venue",
        capacity=100,
        budget=1000.0,
        status="scheduled"
    )
    
    await agent.add_event(event)
    events = await agent.get_events()
    assert len(events) > 0
    assert any(e.id == event.id for e in events)

@pytest.mark.asyncio
async def test_get_event_report(agent):
    """Test getting event report."""
    event = Event(
        id=f"event_{int(time.time())}",
        title="Test Event",
        description="Test event description",
        type="concert",
        date=datetime.now() + timedelta(days=1),
        venue="Test Venue",
        capacity=100,
        budget=1000.0,
        status="scheduled"
    )
    
    await agent.add_event(event)
    start_date = datetime.now()
    end_date = datetime.now() + timedelta(days=30)
    events = await agent.get_events_in_range(start_date, end_date)
    assert len(events) > 0
    assert any(e.id == event.id for e in events) 