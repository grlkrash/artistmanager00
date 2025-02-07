from typing import Dict, List, Optional, Union, Any
import uuid
from datetime import datetime, timedelta
from .log import logger
from pydantic import BaseModel
from coinbase.wallet.client import Client as CoinbaseClient
from enum import Enum
import aiohttp

class PaymentMethod(str, Enum):
    """Payment methods."""
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"

class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentRequest(BaseModel):
    """Payment request model."""
    id: str = str(uuid.uuid4())
    amount: float
    currency: str = "USD"
    description: str
    collaborator_id: Optional[str] = None
    project_id: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = datetime.now()
    paid_at: Optional[datetime] = None
    invoice_link: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None

class CollaboratorRole(str, Enum):
    """Collaborator roles."""
    ARTIST = "artist"
    PRODUCER = "producer"
    MANAGER = "manager"
    SONGWRITER = "songwriter"
    ENGINEER = "engineer"

class CollaboratorProfile(BaseModel):
    """Collaborator profile model."""
    id: str = str(uuid.uuid4())
    name: str
    role: CollaboratorRole
    expertise: List[str]
    rate: Optional[float] = None
    currency: str = "USD"
    location: Optional[str] = None
    availability: Dict[str, List[str]] = {}  # day -> list of time slots
    portfolio_link: Optional[str] = None
    created_at: datetime = datetime.now()

class RateRange(BaseModel):
    """Market rate ranges for different roles."""
    min_rate: float
    max_rate: float
    currency: str = "USD"
    rate_type: str  # hourly, per_project, per_session
    location: Optional[str] = None
    experience_level: Optional[str] = None  # junior, mid, senior
    updated_at: datetime = datetime.now()

class TransactionSource(str, Enum):
    """Source of financial transactions."""
    MANUAL = "manual"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    BANK = "bank"
    OTHER = "other"

class TransactionCategory(str, Enum):
    """Detailed transaction categories."""
    INCOME_STREAMING = "income_streaming"
    INCOME_LICENSING = "income_licensing"
    INCOME_PERFORMANCE = "income_performance"
    INCOME_MERCHANDISE = "income_merchandise"
    EXPENSE_STUDIO = "expense_studio"
    EXPENSE_MARKETING = "expense_marketing"
    EXPENSE_EQUIPMENT = "expense_equipment"
    EXPENSE_TRAVEL = "expense_travel"
    EXPENSE_TEAM = "expense_team"
    EXPENSE_OTHER = "expense_other"

class FinancialAccount(BaseModel):
    """Track different financial accounts."""
    id: str = str(uuid.uuid4())
    name: str
    type: str  # checking, savings, credit, payment_platform
    provider: str
    currency: str = "USD"
    last_sync: Optional[datetime] = None
    credentials: Dict[str, Any] = {}

class EnhancedTransaction(BaseModel):
    """Enhanced transaction tracking."""
    id: str = str(uuid.uuid4())
    date: datetime
    amount: float
    currency: str = "USD"
    category: TransactionCategory
    description: str
    source: TransactionSource
    account_id: Optional[str] = None
    project_id: Optional[str] = None
    payment_request_id: Optional[str] = None
    external_id: Optional[str] = None
    status: str = "completed"
    metadata: Dict[str, Any] = {}
    reconciled: bool = False
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class BudgetTracking(BaseModel):
    """Enhanced budget tracking."""
    id: str = str(uuid.uuid4())
    project_id: Optional[str]
    period_start: datetime
    period_end: datetime
    categories: Dict[TransactionCategory, float] = {}
    actuals: Dict[TransactionCategory, float] = {}
    forecasted_expenses: List[Dict[str, Any]] = []
    last_updated: datetime = datetime.now()

class PaymentManager:
    """Handle payment processing."""
    
    def __init__(self, 
                 stripe_key: Optional[str] = None,
                 paypal_client_id: Optional[str] = None,
                 paypal_secret: Optional[str] = None):
        self.transactions: Dict[str, EnhancedTransaction] = {}
        self.accounts: Dict[str, FinancialAccount] = {}
        self.budgets: Dict[str, BudgetTracking] = {}
        self.stripe_key = stripe_key
        self.paypal_credentials = {
            "client_id": paypal_client_id,
            "secret": paypal_secret
        } if paypal_client_id and paypal_secret else None

    async def create_payment_request(
        self,
        amount: float,
        currency: str,
        description: str,
        payment_method: PaymentMethod,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a payment request."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
            
        if currency not in ["USD", "EUR", "GBP"]:
            raise ValueError("Invalid currency")
            
        if payment_method == PaymentMethod.CRYPTO and self.stripe_key:
            # Implement Stripe payment
            return {
                "id": str(uuid.uuid4()),
                "payment_url": "https://stripe.com/pay/test",
                "status": "pending",
                "expires_at": datetime.now() + timedelta(days=7),
                "payment_method": PaymentMethod.CRYPTO
            }
        elif payment_method == PaymentMethod.BANK_TRANSFER and self.paypal_credentials:
            # Implement PayPal payment
            return {
                "id": str(uuid.uuid4()),
                "payment_url": "https://paypal.com/pay/test",
                "status": "pending",
                "expires_at": datetime.now() + timedelta(days=7),
                "payment_method": PaymentMethod.BANK_TRANSFER,
                "bank_details": {
                    "account": "TEST-ACCOUNT",
                    "routing": "TEST-ROUTING"
                }
            }
        else:
            # Default to manual bank transfer
            return {
                "id": str(uuid.uuid4()),
                "payment_url": None,
                "status": "pending",
                "expires_at": datetime.now() + timedelta(days=7),
                "payment_method": PaymentMethod.BANK_TRANSFER,
                "bank_details": {
                    "account": "TEST-ACCOUNT",
                    "routing": "TEST-ROUTING"
                }
            }
            
    async def add_financial_account(self, account: FinancialAccount) -> str:
        """Add a new financial account for tracking."""
        self.accounts[account.id] = account
        return account.id
        
    async def sync_transactions(self, account_id: str) -> List[str]:
        """Sync transactions from external source."""
        account = self.accounts.get(account_id)
        if not account:
            raise ValueError("Account not found")
            
        new_transaction_ids = []
        
        if account.type == "payment_platform":
            if account.provider == "stripe" and self.stripe_key:
                # Implement Stripe sync
                pass
            elif account.provider == "paypal" and self.paypal_credentials:
                # Implement PayPal sync
                pass
                
        return new_transaction_ids
        
    async def record_transaction(self, transaction: EnhancedTransaction) -> str:
        """Record a new transaction."""
        self.transactions[transaction.id] = transaction
        
        # Update budget tracking if project_id exists
        if transaction.project_id and transaction.project_id in self.budgets:
            budget = self.budgets[transaction.project_id]
            if transaction.category.value.startswith("expense_"):
                budget.actuals[transaction.category] = (
                    budget.actuals.get(transaction.category, 0) + transaction.amount
                )
                budget.last_updated = datetime.now()
            
        return transaction.id
        
    async def get_cash_flow_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate cash flow analysis."""
        transactions = [
            t for t in self.transactions.values()
            if start_date <= t.date <= end_date
            and (not project_id or t.project_id == project_id)
        ]
        
        analysis = {
            "income": {},
            "expenses": {},
            "net_cash_flow": 0,
            "upcoming_obligations": [],
            "forecasted_balance": 0
        }
        
        for t in transactions:
            category = t.category.value
            if category.startswith("income_"):
                analysis["income"][category] = (
                    analysis["income"].get(category, 0) + t.amount
                )
                analysis["net_cash_flow"] += t.amount
            else:
                analysis["expenses"][category] = (
                    analysis["expenses"].get(category, 0) + t.amount
                )
                analysis["net_cash_flow"] -= t.amount
                
        return analysis
        
    async def get_budget_variance(self, project_id: str) -> Dict[str, Any]:
        """Analyze budget vs actual spending."""
        budget = self.budgets.get(project_id)
        if not budget:
            raise ValueError("Budget not found")
            
        variance = {
            "by_category": {},
            "total_variance": 0,
            "percent_used": {}
        }
        
        for category, budgeted in budget.categories.items():
            actual = budget.actuals.get(category, 0)
            variance["by_category"][category.value] = budgeted - actual
            variance["percent_used"][category.value] = (actual / budgeted * 100) if budgeted > 0 else 0
            
        variance["total_variance"] = (
            sum(budget.categories.values()) - sum(budget.actuals.values())
        )
        
        return variance

class Project(BaseModel):
    """Track project details and team assignments."""
    id: str = str(uuid.uuid4())
    name: str
    description: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "active"  # active, completed, cancelled, on_hold
    team_members: List[str] = []  # collaborator_ids
    budget: Optional[float] = None
    deliverables: List[str] = []
    milestones: List[Dict] = []
    notes: Optional[str] = None

class BudgetCategory(str, Enum):
    """Budget categories for financial tracking."""
    PRODUCTION = "production"
    MIXING = "mixing"
    MASTERING = "mastering"
    MARKETING = "marketing"
    DISTRIBUTION = "distribution"
    OTHER = "other"

class FinancialTransaction(BaseModel):
    """Track financial transactions."""
    id: str = str(uuid.uuid4())
    amount: float
    currency: str = "USD"
    category: BudgetCategory
    description: str
    date: datetime = datetime.now()
    project_id: Optional[str] = None
    collaborator_id: Optional[str] = None
    payment_id: Optional[str] = None
    transaction_type: str  # income, expense, payment
    status: str = "pending"  # pending, completed, cancelled
    tax_category: Optional[str] = None
    receipt_url: Optional[str] = None

class BudgetAllocation(BaseModel):
    """Track budget allocations."""
    category: BudgetCategory
    amount: float
    currency: str = "USD"
    project_id: Optional[str] = None
    period_start: datetime
    period_end: datetime
    actual_spend: float = 0.0
    notes: Optional[str] = None

class CalendarProvider(str, Enum):
    """Supported calendar providers."""
    GOOGLE = "google"
    OUTLOOK = "outlook"
    ICAL = "ical"
    MANUAL = "manual"

class AvailabilityPreference(str, Enum):
    """How to handle availability requests."""
    AUTOMATIC = "automatic"  # Auto-approve if fits preferences
    MANUAL = "manual"  # Always require manual approval
    SMART = "smart"  # Auto-approve routine, manual for important

class CalendarIntegration(BaseModel):
    """Calendar integration settings."""
    id: str = str(uuid.uuid4())
    collaborator_id: str
    provider: CalendarProvider
    credentials: Dict[str, Any] = {}
    last_sync: Optional[datetime] = None
    preferences: Dict[str, Any] = {
        "auto_sync": True,
        "availability_preference": AvailabilityPreference.SMART,
        "working_hours": {
            "monday": ["09:00-17:00"],
            "tuesday": ["09:00-17:00"],
            "wednesday": ["09:00-17:00"],
            "thursday": ["09:00-17:00"],
            "friday": ["09:00-17:00"]
        },
        "booking_notice": 24,  # hours
        "max_meetings_per_day": 5
    }

class Meeting(BaseModel):
    """Track meetings and scheduling."""
    id: str = str(uuid.uuid4())
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str]  # collaborator_ids
    project_id: Optional[str] = None
    status: str = "scheduled"  # scheduled, cancelled, completed
    meeting_type: str  # general, project, client
    location: Optional[str] = None
    virtual_meeting_link: Optional[str] = None
    calendar_events: Dict[str, str] = {}  # collaborator_id -> calendar_event_id

class TeamManager:
    def __init__(self, coinbase_api_key: Optional[str] = None, coinbase_api_secret: Optional[str] = None):
        self.collaborators: Dict[str, CollaboratorProfile] = {}
        self.projects: Dict[str, Project] = {}
        self.payments: Dict[str, PaymentRequest] = {}
        self.collaborator_requests: List[Dict[str, Any]] = []
        self.external_db = None  # Will be initialized with Supabase
        self.market_rates: Dict[str, List[RateRange]] = {}
        self.payment_manager = PaymentManager(coinbase_api_key, coinbase_api_secret)
        self.transactions: Dict[str, FinancialTransaction] = {}
        self.budget_allocations: Dict[str, List[BudgetAllocation]] = {}
        self.calendar_integrations: Dict[str, CalendarIntegration] = {}
        self.meetings: Dict[str, Meeting] = {}

    async def initialize_external_db(self, supabase_client):
        """Initialize external database connection."""
        self.external_db = supabase_client

    async def request_specific_collaborator(
        self,
        name: str,
        role: CollaboratorRole,
        project_id: Optional[str] = None,
        notes: Optional[str] = None,
        portfolio_url: Optional[str] = None
    ) -> str:
        """Request to scout and reach out to a specific collaborator."""
        request_id = str(uuid.uuid4())
        request = {
            "id": request_id,
            "name": name,
            "role": role,
            "project_id": project_id,
            "notes": notes,
            "portfolio_url": portfolio_url,
            "status": "pending",
            "created_at": datetime.now()
        }
        self.collaborator_requests.append(request)
        
        # If we have external DB access, store the request
        if self.external_db:
            await self.external_db.table("collaborator_requests").insert(request).execute()
        
        return request_id

    async def scout_collaborators(
        self,
        role: CollaboratorRole,
        expertise: List[str],
        budget_range: Optional[tuple] = None,
        location: Optional[str] = None,
        availability_needed: Optional[Dict[str, List[str]]] = None,
        portfolio_required: bool = False
    ) -> List[Union[CollaboratorProfile, Dict]]:
        """Enhanced collaborator scouting with external search."""
        matches = []
        
        # Search internal collaborators
        for collaborator in self.collaborators.values():
            if self._matches_criteria(
                collaborator, 
                role, 
                expertise, 
                budget_range,
                location,
                availability_needed
            ):
                matches.append(collaborator)

        # Search external database if available
        if self.external_db:
            query = self.external_db.table("collaborators").select("*")
            
            # Apply filters
            query = query.eq("role", role)
            if location:
                query = query.eq("location", location)
            if budget_range:
                min_budget, max_budget = budget_range
                query = query.gte("rate", min_budget).lte("rate", max_budget)
            if portfolio_required:
                query = query.not_.is_("portfolio_link", "null")
            
            try:
                result = await query.execute()
                external_matches = [
                    CollaboratorProfile(**data) 
                    for data in result.data
                    if any(skill in data.get("expertise", []) for skill in expertise)
                ]
                matches.extend(external_matches)
            except Exception as e:
                logger.error(f"Error searching external database: {e}")

        return matches

    def _matches_criteria(
        self,
        collaborator: CollaboratorProfile,
        role: CollaboratorRole,
        expertise: List[str],
        budget_range: Optional[tuple] = None,
        location: Optional[str] = None,
        availability_needed: Optional[Dict[str, List[str]]] = None
    ) -> bool:
        """Check if collaborator matches all criteria."""
        if collaborator.role != role:
            return False
            
        # Check expertise match
        if not any(skill in collaborator.expertise for skill in expertise):
            return False
            
        # Check budget if specified
        if budget_range and collaborator.rate:
            min_budget, max_budget = budget_range
            if not (min_budget <= collaborator.rate <= max_budget):
                return False
                
        # Check location if specified
        if location and getattr(collaborator, "location", None) != location:
            return False
            
        # Check availability if specified
        if availability_needed:
            for day, times in availability_needed.items():
                if day not in collaborator.availability:
                    return False
                # Check if any required time slot overlaps with available slots
                if not any(
                    self._time_slots_overlap(req_time, avail_time)
                    for req_time in times
                    for avail_time in collaborator.availability[day]
                ):
                    return False
                    
        return True

    def _time_slots_overlap(self, slot1: str, slot2: str) -> bool:
        """Check if two time slots overlap."""
        start1, end1 = slot1.split("-")
        start2, end2 = slot2.split("-")
        return not (end1 <= start2 or end2 <= start1)

    async def get_market_rate(
        self,
        role: CollaboratorRole,
        location: Optional[str] = None,
        experience_level: Optional[str] = None,
        rate_type: str = "hourly"
    ) -> Optional[RateRange]:
        """Get market rate range for a role."""
        # Try to get from cache first
        cache_key = f"{role}_{location}_{experience_level}_{rate_type}"
        if cache_key in self.market_rates:
            return self.market_rates[cache_key]

        if self.external_db:
            try:
                query = self.external_db.table("market_rates").select("*").eq("role", role)
                if location:
                    query = query.eq("location", location)
                if experience_level:
                    query = query.eq("experience_level", experience_level)
                query = query.eq("rate_type", rate_type)
                
                result = await query.execute()
                if result.data:
                    rate_range = RateRange(**result.data[0])
                    self.market_rates[cache_key] = rate_range
                    return rate_range
            except Exception as e:
                logger.error(f"Error fetching market rates: {e}")

        # Fallback to default ranges
        default_ranges = {
            CollaboratorRole.PRODUCER: RateRange(
                min_rate=50.0,
                max_rate=200.0,
                rate_type="hourly"
            ),
            CollaboratorRole.MIXING_ENGINEER: RateRange(
                min_rate=75.0,
                max_rate=250.0,
                rate_type="hourly"
            ),
            # Add more default ranges...
        }
        return default_ranges.get(role)

    async def validate_rate(
        self,
        role: CollaboratorRole,
        rate: float,
        rate_type: str,
        location: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate if a rate is within market range."""
        market_rate = await self.get_market_rate(
            role,
            location,
            experience_level,
            rate_type
        )
        
        if not market_rate:
            return {"valid": True, "message": "No market rate data available for comparison"}
            
        is_valid = market_rate.min_rate <= rate <= market_rate.max_rate
        
        if is_valid:
            message = "Rate is within market range"
        elif rate < market_rate.min_rate:
            message = f"Rate is below market minimum of {market_rate.min_rate}"
        else:
            message = f"Rate is above market maximum of {market_rate.max_rate}"
            
        return {
            "valid": is_valid,
            "message": message,
            "market_range": {
                "min": market_rate.min_rate,
                "max": market_rate.max_rate,
                "currency": market_rate.currency
            }
        }

    async def create_payment_request(self, request: PaymentRequest) -> Dict[str, Any]:
        """Create a new payment request with payment processing."""
        # Store payment request
        self.payments[request.id] = request
        
        # Create actual payment request with payment provider
        payment_result = await self.payment_manager.create_payment_request(
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            payment_method=request.payment_method,
            metadata={
                "collaborator_id": request.collaborator_id,
                "payment_request_id": request.id
            }
        )
        
        # Update payment request with provider details
        request.payment_method = request.payment_method
        request.invoice_link = payment_result["payment_url"]
        
        # Store in external DB if available
        if self.external_db:
            await self.external_db.table("payments").insert(request.dict()).execute()
        
        return payment_result

    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Check payment status and update records."""
        status = await self.payment_manager.check_payment_status(payment_id)
        
        if payment_id in self.payments:
            payment = self.payments[payment_id]
            if status["paid"]:
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.now()
            
            # Update in external DB if available
            if self.external_db:
                await self.external_db.table("payments").update(payment.dict()).eq("id", payment_id).execute()
        
        return status 

    async def add_collaborator(self, profile: CollaboratorProfile) -> str:
        """Add a new collaborator to the team."""
        if not profile.id:
            profile.id = str(uuid.uuid4())
        self.collaborators[profile.id] = profile
        return profile.id

    async def get_collaborator(self, collaborator_id: str) -> Optional[CollaboratorProfile]:
        """Get collaborator profile by ID."""
        return self.collaborators.get(collaborator_id)

    async def update_collaborator(
        self,
        collaborator_id: str,
        updates: Dict
    ) -> Optional[CollaboratorProfile]:
        """Update collaborator profile."""
        if collaborator_id not in self.collaborators:
            return None
            
        profile = self.collaborators[collaborator_id]
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
                
        return profile

    async def remove_collaborator(self, collaborator_id: str) -> bool:
        """Remove a collaborator from the team."""
        if collaborator_id not in self.collaborators:
            return False
            
        # Remove from projects
        for project in self.projects.values():
            if collaborator_id in project.team_members:
                project.team_members.remove(collaborator_id)
                
        del self.collaborators[collaborator_id]
        return True

    async def create_project(self, project: Project) -> str:
        """Create a new project."""
        if not project.id:
            project.id = str(uuid.uuid4())
        self.projects[project.id] = project
        return project.id

    async def update_project(
        self,
        project_id: str,
        updates: Dict
    ) -> Optional[Project]:
        """Update project details."""
        if project_id not in self.projects:
            return None
            
        project = self.projects[project_id]
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)
                
        return project

    async def assign_to_project(
        self,
        project_id: str,
        collaborator_id: str,
        role: Optional[str] = None
    ) -> bool:
        """Assign a collaborator to a project."""
        if (project_id not in self.projects or 
            collaborator_id not in self.collaborators):
            return False
            
        project = self.projects[project_id]
        if collaborator_id not in project.team_members:
            project.team_members.append(collaborator_id)
            
        return True

    async def remove_from_project(
        self,
        project_id: str,
        collaborator_id: str
    ) -> bool:
        """Remove a collaborator from a project."""
        if (project_id not in self.projects or 
            collaborator_id not in self.collaborators):
            return False
            
        project = self.projects[project_id]
        if collaborator_id in project.team_members:
            project.team_members.remove(collaborator_id)
            
        return True

    async def get_project_team(self, project_id: str) -> List[CollaboratorProfile]:
        """Get all team members assigned to a project."""
        if project_id not in self.projects:
            return []
            
        project = self.projects[project_id]
        return [
            self.collaborators[member_id]
            for member_id in project.team_members
            if member_id in self.collaborators
        ]

    async def get_collaborator_projects(
        self,
        collaborator_id: str
    ) -> List[Project]:
        """Get all projects a collaborator is assigned to."""
        if collaborator_id not in self.collaborators:
            return []
            
        return [
            project for project in self.projects.values()
            if collaborator_id in project.team_members
        ]

    async def add_project_milestone(
        self,
        project_id: str,
        milestone: Dict
    ) -> bool:
        """Add a milestone to a project."""
        if project_id not in self.projects:
            return False
            
        project = self.projects[project_id]
        milestone["id"] = str(uuid.uuid4())
        milestone["created_at"] = datetime.now()
        project.milestones.append(milestone)
        return True

    async def update_milestone_status(
        self,
        project_id: str,
        milestone_id: str,
        status: str
    ) -> bool:
        """Update the status of a project milestone."""
        if project_id not in self.projects:
            return False
            
        project = self.projects[project_id]
        for milestone in project.milestones:
            if milestone["id"] == milestone_id:
                milestone["status"] = status
                milestone["updated_at"] = datetime.now()
                return True
                
        return False

    async def get_team_availability(
        self,
        date: datetime,
        role: Optional[CollaboratorRole] = None
    ) -> Dict[str, List[str]]:
        """Get team availability for a specific date."""
        availability = {}
        day_name = date.strftime("%A").lower()
        
        for collaborator in self.collaborators.values():
            if role and collaborator.role != role:
                continue
                
            if day_name in collaborator.availability:
                availability[collaborator.id] = collaborator.availability[day_name]
                
        return availability

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string (HH:MM) to minutes since midnight."""
        hours, minutes = map(int, time_str.split(":"))
        return hours * 60 + minutes
        
    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes since midnight to time string (HH:MM)."""
        hours, mins = divmod(minutes, 60)
        return f"{hours:02d}:{mins:02d}"

    async def find_common_availability(
        self,
        collaborator_ids: List[str],
        date: datetime
    ) -> List[str]:
        """Find common availability slots among collaborators."""
        # Get all collaborators' availability for the given day
        all_slots = []
        for collab_id in collaborator_ids:
            collaborator = await self.get_collaborator(collab_id)
            if not collaborator:
                continue
            day_name = date.strftime("%A").lower()
            if day_name in collaborator.availability:
                all_slots.append(collaborator.availability[day_name])

        if not all_slots:
            return []

        # Find latest start time among all slots
        latest_start = "00:00"
        for slots in all_slots:
            for slot in slots:
                start, _ = slot.split("-")
                if self._time_to_minutes(start) > self._time_to_minutes(latest_start):
                    latest_start = start

        # Find earliest end time among all slots that contain latest_start
        earliest_end = None
        for slots in all_slots:
            valid_end = None
            for slot in slots:
                start, end = slot.split("-")
                if self._time_to_minutes(start) <= self._time_to_minutes(latest_start):
                    if valid_end is None or self._time_to_minutes(end) < self._time_to_minutes(valid_end):
                        valid_end = end
            
            if valid_end is None:
                return []  # This collaborator has no valid slots
            
            if earliest_end is None or self._time_to_minutes(valid_end) < self._time_to_minutes(earliest_end):
                earliest_end = valid_end

        if earliest_end is None or self._time_to_minutes(latest_start) >= self._time_to_minutes(earliest_end):
            return []

        return [f"{latest_start}-{earliest_end}"]

    async def get_team_analytics(self) -> Dict[str, Any]:
        """Get analytics about team composition and project distribution."""
        analytics = {
            "total_collaborators": len(self.collaborators),
            "total_projects": len(self.projects),
            "role_distribution": {},
            "project_status": {},
            "availability_by_day": {
                "monday": 0, "tuesday": 0, "wednesday": 0,
                "thursday": 0, "friday": 0, "saturday": 0, "sunday": 0
            },
            "active_projects_by_role": {},
            "average_project_team_size": 0
        }
        
        # Role distribution and availability
        for collaborator in self.collaborators.values():
            # Count roles
            role = collaborator.role.value
            analytics["role_distribution"][role] = analytics["role_distribution"].get(role, 0) + 1
            
            # Count availability
            for day in collaborator.availability:
                analytics["availability_by_day"][day] += 1
                
        # Project statistics
        total_team_size = 0
        for project in self.projects.values():
            # Project status distribution
            analytics["project_status"][project.status] = (
                analytics["project_status"].get(project.status, 0) + 1
            )
            
            # Team size
            team_size = len(project.team_members)
            total_team_size += team_size
            
            # Count projects by role
            for member_id in project.team_members:
                if member_id in self.collaborators:
                    role = self.collaborators[member_id].role.value
                    if project.status == "active":
                        analytics["active_projects_by_role"][role] = (
                            analytics["active_projects_by_role"].get(role, 0) + 1
                        )
                        
        # Calculate average team size
        if self.projects:
            analytics["average_project_team_size"] = total_team_size / len(self.projects)
            
        return analytics

    async def get_project_analytics(self, project_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific project."""
        if project_id not in self.projects:
            return {}
            
        project = self.projects[project_id]
        analytics = {
            "project_name": project.name,
            "status": project.status,
            "duration": None,
            "team_size": len(project.team_members),
            "role_distribution": {},
            "milestone_completion": {
                "total": len(project.milestones),
                "completed": 0,
                "in_progress": 0,
                "pending": 0
            },
            "budget_utilization": None
        }
        
        # Calculate duration
        if project.end_date and project.start_date:
            analytics["duration"] = (project.end_date - project.start_date).days
            
        # Team role distribution
        for member_id in project.team_members:
            if member_id in self.collaborators:
                role = self.collaborators[member_id].role.value
                analytics["role_distribution"][role] = (
                    analytics["role_distribution"].get(role, 0) + 1
                )
                
        # Milestone statistics
        for milestone in project.milestones:
            status = milestone.get("status", "pending")
            analytics["milestone_completion"][status] = (
                analytics["milestone_completion"].get(status, 0) + 1
            )
            
        # Budget utilization if budget is set
        if project.budget:
            # You would typically track actual costs in a real application
            analytics["budget_utilization"] = {
                "total_budget": project.budget,
                "remaining": project.budget  # Placeholder
            }
            
        return analytics

    async def get_collaborator_performance(
        self,
        collaborator_id: str,
        date_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Get performance metrics for a specific collaborator."""
        if collaborator_id not in self.collaborators:
            return {}
            
        collaborator = self.collaborators[collaborator_id]
        performance = {
            "name": collaborator.name,
            "role": collaborator.role.value,
            "projects": {
                "total": 0,
                "active": 0,
                "completed": 0
            },
            "milestones": {
                "total": 0,
                "completed": 0,
                "in_progress": 0
            },
            "availability_score": 0,  # Percentage of work hours available
            "project_completion_rate": 0
        }
        
        # Project statistics
        completed_projects = 0
        for project in self.projects.values():
            if collaborator_id in project.team_members:
                performance["projects"]["total"] += 1
                if project.status == "active":
                    performance["projects"]["active"] += 1
                elif project.status == "completed":
                    performance["projects"]["completed"] += 1
                    completed_projects += 1
                    
        # Calculate project completion rate
        if performance["projects"]["total"] > 0:
            performance["project_completion_rate"] = (
                completed_projects / performance["projects"]["total"]
            )
            
        # Calculate availability score
        total_slots = 0
        available_slots = 0
        for day, slots in collaborator.availability.items():
            total_slots += 8  # Assuming 8 working hours per day
            available_slots += len(slots)
        if total_slots > 0:
            performance["availability_score"] = available_slots / total_slots
            
        return performance

    async def generate_team_report(self) -> str:
        """Generate a comprehensive team status report."""
        analytics = await self.get_team_analytics()
        
        report = [
            "Team Status Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "👥 Team Composition",
            f"Total Collaborators: {analytics['total_collaborators']}",
            "",
            "Role Distribution:"
        ]
        
        for role, count in analytics["role_distribution"].items():
            report.append(f"- {role}: {count}")
            
        report.extend([
            "",
            "📈 Project Status",
            f"Total Projects: {analytics['total_projects']}"
        ])
        
        for status, count in analytics["project_status"].items():
            report.append(f"- {status}: {count}")
            
        report.extend([
            "",
            "⏰ Team Availability",
            "Daily Availability (number of team members):"
        ])
        
        for day, count in analytics["availability_by_day"].items():
            report.append(f"- {day.capitalize()}: {count}")
            
        report.extend([
            "",
            "📊 Project Statistics",
            f"Average Team Size: {analytics['average_project_team_size']:.1f} members"
        ])
        
        return "\n".join(report) 

    async def record_transaction(self, transaction: FinancialTransaction) -> str:
        """Record a financial transaction."""
        self.transactions[transaction.id] = transaction
        if self.external_db:
            await self.external_db.table("transactions").insert(transaction.dict()).execute()
        return transaction.id

    async def set_project_budget(
        self,
        project_id: str,
        allocations: List[BudgetAllocation]
    ) -> bool:
        """Set or update project budget allocations."""
        if project_id not in self.projects:
            return False
        
        self.budget_allocations[project_id] = allocations
        self.projects[project_id].budget = sum(a.amount for a in allocations)
        
        if self.external_db:
            await self.external_db.table("budget_allocations").upsert(
                [{"project_id": project_id, **a.dict()} for a in allocations]
            ).execute()
        
        return True

    async def get_financial_report(
        self,
        start_date: datetime,
        end_date: datetime,
        project_id: Optional[str] = None,
        categories: Optional[List[BudgetCategory]] = None
    ) -> Dict[str, Any]:
        """Generate a financial report for the specified period."""
        transactions = [
            t for t in self.transactions.values()
            if start_date <= t.date <= end_date
            and (not project_id or t.project_id == project_id)
            and (not categories or t.category in categories)
        ]
        
        report = {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "summary": {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net": 0.0
            },
            "by_category": {},
            "by_project": {},
            "pending_payments": [],
            "tax_summary": {
                "deductible_expenses": 0.0,
                "income_by_category": {}
            }
        }
        
        for t in transactions:
            # Update summary
            if t.transaction_type == "income":
                report["summary"]["total_income"] += t.amount
            else:
                report["summary"]["total_expenses"] += t.amount
                
            # Update category breakdown
            cat = t.category.value
            if cat not in report["by_category"]:
                report["by_category"][cat] = {
                    "income": 0.0,
                    "expenses": 0.0,
                    "budget": 0.0,
                    "remaining": 0.0
                }
            if t.transaction_type == "income":
                report["by_category"][cat]["income"] += t.amount
            else:
                report["by_category"][cat]["expenses"] += t.amount
                
            # Update project breakdown
            if t.project_id:
                if t.project_id not in report["by_project"]:
                    report["by_project"][t.project_id] = {
                        "income": 0.0,
                        "expenses": 0.0,
                        "budget": self.projects[t.project_id].budget if t.project_id in self.projects else 0.0
                    }
                if t.transaction_type == "income":
                    report["by_project"][t.project_id]["income"] += t.amount
                else:
                    report["by_project"][t.project_id]["expenses"] += t.amount
                    
            # Track pending payments
            if t.status == "pending" and t.transaction_type == "payment":
                report["pending_payments"].append({
                    "id": t.id,
                    "amount": t.amount,
                    "description": t.description,
                    "collaborator_id": t.collaborator_id
                })
                
            # Update tax summary
            if t.tax_category:
                if t.transaction_type == "expense":
                    report["tax_summary"]["deductible_expenses"] += t.amount
                else:
                    if t.tax_category not in report["tax_summary"]["income_by_category"]:
                        report["tax_summary"]["income_by_category"][t.tax_category] = 0.0
                    report["tax_summary"]["income_by_category"][t.tax_category] += t.amount
        
        # Calculate net and budget remaining
        report["summary"]["net"] = report["summary"]["total_income"] - report["summary"]["total_expenses"]
        
        # Add budget vs actual for categories
        for project_id, allocations in self.budget_allocations.items():
            if project_id == project_id or not project_id:
                for allocation in allocations:
                    cat = allocation.category.value
                    if cat in report["by_category"]:
                        report["by_category"][cat]["budget"] += allocation.amount
                        report["by_category"][cat]["remaining"] = (
                            allocation.amount - report["by_category"][cat]["expenses"]
                        )
        
        return report

    async def get_tax_report(self, tax_year: int) -> Dict[str, Any]:
        """Generate a tax report for the specified year."""
        start_date = datetime(tax_year, 1, 1)
        end_date = datetime(tax_year, 12, 31, 23, 59, 59)
        
        report = await self.get_financial_report(start_date, end_date)
        
        # Add tax-specific calculations
        tax_report = {
            "year": tax_year,
            "gross_income": report["summary"]["total_income"],
            "total_expenses": report["summary"]["total_expenses"],
            "net_income": report["summary"]["net"],
            "deductible_expenses": report["tax_summary"]["deductible_expenses"],
            "income_by_category": report["tax_summary"]["income_by_category"],
            "expense_categories": {},
            "collaborator_payments": {}
        }
        
        # Categorize expenses for tax purposes
        for t in self.transactions.values():
            if start_date <= t.date <= end_date and t.transaction_type == "expense":
                cat = t.category.value
                if cat not in tax_report["expense_categories"]:
                    tax_report["expense_categories"][cat] = 0.0
                tax_report["expense_categories"][cat] += t.amount
                
                # Track payments to collaborators
                if t.collaborator_id:
                    if t.collaborator_id not in tax_report["collaborator_payments"]:
                        collaborator = self.collaborators.get(t.collaborator_id)
                        tax_report["collaborator_payments"][t.collaborator_id] = {
                            "name": collaborator.name if collaborator else "Unknown",
                            "total_paid": 0.0,
                            "payment_ids": []
                        }
                    tax_report["collaborator_payments"][t.collaborator_id]["total_paid"] += t.amount
                    if t.payment_id:
                        tax_report["collaborator_payments"][t.collaborator_id]["payment_ids"].append(t.payment_id)
        
        return tax_report 

    async def add_calendar_integration(
        self,
        collaborator_id: str,
        provider: CalendarProvider,
        credentials: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add calendar integration for a collaborator."""
        integration = CalendarIntegration(
            collaborator_id=collaborator_id,
            provider=provider,
            credentials=credentials
        )
        if preferences:
            integration.preferences.update(preferences)
            
        self.calendar_integrations[integration.id] = integration
        return integration.id
        
    async def sync_calendar(self, integration_id: str) -> bool:
        """Sync calendar data for availability."""
        integration = self.calendar_integrations.get(integration_id)
        if not integration:
            return False
            
        try:
            if integration.provider == CalendarProvider.GOOGLE:
                # Implement Google Calendar sync
                pass
            elif integration.provider == CalendarProvider.OUTLOOK:
                # Implement Outlook sync
                pass
                
            integration.last_sync = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Calendar sync failed: {e}")
            return False
            
    async def schedule_meeting(
        self,
        title: str,
        attendees: List[str],
        duration_minutes: int,
        earliest_start: datetime,
        latest_start: datetime,
        meeting_type: str,
        project_id: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> Optional[Meeting]:
        """Schedule a meeting finding common availability."""
        # Get all attendees' availability
        available_slots = await self.find_common_availability(
            attendees,
            earliest_start.date()
        )
        
        if not available_slots:
            return None
            
        # Find best slot that fits duration
        best_slot = None
        for slot in available_slots:
            start, end = slot.split("-")
            slot_start = datetime.combine(
                earliest_start.date(),
                datetime.strptime(start, "%H:%M").time()
            )
            slot_end = datetime.combine(
                earliest_start.date(),
                datetime.strptime(end, "%H:%M").time()
            )
            
            if (slot_start >= earliest_start and 
                slot_end <= latest_start and
                (slot_end - slot_start).total_seconds() / 60 >= duration_minutes):
                best_slot = (slot_start, slot_end)
                break
                
        if not best_slot:
            return None
            
        # Create meeting
        meeting = Meeting(
            title=title,
            description=description,
            start_time=best_slot[0],
            end_time=best_slot[0] + timedelta(minutes=duration_minutes),
            attendees=attendees,
            project_id=project_id,
            meeting_type=meeting_type,
            location=location
        )
        
        # Create calendar events for all attendees
        for attendee_id in attendees:
            # Find their calendar integration
            integration = next(
                (i for i in self.calendar_integrations.values() 
                 if i.collaborator_id == attendee_id),
                None
            )
            
            if integration:
                try:
                    if integration.provider == CalendarProvider.GOOGLE:
                        # Create Google Calendar event
                        pass
                    elif integration.provider == CalendarProvider.OUTLOOK:
                        # Create Outlook event
                        pass
                        
                    # Store event ID for future reference
                    meeting.calendar_events[attendee_id] = "event_id"
                except Exception as e:
                    logger.error(f"Failed to create calendar event: {e}")
                    
        self.meetings[meeting.id] = meeting
        return meeting
        
    async def cancel_meeting(self, meeting_id: str) -> bool:
        """Cancel a meeting and remove calendar events."""
        meeting = self.meetings.get(meeting_id)
        if not meeting:
            return False
            
        # Cancel calendar events
        for attendee_id, event_id in meeting.calendar_events.items():
            integration = next(
                (i for i in self.calendar_integrations.values() 
                 if i.collaborator_id == attendee_id),
                None
            )
            
            if integration:
                try:
                    if integration.provider == CalendarProvider.GOOGLE:
                        # Delete Google Calendar event
                        pass
                    elif integration.provider == CalendarProvider.OUTLOOK:
                        # Delete Outlook event
                        pass
                except Exception as e:
                    logger.error(f"Failed to delete calendar event: {e}")
                    
        meeting.status = "cancelled"
        return True
        
    async def get_upcoming_meetings(
        self,
        collaborator_id: str,
        days_ahead: int = 7
    ) -> List[Meeting]:
        """Get upcoming meetings for a collaborator."""
        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)
        
        return [
            meeting for meeting in self.meetings.values()
            if (collaborator_id in meeting.attendees and
                meeting.status == "scheduled" and
                meeting.start_time >= now and
                meeting.start_time <= end_date)
        ] 