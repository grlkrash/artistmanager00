import pytest
from datetime import datetime, timedelta
from artist_manager_agent.agent import ArtistManagerAgent, ArtistProfile, Contract, Task, Event, FinancialRecord

@pytest.fixture
def agent(profile):
    """Create a test agent with the test profile."""
    return ArtistManagerAgent(
        artist_profile=profile,
        openai_api_key="test-key-123",
        model="gpt-3.5-turbo",
        db_url="sqlite:///test.db",
        telegram_token="test-telegram-token",
        ai_mastering_key="test-mastering-key"
    )

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
async def test_add_contract(agent):
    """Test adding a new contract."""
    contract = Contract(
        id="test-contract-123",
        title="Test Contract",
        description="A test contract",
        parties=["Artist", "Venue"],
        terms={"term1": "value1", "term2": "value2"},
        value=1000.0,
        status="pending",
        expiration=datetime.now() + timedelta(days=30),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    result = await agent.add_contract(contract)
    assert result is not None
    assert result.id == contract.id

@pytest.mark.asyncio
async def test_update_contract(agent):
    """Test updating an existing contract."""
    contract = Contract(
        id="test-contract-123",
        title="Test Contract",
        description="A test contract",
        parties=["Artist", "Venue"],
        terms={"term1": "value1", "term2": "value2"},
        value=1000.0,
        status="pending",
        expiration=datetime.now() + timedelta(days=30),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_contract(contract)
    
    contract.status = "active"
    result = await agent.update_contract(contract)
    assert result is not None
    assert result.status == "active"

@pytest.mark.asyncio
async def test_add_task(agent):
    """Test adding a new task."""
    task = Task(
        id="test-task-123",
        title="Test Task",
        description="A test task",
        deadline=datetime.now() + timedelta(days=7),
        assigned_to="Test User",
        status="pending",
        priority=1,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    result = await agent.add_task(task)
    assert result is not None
    assert result.id == task.id

@pytest.mark.asyncio
async def test_update_task(agent):
    """Test updating an existing task."""
    task = Task(
        id="test-task-123",
        title="Test Task",
        description="A test task",
        deadline=datetime.now() + timedelta(days=7),
        assigned_to="Test User",
        status="pending",
        priority=1,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_task(task)
    
    task.status = "completed"
    result = await agent.update_task(task)
    assert result is not None
    assert result.status == "completed"

@pytest.mark.asyncio
async def test_add_event(agent):
    """Test adding a new event."""
    event = Event(
        id="test-event-123",
        title="Test Event",
        type="concert",
        date=datetime.now() + timedelta(days=30),
        venue="Test Venue",
        capacity=100,
        budget=1000.0,
        status="scheduled",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    result = await agent.add_event(event)
    assert result is not None
    assert result.id == event.id

@pytest.mark.asyncio
async def test_update_event(agent):
    """Test updating an existing event."""
    event = Event(
        id="test-event-123",
        title="Test Event",
        type="concert",
        date=datetime.now() + timedelta(days=30),
        venue="Test Venue",
        capacity=100,
        budget=1000.0,
        status="scheduled",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_event(event)
    
    event.status = "cancelled"
    result = await agent.update_event(event)
    assert result is not None
    assert result.status == "cancelled"

@pytest.mark.asyncio
async def test_add_financial_record(agent):
    """Test adding a new financial record."""
    record = FinancialRecord(
        id="test-record-123",
        date=datetime.now(),
        type="income",
        amount=1000.0,
        currency="USD",
        category="performance",
        description="A test financial record",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_financial_record(record)
    records = await agent.get_financial_records()
    assert len(records) == 1
    assert records[0].id == "test-record-123"

@pytest.mark.asyncio
async def test_update_financial_record(agent):
    """Test updating an existing financial record."""
    record = FinancialRecord(
        id="test-record-123",
        date=datetime.now(),
        type="income",
        amount=1000.0,
        currency="USD",
        category="performance",
        description="A test financial record",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await agent.add_financial_record(record)
    record.amount = 2000.0
    await agent.update_financial_record(record)
    records = await agent.get_financial_records()
    assert len(records) == 1
    assert records[0].amount == 2000.0

@pytest.mark.asyncio
async def test_get_financial_report(agent):
    """Test getting a financial report."""
    # Add some test records
    records = [
        FinancialRecord(
            id=f"record_{i}",
            date=datetime.now(),
            type="income" if i % 2 == 0 else "expense",
            amount=1000.0,
            currency="USD",
            category="performance",
            description=f"Test record {i}"
        )
        for i in range(5)
    ]
    for record in records:
        await agent.add_financial_record(record)
    
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    
    report = await agent.generate_financial_report(start_date, end_date)
    assert report is not None
    assert "total_income" in report
    assert "total_expenses" in report
    assert "net_profit" in report

@pytest.mark.asyncio
async def test_get_task_report(agent):
    """Test getting a task report."""
    # Add some test tasks
    tasks = [
        Task(
            id=f"task_{i}",
            title=f"Test Task {i}",
            description=f"Test description {i}",
            deadline=datetime.now() + timedelta(days=i),
            assigned_to="Manager",
            status="pending" if i % 2 == 0 else "completed",
            priority=i % 3 + 1
        )
        for i in range(5)
    ]
    
    for task in tasks:
        await agent.add_task(task)
    
    tasks = await agent.get_tasks()
    assert len(tasks) == 5
    assert all(isinstance(task, Task) for task in tasks)

@pytest.mark.asyncio
async def test_get_event_report(agent):
    """Test getting an event report."""
    # Add some test events
    events = [
        Event(
            id=f"event_{i}",
            title=f"Test Event {i}",
            type="concert",
            date=datetime.now() + timedelta(days=i * 7),
            venue=f"Test Venue {i}",
            capacity=1000,
            budget=5000.0,
            status="scheduled" if i % 2 == 0 else "completed"
        )
        for i in range(5)
    ]
    
    for event in events:
        await agent.add_event(event)
    
    start_date = datetime.now()
    end_date = datetime.now() + timedelta(days=30)
    
    events = await agent.get_events_in_range(start_date, end_date)
    assert len(events) > 0
    assert all(isinstance(event, Event) for event in events) 