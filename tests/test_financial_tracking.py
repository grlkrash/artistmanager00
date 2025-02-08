import pytest
from datetime import datetime, timedelta
from artist_manager_agent.agent import (
    ArtistManagerAgent,
    FinancialRecord
)

@pytest.fixture
def agent():
    return ArtistManagerAgent()

@pytest.fixture
def sample_income():
    return FinancialRecord(
        record_id="finance_1",
        type="income",
        amount=1000.0,
        description="Streaming revenue",
        date=datetime.now(),
        category="streaming_revenue",
        status="completed",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def sample_expense():
    return FinancialRecord(
        record_id="finance_2",
        type="expense",
        amount=500.0,
        description="Studio time",
        date=datetime.now(),
        category="studio_expenses",
        status="completed",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.mark.asyncio
async def test_add_financial_record(agent, sample_income):
    """Test adding a financial record."""
    await agent.add_financial_record(sample_income)
    records = await agent.get_financial_records()
    assert len(records) == 1
    assert records[0].record_id == "finance_1"
    assert records[0].amount == 1000.0

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
    assert analysis["net_cash_flow"] == 500.0  # 1000 income - 500 expense
    assert analysis["income"]["streaming_revenue"] == 1000.0
    assert analysis["expenses"]["studio_expenses"] == 500.0

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
    assert report["net_income"] == 500.0
    assert report["categories"]["streaming_revenue"] == 1000.0
    assert report["categories"]["studio_expenses"] == 500.0

@pytest.mark.asyncio
async def test_get_monthly_summary(agent, sample_income, sample_expense):
    """Test generating a monthly financial summary."""
    await agent.add_financial_record(sample_income)
    await agent.add_financial_record(sample_expense)
    
    current_month = datetime.now().replace(day=1)
    summary = await agent.get_monthly_summary(current_month)
    assert summary["month"] == current_month.strftime("%Y-%m")
    assert summary["total_income"] == 1000.0
    assert summary["total_expenses"] == 500.0
    assert summary["net_income"] == 500.0 