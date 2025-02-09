import pytest
from datetime import datetime, timedelta
from artist_manager_agent.agent import (
    ArtistManagerAgent,
    FinancialRecord
)
from artist_manager_agent.models import ArtistProfile

@pytest.fixture
def agent():
    artist_profile = ArtistProfile(
        id="test-artist",
        name="Test Artist",
        genre="Pop",
        genres=["pop", "rock"],
        career_stage="Emerging",
        goals=["Increase streaming numbers", "Book more live shows"],
        strengths=["Vocal ability", "Stage presence"],
        areas_for_improvement=["Marketing", "Networking"],
        achievements=["Released debut EP", "100k streams"],
        social_media={"instagram": "@test", "twitter": "@test"},
        streaming_profiles={"spotify": "test_url", "apple": "test_url"},
        brand_guidelines={
            "colors": ["#000000", "#FFFFFF"],
            "fonts": ["Helvetica", "Arial"],
            "tone": "Professional"
        },
        email="test@example.com"
    )
    return ArtistManagerAgent(
        artist_profile=artist_profile,
        openai_api_key="test_key",
        model="gpt-3.5-turbo",
        db_url="sqlite:///:memory:"
    )

@pytest.fixture
def sample_income():
    return FinancialRecord(
        id="test-income",
        date=datetime.now(),
        type="income",
        amount=1000.0,
        currency="USD",
        category="performance",
        description="Test income record",
        status="completed"
    )

@pytest.fixture
def sample_expense():
    return FinancialRecord(
        id="test-expense",
        date=datetime.now(),
        type="expense",
        amount=500.0,
        currency="USD",
        category="marketing",
        description="Test expense record",
        status="completed"
    )

@pytest.mark.asyncio
async def test_add_financial_record(agent, sample_income):
    """Test adding a financial record."""
    await agent.add_financial_record(sample_income)
    records = await agent.get_financial_records()
    assert len(records) == 1
    assert records[0].id == "test-income"

@pytest.mark.asyncio
async def test_update_financial_record(agent, sample_income):
    """Test updating a financial record."""
    await agent.add_financial_record(sample_income)
    updated_record = sample_income.copy()
    updated_record.status = "pending"
    await agent.update_financial_record(updated_record)
    records = await agent.get_financial_records()
    assert records[0].status == "pending"

@pytest.mark.asyncio
async def test_cash_flow_analysis(agent, sample_income, sample_expense):
    """Test cash flow analysis."""
    # Add income and expense records
    await agent.add_financial_record(sample_income)
    await agent.add_financial_record(sample_expense)
    
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    
    analysis = await agent.get_cash_flow_analysis(start_date, end_date)
    assert analysis["income"] == 1000.0
    assert analysis["expenses"] == 500.0
    assert analysis["net_cash_flow"] == 500.0

@pytest.mark.asyncio
async def test_get_financial_report(agent, sample_income, sample_expense):
    """Test generating a financial report."""
    await agent.add_financial_record(sample_income)
    await agent.add_financial_record(sample_expense)
    
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    
    report = await agent.get_financial_report(start_date, end_date)
    assert report["total_income"] == 1000.0
    assert report["total_expenses"] == 500.0
    assert report["income_by_category"]["performance"] == 1000.0
    assert report["expenses_by_category"]["marketing"] == 500.0

@pytest.mark.asyncio
async def test_get_monthly_summary(agent, sample_income, sample_expense):
    """Test generating a monthly financial summary."""
    await agent.add_financial_record(sample_income)
    await agent.add_financial_record(sample_expense)
    
    current_month = datetime.now().replace(day=1)
    summary = await agent.get_monthly_summary(current_month)
    assert summary["total_income"] == 1000.0
    assert summary["total_expenses"] == 500.0
    assert summary["period_start"] == current_month
    assert summary["period_end"] == (current_month.replace(month=current_month.month + 1) - timedelta(days=1)) if current_month.month < 12 else current_month.replace(year=current_month.year + 1, month=1, day=1) - timedelta(days=1) 