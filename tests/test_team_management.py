import pytest
from datetime import datetime, timedelta
from artist_manager_agent.team_management import (
    TeamManager,
    CollaboratorProfile,
    CollaboratorRole,
    Project,
    FinancialTransaction,
    BudgetCategory,
    BudgetAllocation
)

@pytest.fixture
def team_manager():
    return TeamManager()

@pytest.fixture
def sample_collaborator():
    return CollaboratorProfile(
        name="John Doe",
        role=CollaboratorRole.PRODUCER,
        expertise=["Music Production", "Mixing"],
        rate=100.0,
        currency="USD",
        location="New York",
        availability={
            "monday": ["09:00-17:00"],
            "wednesday": ["09:00-17:00"],
            "friday": ["09:00-17:00"]
        }
    )

@pytest.fixture
def sample_project():
    return Project(
        name="Album Production",
        description="Produce debut album",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=90),
        budget=10000.0,
        deliverables=["10 tracks", "Album artwork", "Credits document"]
    )

@pytest.fixture
def sample_transaction():
    return FinancialTransaction(
        amount=1000.0,
        category=BudgetCategory.PRODUCTION,
        description="Studio time",
        transaction_type="expense",
        tax_category="business_expense"
    )

@pytest.fixture
def sample_budget_allocation():
    return BudgetAllocation(
        category=BudgetCategory.PRODUCTION,
        amount=5000.0,
        period_start=datetime.now(),
        period_end=datetime.now() + timedelta(days=90)
    )

@pytest.mark.asyncio
async def test_add_collaborator(team_manager, sample_collaborator):
    """Test adding a collaborator to the team."""
    collaborator_id = await team_manager.add_collaborator(sample_collaborator)
    assert collaborator_id is not None
    assert collaborator_id in team_manager.collaborators
    assert team_manager.collaborators[collaborator_id].name == "John Doe"

@pytest.mark.asyncio
async def test_update_collaborator(team_manager, sample_collaborator):
    """Test updating collaborator information."""
    collaborator_id = await team_manager.add_collaborator(sample_collaborator)
    updates = {"rate": 150.0, "location": "Los Angeles"}
    updated = await team_manager.update_collaborator(collaborator_id, updates)
    assert updated is not None
    assert updated.rate == 150.0
    assert updated.location == "Los Angeles"

@pytest.mark.asyncio
async def test_create_project(team_manager, sample_project):
    """Test creating a new project."""
    project_id = await team_manager.create_project(sample_project)
    assert project_id is not None
    assert project_id in team_manager.projects
    assert team_manager.projects[project_id].name == "Album Production"

@pytest.mark.asyncio
async def test_assign_to_project(team_manager, sample_collaborator, sample_project):
    """Test assigning a collaborator to a project."""
    collaborator_id = await team_manager.add_collaborator(sample_collaborator)
    project_id = await team_manager.create_project(sample_project)
    
    success = await team_manager.assign_to_project(project_id, collaborator_id)
    assert success is True
    assert collaborator_id in team_manager.projects[project_id].team_members

@pytest.mark.asyncio
async def test_get_team_analytics(team_manager, sample_collaborator, sample_project):
    """Test team analytics generation."""
    await team_manager.add_collaborator(sample_collaborator)
    await team_manager.create_project(sample_project)
    
    analytics = await team_manager.get_team_analytics()
    assert analytics["total_collaborators"] == 1
    assert analytics["total_projects"] == 1
    assert "producer" in analytics["role_distribution"]
    assert analytics["role_distribution"]["producer"] == 1

@pytest.mark.asyncio
async def test_get_project_analytics(team_manager, sample_collaborator, sample_project):
    """Test project analytics generation."""
    collaborator_id = await team_manager.add_collaborator(sample_collaborator)
    project_id = await team_manager.create_project(sample_project)
    await team_manager.assign_to_project(project_id, collaborator_id)
    
    analytics = await team_manager.get_project_analytics(project_id)
    assert analytics["project_name"] == "Album Production"
    assert analytics["team_size"] == 1
    assert "producer" in analytics["role_distribution"]
    assert analytics["role_distribution"]["producer"] == 1

@pytest.mark.asyncio
async def test_get_collaborator_performance(team_manager, sample_collaborator, sample_project):
    """Test collaborator performance metrics."""
    collaborator_id = await team_manager.add_collaborator(sample_collaborator)
    project_id = await team_manager.create_project(sample_project)
    await team_manager.assign_to_project(project_id, collaborator_id)
    
    performance = await team_manager.get_collaborator_performance(collaborator_id)
    assert performance["name"] == "John Doe"
    assert performance["role"] == "producer"
    assert performance["projects"]["total"] == 1
    assert performance["projects"]["active"] == 1

@pytest.mark.asyncio
async def test_find_common_availability(team_manager):
    """Test finding common availability slots."""
    collaborator1 = CollaboratorProfile(
        name="John Doe",
        role=CollaboratorRole.PRODUCER,
        expertise=["Music Production"],
        availability={"monday": ["09:00-17:00"]}
    )
    collaborator2 = CollaboratorProfile(
        name="Jane Smith",
        role=CollaboratorRole.ENGINEER,
        expertise=["Sound Engineering"],
        availability={"monday": ["10:00-18:00"]}
    )
    
    id1 = await team_manager.add_collaborator(collaborator1)
    id2 = await team_manager.add_collaborator(collaborator2)
    
    # Test for Monday
    monday = datetime.strptime("2024-02-12", "%Y-%m-%d")  # A Monday
    common_slots = await team_manager.find_common_availability([id1, id2], monday)
    
    # The common availability should be 10:00-17:00 (intersection of 09:00-17:00 and 10:00-18:00)
    assert len(common_slots) == 1
    start_time, end_time = common_slots[0].split("-")
    assert start_time == "10:00"  # Latest start time
    assert end_time == "17:00"    # Earliest end time

@pytest.mark.asyncio
async def test_generate_team_report(team_manager, sample_collaborator, sample_project):
    """Test team report generation."""
    await team_manager.add_collaborator(sample_collaborator)
    await team_manager.create_project(sample_project)
    
    report = await team_manager.generate_team_report()
    assert "Team Status Report" in report
    assert "Total Collaborators: 1" in report
    assert "Total Projects: 1" in report
    assert "producer" in report.lower()

@pytest.mark.asyncio
async def test_remove_collaborator(team_manager, sample_collaborator, sample_project):
    """Test removing a collaborator."""
    collaborator_id = await team_manager.add_collaborator(sample_collaborator)
    project_id = await team_manager.create_project(sample_project)
    await team_manager.assign_to_project(project_id, collaborator_id)
    
    success = await team_manager.remove_collaborator(collaborator_id)
    assert success is True
    assert collaborator_id not in team_manager.collaborators
    assert collaborator_id not in team_manager.projects[project_id].team_members

@pytest.mark.asyncio
async def test_get_project_team(team_manager, sample_collaborator, sample_project):
    """Test getting project team members."""
    collaborator_id = await team_manager.add_collaborator(sample_collaborator)
    project_id = await team_manager.create_project(sample_project)
    await team_manager.assign_to_project(project_id, collaborator_id)
    
    team = await team_manager.get_project_team(project_id)
    assert len(team) == 1
    assert team[0].name == "John Doe"
    assert team[0].role == CollaboratorRole.PRODUCER 

@pytest.mark.asyncio
async def test_record_transaction(team_manager, sample_transaction):
    """Test recording a financial transaction."""
    transaction_id = await team_manager.record_transaction(sample_transaction)
    assert transaction_id is not None
    assert transaction_id in team_manager.transactions
    assert team_manager.transactions[transaction_id].amount == 1000.0
    assert team_manager.transactions[transaction_id].category == BudgetCategory.PRODUCTION

@pytest.mark.asyncio
async def test_set_project_budget(team_manager, sample_project, sample_budget_allocation):
    """Test setting project budget allocations."""
    project_id = await team_manager.create_project(sample_project)
    success = await team_manager.set_project_budget(project_id, [sample_budget_allocation])
    assert success is True
    assert project_id in team_manager.budget_allocations
    assert team_manager.budget_allocations[project_id][0].amount == 5000.0
    assert team_manager.projects[project_id].budget == 5000.0

@pytest.mark.asyncio
async def test_get_financial_report(team_manager, sample_transaction, sample_project):
    """Test generating a financial report."""
    # Add transaction and project
    project_id = await team_manager.create_project(sample_project)
    sample_transaction.project_id = project_id
    await team_manager.record_transaction(sample_transaction)
    
    # Generate report
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    report = await team_manager.get_financial_report(start_date, end_date)
    
    assert report["summary"]["total_expenses"] == 1000.0
    assert "production" in report["by_category"]
    assert report["by_category"]["production"]["expenses"] == 1000.0
    assert project_id in report["by_project"]
    assert report["by_project"][project_id]["expenses"] == 1000.0

@pytest.mark.asyncio
async def test_get_tax_report(team_manager, sample_transaction):
    """Test generating a tax report."""
    # Add transaction
    await team_manager.record_transaction(sample_transaction)
    
    # Generate tax report for current year
    current_year = datetime.now().year
    tax_report = await team_manager.get_tax_report(current_year)
    
    assert tax_report["year"] == current_year
    assert tax_report["total_expenses"] == 1000.0
    assert tax_report["deductible_expenses"] == 1000.0
    assert "production" in tax_report["expense_categories"]
    assert tax_report["expense_categories"]["production"] == 1000.0

@pytest.mark.asyncio
async def test_budget_tracking(team_manager, sample_project, sample_budget_allocation, sample_transaction):
    """Test budget tracking and reporting."""
    # Create project with budget
    project_id = await team_manager.create_project(sample_project)
    await team_manager.set_project_budget(project_id, [sample_budget_allocation])
    
    # Add expense transaction
    sample_transaction.project_id = project_id
    await team_manager.record_transaction(sample_transaction)
    
    # Get financial report
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    report = await team_manager.get_financial_report(start_date, end_date)
    
    # Check budget vs actual
    assert report["by_category"]["production"]["budget"] == 5000.0
    assert report["by_category"]["production"]["expenses"] == 1000.0
    assert report["by_category"]["production"]["remaining"] == 4000.0

@pytest.mark.asyncio
async def test_collaborator_payment_tracking(team_manager, sample_collaborator, sample_transaction):
    """Test tracking payments to collaborators."""
    # Add collaborator
    collaborator_id = await team_manager.add_collaborator(sample_collaborator)
    
    # Add payment transaction
    sample_transaction.collaborator_id = collaborator_id
    sample_transaction.payment_id = "payment123"
    await team_manager.record_transaction(sample_transaction)
    
    # Get tax report
    current_year = datetime.now().year
    tax_report = await team_manager.get_tax_report(current_year)
    
    # Check collaborator payments
    assert collaborator_id in tax_report["collaborator_payments"]
    assert tax_report["collaborator_payments"][collaborator_id]["name"] == "John Doe"
    assert tax_report["collaborator_payments"][collaborator_id]["total_paid"] == 1000.0
    assert "payment123" in tax_report["collaborator_payments"][collaborator_id]["payment_ids"] 