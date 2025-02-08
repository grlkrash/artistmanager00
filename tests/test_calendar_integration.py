import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from telegram import Bot, Update, Message, Chat, User
from telegram.ext import ContextTypes
from artist_manager_agent.agent import (
    ArtistManagerAgent,
    Event
)

@pytest.fixture
def agent():
    return ArtistManagerAgent()

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
async def test_add_event(agent, sample_event):
    """Test adding an event."""
    await agent.add_event(sample_event)
    events = await agent.get_events()
    assert len(events) == 1
    assert events[0].event_id == "event_1"
    assert events[0].title == "Team Meeting"
    assert events[0].status == "scheduled"

@pytest.mark.asyncio
async def test_update_event(agent, sample_event):
    """Test updating an event."""
    await agent.add_event(sample_event)
    updated_event = sample_event.copy()
    updated_event.status = "completed"
    await agent.update_event(updated_event)
    events = await agent.get_events()
    assert events[0].status == "completed"

@pytest.mark.asyncio
async def test_cancel_event(agent, sample_event):
    """Test canceling an event."""
    await agent.add_event(sample_event)
    cancelled_event = sample_event.copy()
    cancelled_event.status = "cancelled"
    await agent.update_event(cancelled_event)
    events = await agent.get_events()
    assert events[0].status == "cancelled"

@pytest.mark.asyncio
async def test_get_upcoming_events(agent):
    """Test getting upcoming events."""
    # Create events for different days
    event1 = Event(
        event_id="event_1",
        title="Today's Meeting",
        description="Team sync",
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        location="Virtual",
        attendees=["John Doe"],
        status="scheduled",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    event2 = Event(
        event_id="event_2",
        title="Tomorrow's Meeting",
        description="Project review",
        start_time=datetime.now() + timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1, hours=1),
        location="Virtual",
        attendees=["John Doe", "Jane Smith"],
        status="scheduled",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    await agent.add_event(event1)
    await agent.add_event(event2)
    
    # Get upcoming events
    upcoming = await agent.get_upcoming_events()
    assert len(upcoming) == 2
    assert any(e.event_id == "event_1" for e in upcoming)
    assert any(e.event_id == "event_2" for e in upcoming)
    
    # Get upcoming events for specific attendee
    john_events = await agent.get_upcoming_events(attendee="John Doe")
    assert len(john_events) == 2
    
    jane_events = await agent.get_upcoming_events(attendee="Jane Smith")
    assert len(jane_events) == 1
    assert jane_events[0].event_id == "event_2"

@pytest.mark.asyncio
async def test_get_event_report(agent, sample_event):
    """Test generating an event report."""
    await agent.add_event(sample_event)
    report = await agent.get_event_report()
    assert report["total_events"] == 1
    assert report["by_status"]["scheduled"] == 1 