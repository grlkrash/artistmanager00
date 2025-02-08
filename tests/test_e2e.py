import pytest
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any

from artist_manager_agent.agent import (
    ArtistManagerAgent,
    ArtistProfile,
    Contract,
    Event,
    Task,
    FinancialRecord
)

@pytest.fixture
def agent():
    """Create a test agent with a complete profile."""
    profile = ArtistProfile(
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
            "tone": "Authentic and energetic",
            "values": ["Creativity", "Authenticity", "Connection"]
        },
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    return ArtistManagerAgent(
        artist_profile=profile,
        openai_api_key="test_key"
    )

@pytest.mark.asyncio
async def test_album_release_workflow(agent):
    """Test the complete workflow of planning and executing an album release."""
    # 1. Create album project
    contract = Contract(
        title="Album Production Agreement",
        parties=["Test Artist", "Producer"],
        terms={
            "duration": "6 months",
            "deliverables": ["10 tracks", "2 music videos"],
            "rights": "Full ownership to artist"
        },
        status="active",
        value=50000.0,
        expiration=datetime.now() + timedelta(days=180)
    )
    await agent.add_contract(contract)
    
    # 2. Create production tasks
    tasks = [
        Task(
            title="Record vocals",
            description="Record vocals for all tracks",
            deadline=datetime.now() + timedelta(days=30),
            assigned_to="Test Artist",
            status="pending",
            priority=1
        ),
        Task(
            title="Mix tracks",
            description="Mix all recorded tracks",
            deadline=datetime.now() + timedelta(days=60),
            assigned_to="Producer",
            status="pending",
            priority=2
        ),
        Task(
            title="Plan release",
            description="Plan marketing and release strategy",
            deadline=datetime.now() + timedelta(days=90),
            assigned_to="Manager",
            status="pending",
            priority=3
        )
    ]
    
    for task in tasks:
        await agent.add_task(task)
    
    # 3. Schedule release events
    events = [
        Event(
            title="Album Release Party",
            type="release_party",
            date=datetime.now() + timedelta(days=100),
            venue="Luxury Venue",
            capacity=500,
            budget=10000.0,
            status="planned"
        ),
        Event(
            title="Press Conference",
            type="press",
            date=datetime.now() + timedelta(days=95),
            venue="Hotel Conference Room",
            capacity=50,
            budget=2000.0,
            status="planned"
        )
    ]
    
    for event in events:
        await agent.add_event(event)
    
    # 4. Record financial transactions
    transactions = [
        FinancialRecord(
            date=datetime.now(),
            type="expense",
            amount=25000.0,
            category="production",
            description="Initial producer payment"
        ),
        FinancialRecord(
            date=datetime.now(),
            type="expense",
            amount=5000.0,
            category="marketing",
            description="Marketing campaign setup"
        )
    ]
    
    for transaction in transactions:
        await agent.add_financial_record(transaction)
    
    # 5. Verify the complete workflow
    contracts = await agent.get_contracts()
    assert len(contracts) == 1
    assert contracts[0].title == "Album Production Agreement"
    
    stored_tasks = await agent.get_tasks()
    assert len(stored_tasks) == 3
    
    stored_events = await agent.get_events()
    assert len(stored_events) == 2
    
    records = await agent.get_financial_records()
    assert len(records) == 2
    assert sum(r.amount for r in records) == 30000.0

@pytest.mark.asyncio
async def test_crisis_management_workflow(agent):
    """Test the workflow of handling a PR crisis."""
    # 1. Create crisis task
    crisis_task = Task(
        title="Handle PR Crisis",
        description="Address negative press coverage",
        deadline=datetime.now() + timedelta(days=1),
        assigned_to="PR Manager",
        status="urgent",
        priority=1
    )
    await agent.add_task(crisis_task)
    
    # 2. Schedule emergency meetings
    meetings = [
        Event(
            title="Emergency Team Meeting",
            type="internal",
            date=datetime.now() + timedelta(hours=2),
            venue="Virtual",
            capacity=10,
            budget=0.0,
            status="scheduled"
        ),
        Event(
            title="Press Statement",
            type="press",
            date=datetime.now() + timedelta(days=1),
            venue="Online",
            capacity=0,
            budget=1000.0,
            status="scheduled"
        )
    ]
    
    for meeting in meetings:
        await agent.add_event(meeting)
    
    # 3. Record crisis management expenses
    expense = FinancialRecord(
        date=datetime.now(),
        type="expense",
        amount=5000.0,
        category="crisis_management",
        description="Emergency PR services"
    )
    await agent.add_financial_record(expense)
    
    # 4. Verify crisis management workflow
    tasks = await agent.get_tasks()
    assert any(t.title == "Handle PR Crisis" for t in tasks)
    
    events = await agent.get_events()
    assert any(e.title == "Emergency Team Meeting" for e in events)
    assert any(e.title == "Press Statement" for e in events)
    
    records = await agent.get_financial_records()
    assert any(r.category == "crisis_management" for r in records)

@pytest.mark.asyncio
async def test_tour_planning_workflow(agent):
    """Test the workflow of planning and managing a tour."""
    # 1. Create tour contract
    tour_contract = Contract(
        title="Summer Tour Agreement",
        parties=["Test Artist", "Tour Manager", "Venues"],
        terms={
            "duration": "3 months",
            "venues": "10 cities",
            "support": "Full production support"
        },
        status="pending",
        value=100000.0,
        expiration=datetime.now() + timedelta(days=120)
    )
    await agent.add_contract(tour_contract)
    
    # 2. Create tour planning tasks
    planning_tasks = [
        Task(
            title="Book venues",
            description="Secure all tour venues",
            deadline=datetime.now() + timedelta(days=30),
            assigned_to="Tour Manager",
            status="pending",
            priority=1
        ),
        Task(
            title="Arrange transportation",
            description="Book tour bus and flights",
            deadline=datetime.now() + timedelta(days=45),
            assigned_to="Tour Manager",
            status="pending",
            priority=2
        ),
        Task(
            title="Hire support staff",
            description="Hire technical and support crew",
            deadline=datetime.now() + timedelta(days=60),
            assigned_to="Tour Manager",
            status="pending",
            priority=2
        )
    ]
    
    for task in planning_tasks:
        await agent.add_task(task)
    
    # 3. Schedule tour dates
    tour_dates = []
    start_date = datetime.now() + timedelta(days=90)
    
    for i in range(10):
        event = Event(
            title=f"Tour Stop {i+1}",
            type="concert",
            date=start_date + timedelta(days=i*3),
            venue=f"Venue {i+1}",
            capacity=1000,
            budget=8000.0,
            status="scheduled"
        )
        tour_dates.append(event)
    
    for event in tour_dates:
        await agent.add_event(event)
    
    # 4. Record tour expenses
    expenses = [
        FinancialRecord(
            date=datetime.now(),
            type="expense",
            amount=20000.0,
            category="tour_transportation",
            description="Tour bus deposit"
        ),
        FinancialRecord(
            date=datetime.now(),
            type="expense",
            amount=15000.0,
            category="tour_staff",
            description="Staff advances"
        )
    ]
    
    for expense in expenses:
        await agent.add_financial_record(expense)
    
    # 5. Verify tour planning workflow
    contracts = await agent.get_contracts()
    assert any(c.title == "Summer Tour Agreement" for c in contracts)
    
    tasks = await agent.get_tasks()
    assert len([t for t in tasks if "tour" in t.title.lower()]) == 3
    
    events = await agent.get_events()
    assert len([e for e in events if "Tour Stop" in e.title]) == 10
    
    records = await agent.get_financial_records()
    tour_expenses = [r for r in records if "tour" in r.category.lower()]
    assert sum(r.amount for r in tour_expenses) == 35000.0 