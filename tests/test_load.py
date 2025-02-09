import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List
import time

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
    """Create a test agent."""
    profile = ArtistProfile(
        id="test-profile-123",
        name="Test Artist",
        genre="Pop",
        career_stage="emerging",
        goals=["Release album"],
        strengths=["Vocals"],
        areas_for_improvement=["Marketing"],
        achievements=[],
        social_media={},
        streaming_profiles={},
        health_notes=[],
        brand_guidelines={},
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    return ArtistManagerAgent(
        artist_profile=profile,
        openai_api_key="test_key"
    )

async def create_concurrent_tasks(agent: ArtistManagerAgent, count: int) -> List[Task]:
    """Create multiple tasks concurrently."""
    tasks = []
    for i in range(count):
        task = Task(
            title=f"Test Task {i}",
            description=f"Description {i}",
            deadline=datetime.now() + timedelta(days=1),
            assigned_to="Test User",
            status="pending",
            priority=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        tasks.append(task)
    
    await asyncio.gather(*[agent.add_task(task) for task in tasks])
    return tasks

async def create_concurrent_events(agent: ArtistManagerAgent, count: int) -> List[Event]:
    """Create multiple events concurrently."""
    events = []
    for i in range(count):
        event = Event(
            title=f"Test Event {i}",
            type="concert",
            date=datetime.now() + timedelta(days=i),
            venue=f"Venue {i}",
            capacity=1000,
            budget=1000.0,
            status="scheduled",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        events.append(event)
    
    await asyncio.gather(*[agent.add_event(event) for event in events])
    return events

@pytest.mark.asyncio
async def test_concurrent_task_creation(agent):
    """Test creating many tasks concurrently."""
    start_time = time.time()
    tasks = await create_concurrent_tasks(agent, 100)
    end_time = time.time()
    
    # Verify all tasks were created
    stored_tasks = await agent.get_tasks()
    assert len(stored_tasks) == 100
    
    # Check performance
    execution_time = end_time - start_time
    assert execution_time < 5.0  # Should complete in under 5 seconds

@pytest.mark.asyncio
async def test_concurrent_event_creation(agent):
    """Test creating many events concurrently."""
    start_time = time.time()
    events = await create_concurrent_events(agent, 100)
    end_time = time.time()
    
    # Verify all events were created
    stored_events = await agent.get_events()
    assert len(stored_events) == 100
    
    # Check performance
    execution_time = end_time - start_time
    assert execution_time < 5.0  # Should complete in under 5 seconds

@pytest.mark.asyncio
async def test_mixed_concurrent_operations(agent):
    """Test performing different types of operations concurrently."""
    start_time = time.time()
    
    # Create tasks, events, and financial records concurrently
    tasks = [create_concurrent_tasks(agent, 50)]
    events = [create_concurrent_events(agent, 50)]
    
    records = []
    for i in range(50):
        record = FinancialRecord(
            date=datetime.now(),
            type="income",
            amount=1000.0,
            category="performance",
            description=f"Test Record {i}",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        records.append(agent.add_financial_record(record))
    
    # Execute all operations concurrently
    await asyncio.gather(
        *tasks,
        *events,
        *records
    )
    
    end_time = time.time()
    
    # Verify all items were created
    stored_tasks = await agent.get_tasks()
    stored_events = await agent.get_events()
    stored_records = await agent.get_financial_records()
    
    assert len(stored_tasks) == 50
    assert len(stored_events) == 50
    assert len(stored_records) == 50
    
    # Check performance
    execution_time = end_time - start_time
    assert execution_time < 10.0  # Should complete in under 10 seconds

@pytest.mark.asyncio
async def test_rapid_sequential_operations(agent):
    """Test performing rapid sequential operations."""
    start_time = time.time()
    
    for i in range(100):
        # Add a task
        task = Task(
            title=f"Quick Task {i}",
            description="Quick task",
            deadline=datetime.now() + timedelta(days=1),
            assigned_to="Test User",
            status="pending",
            priority=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await agent.add_task(task)
        
        # Update the task immediately
        task.status = "in_progress"
        await agent.update_task(task)
        
        # Delete the task
        await agent.delete_task(task.id)
    
    end_time = time.time()
    
    # Check performance
    execution_time = end_time - start_time
    assert execution_time < 20.0  # Should complete in under 20 seconds 