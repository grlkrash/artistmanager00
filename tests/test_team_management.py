import pytest
from datetime import datetime, timedelta
from artist_manager_agent.agent import (
    ArtistManagerAgent,
    Contract,
    Event,
    FinancialRecord,
    Task
)

@pytest.fixture
def agent():
    return ArtistManagerAgent()

@pytest.fixture
def sample_contract():
    return Contract(
        contract_id="contract_1",
        title="Producer Agreement",
        parties=["Artist", "John Doe"],
        terms="Music production services for upcoming album",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=90),
        value=10000.0,
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def sample_task():
    return Task(
        task_id="task_1",
        title="Album Production",
        description="Produce debut album",
        assigned_to="John Doe",
        due_date=datetime.now() + timedelta(days=90),
        priority="high",
        status="in_progress",
        dependencies=["Track recording", "Mixing", "Mastering"],
        notes=["Focus on maintaining consistent sound"],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def sample_event():
    return Event(
        event_id="event_1",
        title="Production Meeting",
        description="Weekly production status meeting",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        location="Studio A",
        attendees=["Artist", "John Doe"],
        status="scheduled",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def sample_financial_record():
    return FinancialRecord(
        record_id="finance_1",
        type="expense",
        amount=1000.0,
        description="Studio time payment",
        date=datetime.now(),
        category="studio_expenses",
        status="completed",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.mark.asyncio
async def test_add_contract(agent, sample_contract):
    """Test adding a contract."""
    await agent.add_contract(sample_contract)
    contracts = await agent.get_contracts()
    assert len(contracts) == 1
    assert contracts[0].contract_id == "contract_1"
    assert contracts[0].title == "Producer Agreement"

@pytest.mark.asyncio
async def test_update_contract(agent, sample_contract):
    """Test updating contract information."""
    await agent.add_contract(sample_contract)
    updated_contract = sample_contract.copy()
    updated_contract.status = "completed"
    await agent.update_contract(updated_contract)
    contracts = await agent.get_contracts()
    assert contracts[0].status == "completed"

@pytest.mark.asyncio
async def test_add_task(agent, sample_task):
    """Test adding a task."""
    await agent.add_task(sample_task)
    tasks = await agent.get_tasks()
    assert len(tasks) == 1
    assert tasks[0].task_id == "task_1"
    assert tasks[0].title == "Album Production"

@pytest.mark.asyncio
async def test_update_task(agent, sample_task):
    """Test updating task status."""
    await agent.add_task(sample_task)
    updated_task = sample_task.copy()
    updated_task.status = "completed"
    await agent.update_task(updated_task)
    tasks = await agent.get_tasks()
    assert tasks[0].status == "completed"

@pytest.mark.asyncio
async def test_add_event(agent, sample_event):
    """Test adding an event."""
    await agent.add_event(sample_event)
    events = await agent.get_events()
    assert len(events) == 1
    assert events[0].event_id == "event_1"
    assert events[0].title == "Production Meeting"

@pytest.mark.asyncio
async def test_update_event(agent, sample_event):
    """Test updating event status."""
    await agent.add_event(sample_event)
    updated_event = sample_event.copy()
    updated_event.status = "completed"
    await agent.update_event(updated_event)
    events = await agent.get_events()
    assert events[0].status == "completed"

@pytest.mark.asyncio
async def test_add_financial_record(agent, sample_financial_record):
    """Test adding a financial record."""
    await agent.add_financial_record(sample_financial_record)
    records = await agent.get_financial_records()
    assert len(records) == 1
    assert records[0].record_id == "finance_1"
    assert records[0].amount == 1000.0

@pytest.mark.asyncio
async def test_get_financial_report(agent, sample_financial_record):
    """Test generating a financial report."""
    await agent.add_financial_record(sample_financial_record)
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    report = await agent.get_financial_report(start_date, end_date)
    assert report["total_expenses"] == 1000.0
    assert report["categories"]["studio_expenses"] == 1000.0

@pytest.mark.asyncio
async def test_get_task_report(agent, sample_task):
    """Test generating a task report."""
    await agent.add_task(sample_task)
    report = await agent.get_task_report()
    assert report["total_tasks"] == 1
    assert report["by_status"]["in_progress"] == 1
    assert report["by_priority"]["high"] == 1

@pytest.mark.asyncio
async def test_get_event_report(agent, sample_event):
    """Test generating an event report."""
    await agent.add_event(sample_event)
    report = await agent.get_event_report()
    assert report["total_events"] == 1
    assert report["by_status"]["scheduled"] == 1 