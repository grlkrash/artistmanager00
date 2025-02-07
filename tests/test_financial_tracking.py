import pytest
from datetime import datetime, timedelta
from artist_manager_agent.team_management import (
    PaymentManager,
    FinancialAccount,
    EnhancedTransaction,
    BudgetTracking,
    TransactionCategory,
    TransactionSource
)

@pytest.fixture
def payment_manager():
    return PaymentManager(
        stripe_key="test_stripe_key",
        paypal_client_id="test_client_id",
        paypal_secret="test_secret"
    )

@pytest.fixture
def sample_account():
    return FinancialAccount(
        name="Test Account",
        type="payment_platform",
        provider="stripe"
    )

@pytest.fixture
def sample_transaction():
    return EnhancedTransaction(
        date=datetime.now(),
        amount=1000.0,
        category=TransactionCategory.INCOME_STREAMING,
        description="Test streaming revenue",
        source=TransactionSource.STRIPE
    )

@pytest.fixture
def sample_budget():
    return BudgetTracking(
        project_id="test_project",
        period_start=datetime.now(),
        period_end=datetime.now() + timedelta(days=30),
        categories={
            TransactionCategory.EXPENSE_STUDIO: 2000.0,
            TransactionCategory.EXPENSE_MARKETING: 1000.0
        }
    )

@pytest.mark.asyncio
async def test_add_financial_account(payment_manager, sample_account):
    """Test adding a financial account."""
    account_id = await payment_manager.add_financial_account(sample_account)
    assert account_id in payment_manager.accounts
    assert payment_manager.accounts[account_id].name == "Test Account"

@pytest.mark.asyncio
async def test_record_transaction(payment_manager, sample_transaction):
    """Test recording a transaction."""
    transaction_id = await payment_manager.record_transaction(sample_transaction)
    assert transaction_id in payment_manager.transactions
    assert payment_manager.transactions[transaction_id].amount == 1000.0

@pytest.mark.asyncio
async def test_cash_flow_analysis(payment_manager):
    """Test cash flow analysis."""
    # Add income transaction
    income = EnhancedTransaction(
        date=datetime.now(),
        amount=1000.0,
        category=TransactionCategory.INCOME_STREAMING,
        description="Streaming revenue",
        source=TransactionSource.STRIPE
    )
    await payment_manager.record_transaction(income)
    
    # Add expense transaction
    expense = EnhancedTransaction(
        date=datetime.now(),
        amount=500.0,
        category=TransactionCategory.EXPENSE_STUDIO,
        description="Studio time",
        source=TransactionSource.MANUAL
    )
    await payment_manager.record_transaction(expense)
    
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    
    analysis = await payment_manager.get_cash_flow_analysis(start_date, end_date)
    assert analysis["net_cash_flow"] == 500.0  # 1000 income - 500 expense
    assert TransactionCategory.INCOME_STREAMING.value in analysis["income"]
    assert TransactionCategory.EXPENSE_STUDIO.value in analysis["expenses"]
    assert analysis["income"][TransactionCategory.INCOME_STREAMING.value] == 1000.0
    assert analysis["expenses"][TransactionCategory.EXPENSE_STUDIO.value] == 500.0

@pytest.mark.asyncio
async def test_budget_variance(payment_manager, sample_budget):
    """Test budget variance analysis."""
    # Add budget
    payment_manager.budgets[sample_budget.project_id] = sample_budget
    
    # Add some transactions
    transaction = EnhancedTransaction(
        date=datetime.now(),
        amount=1500.0,
        category=TransactionCategory.EXPENSE_STUDIO,
        description="Studio session",
        source=TransactionSource.MANUAL,
        project_id=sample_budget.project_id
    )
    await payment_manager.record_transaction(transaction)
    
    variance = await payment_manager.get_budget_variance(sample_budget.project_id)
    assert variance["by_category"][TransactionCategory.EXPENSE_STUDIO.value] == 500.0  # 2000 budget - 1500 spent
    assert variance["percent_used"][TransactionCategory.EXPENSE_STUDIO.value] == 75.0  # 1500/2000 * 100 