import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import statistics

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

class PerformanceMetrics:
    """Track performance metrics."""
    def __init__(self):
        self.operation_times: Dict[str, List[float]] = {}
        self.memory_usage: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
    
    def add_operation_time(self, operation: str, duration: float):
        if operation not in self.operation_times:
            self.operation_times[operation] = []
        self.operation_times[operation].append(duration)
    
    def add_memory_usage(self, operation: str, usage: float):
        if operation not in self.memory_usage:
            self.memory_usage[operation] = []
        self.memory_usage[operation].append(usage)
    
    def increment_error_count(self, operation: str):
        self.error_counts[operation] = self.error_counts.get(operation, 0) + 1
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        times = self.operation_times.get(operation, [])
        memory = self.memory_usage.get(operation, [])
        errors = self.error_counts.get(operation, 0)
        
        if not times:
            return {}
        
        return {
            "avg_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev_time": statistics.stdev(times) if len(times) > 1 else 0,
            "avg_memory": statistics.mean(memory) if memory else 0,
            "error_count": errors,
            "total_operations": len(times),
            "success_rate": (len(times) - errors) / len(times) * 100
        }

async def measure_operation_time(operation_name: str, metrics: PerformanceMetrics, operation):
    """Measure the time taken by an operation."""
    start_time = time.time()
    try:
        result = await operation()
        duration = time.time() - start_time
        metrics.add_operation_time(operation_name, duration)
        return result
    except Exception as e:
        metrics.increment_error_count(operation_name)
        raise e

@pytest.mark.asyncio
async def test_task_operation_performance(agent):
    """Test performance of task operations."""
    metrics = PerformanceMetrics()
    operations = 1000
    
    # Test task creation performance
    for i in range(operations):
        task = Task(
            id=f"task-{i}",
            title=f"Performance Test Task {i}",
            description="Test task",
            deadline=datetime.now() + timedelta(days=1),
            assigned_to="Manager",
            status="pending",
            priority=1
        )
        await measure_operation_time(
            "task_creation",
            metrics,
            lambda: agent.add_task(task)
        )
    
    # Test task retrieval performance
    tasks = await agent.get_tasks()
    for task in tasks[:100]:  # Test first 100 tasks
        await measure_operation_time(
            "task_retrieval",
            metrics,
            lambda: agent.get_task(task.id)
        )
    
    # Test task update performance
    for task in tasks[:100]:
        task.status = "completed"
        await measure_operation_time(
            "task_update",
            metrics,
            lambda: agent.update_task(task)
        )
    
    # Verify performance metrics
    creation_stats = metrics.get_stats("task_creation")
    retrieval_stats = metrics.get_stats("task_retrieval")
    update_stats = metrics.get_stats("task_update")
    
    # Assert performance requirements
    assert creation_stats["avg_time"] < 0.1  # Average creation under 100ms
    assert retrieval_stats["avg_time"] < 0.05  # Average retrieval under 50ms
    assert update_stats["avg_time"] < 0.1  # Average update under 100ms
    assert creation_stats["success_rate"] > 99.0  # 99% success rate
    assert retrieval_stats["success_rate"] > 99.0
    assert update_stats["success_rate"] > 99.0

@pytest.mark.asyncio
async def test_event_operation_performance(agent):
    """Test performance of event operations."""
    metrics = PerformanceMetrics()
    operations = 1000
    
    # Test event creation performance
    for i in range(operations):
        event = Event(
            id=f"event-{i}",
            title=f"Performance Test Event {i}",
            type="test",
            date=datetime.now() + timedelta(days=i % 30),
            venue="Test Venue",
            capacity=100,
            budget=1000.0,
            status="scheduled"
        )
        await measure_operation_time(
            "event_creation",
            metrics,
            lambda: agent.add_event(event)
        )
    
    # Test event search performance
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    for _ in range(100):
        await measure_operation_time(
            "event_search",
            metrics,
            lambda: agent.get_events_in_range(start_date, end_date)
        )
    
    # Verify performance metrics
    creation_stats = metrics.get_stats("event_creation")
    search_stats = metrics.get_stats("event_search")
    
    # Assert performance requirements
    assert creation_stats["avg_time"] < 0.1
    assert search_stats["avg_time"] < 0.2
    assert creation_stats["success_rate"] > 99.0
    assert search_stats["success_rate"] > 99.0

@pytest.mark.asyncio
async def test_financial_operation_performance(agent):
    """Test performance of financial operations."""
    metrics = PerformanceMetrics()
    operations = 1000
    
    # Test financial record creation performance
    for i in range(operations):
        record = FinancialRecord(
            id=f"record-{i}",
            date=datetime.now(),
            type="test",
            amount=100.0,
            category="test",
            description=f"Performance Test Record {i}"
        )
        await measure_operation_time(
            "financial_creation",
            metrics,
            lambda: agent.add_financial_record(record)
        )
    
    # Test financial report generation performance
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    for _ in range(100):
        await measure_operation_time(
            "financial_report",
            metrics,
            lambda: agent.generate_financial_report(start_date, end_date)
        )
    
    # Verify performance metrics
    creation_stats = metrics.get_stats("financial_creation")
    report_stats = metrics.get_stats("financial_report")
    
    # Assert performance requirements
    assert creation_stats["avg_time"] < 0.1
    assert report_stats["avg_time"] < 0.5
    assert creation_stats["success_rate"] > 99.0
    assert report_stats["success_rate"] > 99.0

@pytest.mark.asyncio
async def test_concurrent_operation_performance(agent):
    """Test performance under concurrent operations."""
    metrics = PerformanceMetrics()
    operations = 100
    
    async def concurrent_operations():
        # Create a mix of operations
        task = Task(
            id="concurrent-task",
            title="Concurrent Test Task",
            description="Test task",
            deadline=datetime.now() + timedelta(days=1),
            assigned_to="Manager",
            status="pending",
            priority=1
        )
        
        event = Event(
            id="concurrent-event",
            title="Concurrent Test Event",
            type="test",
            date=datetime.now(),
            venue="Test Venue",
            capacity=100,
            budget=1000.0,
            status="scheduled"
        )
        
        record = FinancialRecord(
            id="concurrent-record",
            date=datetime.now(),
            type="test",
            amount=100.0,
            category="test",
            description="Concurrent Test Record"
        )
        
        # Execute operations concurrently
        await asyncio.gather(
            measure_operation_time(
                "concurrent_task",
                metrics,
                lambda: agent.add_task(task)
            ),
            measure_operation_time(
                "concurrent_event",
                metrics,
                lambda: agent.add_event(event)
            ),
            measure_operation_time(
                "concurrent_financial",
                metrics,
                lambda: agent.add_financial_record(record)
            )
        )
    
    # Run concurrent operations
    await asyncio.gather(
        *[concurrent_operations() for _ in range(operations)]
    )
    
    # Verify performance metrics
    task_stats = metrics.get_stats("concurrent_task")
    event_stats = metrics.get_stats("concurrent_event")
    financial_stats = metrics.get_stats("concurrent_financial")
    
    # Assert performance requirements
    assert task_stats["avg_time"] < 0.2
    assert event_stats["avg_time"] < 0.2
    assert financial_stats["avg_time"] < 0.2
    assert task_stats["success_rate"] > 95.0
    assert event_stats["success_rate"] > 95.0
    assert financial_stats["success_rate"] > 95.0 