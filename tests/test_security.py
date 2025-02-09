import pytest
from datetime import datetime, timedelta
import re
import json
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

def contains_sensitive_info(text: str) -> bool:
    """Check if text contains sensitive information patterns."""
    patterns = [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone number
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b(?:\d[ -]*?){13,16}\b",  # Credit card
        r"password|secret|key|token|credential",  # Sensitive keywords
        r"api[_-]?key|access[_-]?token|secret[_-]?key"  # API credentials
    ]
    
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

@pytest.mark.asyncio
async def test_no_sensitive_info_in_tasks(agent):
    """Test that tasks don't contain sensitive information."""
    task = Task(
        id="test-task",
        title="Contact artist",
        description="Send contract documents",
        deadline=datetime.now() + timedelta(days=1),
        assigned_to="Manager",
        status="pending",
        priority=1
    )
    await agent.add_task(task)
    
    stored_task = await agent.get_task(task.id)
    assert stored_task is not None
    assert not contains_sensitive_info(stored_task.title)
    assert not contains_sensitive_info(stored_task.description)

@pytest.mark.asyncio
async def test_no_sensitive_info_in_events(agent):
    """Test that events don't contain sensitive information."""
    event = Event(
        id="test-event",
        title="Team Meeting",
        type="meeting",
        date=datetime.now(),
        venue="Office",
        capacity=10,
        budget=1000.0,
        status="scheduled"
    )
    await agent.add_event(event)
    
    stored_event = await agent.get_event(event.id)
    assert stored_event is not None
    assert not contains_sensitive_info(stored_event.title)
    assert not contains_sensitive_info(stored_event.venue)

@pytest.mark.asyncio
async def test_no_sensitive_info_in_contracts(agent):
    """Test that contracts don't contain sensitive information."""
    contract = Contract(
        id="test-contract",
        title="Agreement",
        parties=["Artist", "Manager"],
        terms={
            "rate": 1000,
            "details": "Standard terms"
        },
        status="active",
        value=1000.0,
        expiration=datetime.now() + timedelta(days=30)
    )
    await agent.add_contract(contract)
    
    stored_contract = await agent.get_contract(contract.id)
    assert stored_contract is not None
    assert not any(contains_sensitive_info(str(value)) for value in stored_contract.terms.values())

@pytest.mark.asyncio
async def test_financial_record_amount_validation(agent):
    """Test that financial records validate amount ranges."""
    record = FinancialRecord(
        id="test-record",
        date=datetime.now(),
        type="expense",
        amount=-1000.0,  # Negative amount
        currency="USD",
        category="marketing",
        description="Marketing expenses"
    )
    with pytest.raises(ValueError, match="Amount cannot be negative"):
        await agent.add_financial_record(record)

@pytest.mark.asyncio
async def test_input_sanitization(agent):
    """Test that inputs are properly sanitized."""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "<script>alert('xss')</script>",
        "${system('rm -rf /')}",
        "{{7*7}}",
        "|ls -la|",
        "\x00\x1f\x7f",  # Control characters
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4="
    ]
    
    for input_str in malicious_inputs:
        task = Task(
            title=input_str,
            description="Test task",
            deadline=datetime.now() + timedelta(days=1),
            assigned_to="Manager",
            status="pending",
            priority=1
        )
        
        with pytest.raises(Exception) as exc_info:
            await agent.add_task(task)
        assert "contains invalid characters" in str(exc_info.value)

@pytest.mark.asyncio
async def test_rate_limiting(agent):
    """Test that rate limiting is enforced."""
    start_time = datetime.now()
    
    # Try to create 100 tasks rapidly
    for i in range(100):
        task = Task(
            title=f"Task {i}",
            description="Test task",
            deadline=datetime.now() + timedelta(days=1),
            assigned_to="Manager",
            status="pending",
            priority=1
        )
        await agent.add_task(task)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Should take at least 2 seconds due to rate limiting (100 tasks * 0.02s)
    assert duration >= 2.0

@pytest.mark.asyncio
async def test_data_encryption(agent):
    """Test that sensitive data is encrypted."""
    contract = Contract(
        id="test-contract-123",
        title="Confidential Agreement",
        parties=["Artist", "Manager"],
        terms={
            "rate": 1000,
            "confidential": True
        },
        status="active",
        value=10000.0,
        expiration=datetime.now() + timedelta(days=30)
    )
    
    await agent.add_contract(contract)
    
    # Get raw data from storage
    raw_data = agent._get_raw_contract_data(contract.id)
    
    # Verify that sensitive fields are encrypted
    assert "terms" not in raw_data
    assert "value" not in raw_data
    assert "encrypted_data" in raw_data

@pytest.mark.asyncio
async def test_access_control(agent):
    """Test that access control is properly enforced."""
    # Create a task with restricted access
    task = Task(
        title="Confidential Task",
        description="Sensitive information",
        deadline=datetime.now() + timedelta(days=1),
        assigned_to="Manager",
        status="pending",
        priority=1,
        access_level="restricted"
    )
    
    await agent.add_task(task)
    
    # Try to access with insufficient privileges
    with pytest.raises(Exception) as exc_info:
        await agent.get_task(task.id, access_level="public")
    assert "Insufficient privileges" in str(exc_info.value)

@pytest.mark.asyncio
async def test_audit_logging(agent):
    """Test that all sensitive operations are logged."""
    start_time = datetime.now() - timedelta(minutes=5)
    
    # Perform various operations
    task = Task(
        title="Test Task",
        description="Test description",
        deadline=datetime.now() + timedelta(days=1),
        assigned_to="Manager",
        status="pending",
        priority=1
    )
    
    # Test task operations
    await agent.add_task(task)
    task.status = "completed"
    await agent.update_task(task)
    await agent.delete_task(task.id)
    
    # Test financial operations
    record = FinancialRecord(
        id="test-record",
        date=datetime.now(),
        type="income",
        amount=1000.0,
        currency="USD",
        category="performance",
        description="Test Record"
    )
    await agent.add_financial_record(record)
    
    # Get audit logs
    end_time = datetime.now() + timedelta(minutes=5)
    logs = await agent.get_audit_logs(start_time, end_time)
    
    # Verify all operations were logged
    assert len(logs) >= 4  # At least create, update, delete for task and create for financial record
    
    # Verify log structure and event types
    task_created_log = next(log for log in logs if log["event_type"] == "task_created")
    assert task_created_log["details"]["task_id"] == task.id
    assert task_created_log["details"]["operation"] == "create"
    assert "timestamp" in task_created_log
    
    task_updated_log = next(log for log in logs if log["event_type"] == "task_updated")
    assert task_updated_log["details"]["task_id"] == task.id
    assert task_updated_log["details"]["operation"] == "update"
    
    task_deleted_log = next(log for log in logs if log["event_type"] == "task_deleted")
    assert task_deleted_log["details"]["task_id"] == task.id
    assert task_deleted_log["details"]["operation"] == "delete"
    
    financial_created_log = next(log for log in logs if log["event_type"] == "financial_record_created")
    assert financial_created_log["details"]["financial_record_id"] == record.id
    assert financial_created_log["details"]["operation"] == "create"
    
    # Test filtering by event type
    task_logs = await agent.get_audit_logs(start_time, end_time, event_type="task_created")
    assert len(task_logs) == 1
    assert task_logs[0]["event_type"] == "task_created" 