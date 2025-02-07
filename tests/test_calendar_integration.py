import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from telegram import Bot, Update, Message, Chat, User
from telegram.ext import ContextTypes
from artist_manager_agent.team_management import (
    TeamManager,
    CalendarIntegration,
    CalendarProvider,
    AvailabilityPreference,
    Meeting,
    CollaboratorProfile,
    CollaboratorRole
)

@pytest.fixture
def team_manager():
    return TeamManager()

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
def sample_collaborators(team_manager):
    async def _create_collaborators():
        collaborator1 = CollaboratorProfile(
            name="John Doe",
            role=CollaboratorRole.PRODUCER,
            expertise=["Music Production"],
            availability={
                "monday": ["09:00-17:00"],
                "tuesday": ["10:00-18:00"]
            }
        )
        collaborator2 = CollaboratorProfile(
            name="Jane Smith",
            role=CollaboratorRole.ENGINEER,
            expertise=["Sound Engineering"],
            availability={
                "monday": ["10:00-18:00"],
                "tuesday": ["09:00-17:00"]
            }
        )
        
        id1 = await team_manager.add_collaborator(collaborator1)
        id2 = await team_manager.add_collaborator(collaborator2)
        return [id1, id2]
    
    return _create_collaborators

@pytest.mark.asyncio
async def test_add_calendar_integration(team_manager, sample_collaborators):
    """Test adding calendar integration."""
    collaborator_ids = await sample_collaborators()
    
    integration_id = await team_manager.add_calendar_integration(
        collaborator_id=collaborator_ids[0],
        provider=CalendarProvider.GOOGLE,
        credentials={"token": "test_token"},
        preferences={
            "auto_sync": True,
            "availability_preference": AvailabilityPreference.AUTOMATIC
        }
    )
    
    assert integration_id in team_manager.calendar_integrations
    integration = team_manager.calendar_integrations[integration_id]
    assert integration.collaborator_id == collaborator_ids[0]
    assert integration.provider == CalendarProvider.GOOGLE
    assert integration.preferences["auto_sync"] is True

@pytest.mark.asyncio
async def test_schedule_meeting(team_manager, sample_collaborators):
    """Test scheduling a meeting."""
    collaborator_ids = await sample_collaborators()
    
    # Add calendar integrations
    for collab_id in collaborator_ids:
        await team_manager.add_calendar_integration(
            collaborator_id=collab_id,
            provider=CalendarProvider.GOOGLE,
            credentials={"token": "test_token"}
        )
    
    # Schedule a meeting for Monday at 10:00
    monday = datetime.strptime("2024-02-12 10:00", "%Y-%m-%d %H:%M")
    meeting = await team_manager.schedule_meeting(
        title="Test Meeting",
        attendees=collaborator_ids,
        duration_minutes=60,
        earliest_start=monday,
        latest_start=monday.replace(hour=16),
        meeting_type="project",
        description="Test project meeting"
    )
    
    assert meeting is not None
    assert meeting.title == "Test Meeting"
    assert meeting.status == "scheduled"
    assert set(meeting.attendees) == set(collaborator_ids)
    assert (meeting.end_time - meeting.start_time).total_seconds() / 60 == 60
    assert meeting.start_time.hour == 10  # Should start at 10:00

@pytest.mark.asyncio
async def test_cancel_meeting(team_manager, sample_collaborators):
    """Test canceling a meeting."""
    collaborator_ids = await sample_collaborators()
    
    # Schedule a meeting first
    monday = datetime.strptime("2024-02-12 10:00", "%Y-%m-%d %H:%M")
    meeting = await team_manager.schedule_meeting(
        title="Test Meeting",
        attendees=collaborator_ids,
        duration_minutes=60,
        earliest_start=monday,
        latest_start=monday.replace(hour=16),
        meeting_type="project"
    )
    
    assert meeting is not None
    
    # Cancel the meeting
    success = await team_manager.cancel_meeting(meeting.id)
    assert success is True
    
    # Verify meeting is cancelled
    cancelled_meeting = team_manager.meetings[meeting.id]
    assert cancelled_meeting.status == "cancelled"

@pytest.mark.asyncio
async def test_get_upcoming_meetings(team_manager, sample_collaborators):
    """Test getting upcoming meetings."""
    collaborator_ids = await sample_collaborators()
    
    # Schedule multiple meetings
    monday = datetime.strptime("2024-02-12 10:00", "%Y-%m-%d %H:%M")
    meeting1 = await team_manager.schedule_meeting(
        title="Meeting 1",
        attendees=[collaborator_ids[0]],
        duration_minutes=60,
        earliest_start=monday,
        latest_start=monday.replace(hour=16),
        meeting_type="project"
    )
    
    assert meeting1 is not None
    
    tuesday = monday + timedelta(days=1)
    meeting2 = await team_manager.schedule_meeting(
        title="Meeting 2",
        attendees=collaborator_ids,
        duration_minutes=60,
        earliest_start=tuesday,
        latest_start=tuesday.replace(hour=16),
        meeting_type="project"
    )
    
    assert meeting2 is not None
    
    # Get upcoming meetings for first collaborator
    upcoming = await team_manager.get_upcoming_meetings(collaborator_ids[0])
    assert len(upcoming) == 2
    assert meeting1 in upcoming
    assert meeting2 in upcoming
    
    # Get upcoming meetings for second collaborator
    upcoming = await team_manager.get_upcoming_meetings(collaborator_ids[1])
    assert len(upcoming) == 1
    assert meeting2 in upcoming 