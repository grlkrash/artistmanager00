from typing import Dict, List, Optional, Union, Any
import uuid
from datetime import datetime
from log import logger
from pydantic import BaseModel
from coinbase.wallet.client import Client as CoinbaseClient
from enum import Enum

class RateRange(BaseModel):
    """Market rate ranges for different roles."""
    min_rate: float
    max_rate: float
    currency: str = "USD"
    rate_type: str  # hourly, per_project, per_session
    location: Optional[str] = None
    experience_level: Optional[str] = None  # junior, mid, senior
    updated_at: datetime = datetime.now()

class PaymentMethod(str, Enum):
    """Payment methods."""
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"

class PaymentManager:
    """Handle payment processing."""
    
    def __init__(self, coinbase_api_key: Optional[str] = None, coinbase_api_secret: Optional[str] = None):
        self.coinbase_client = None
        if coinbase_api_key and coinbase_api_secret:
            self.coinbase_client = CoinbaseClient(coinbase_api_key, coinbase_api_secret)

    async def create_payment_request(
        self,
        amount: float,
        currency: str,
        description: str,
        payment_method: PaymentMethod,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a payment request."""
        if payment_method == PaymentMethod.CRYPTO and self.coinbase_client:
            # Create Coinbase charge
            charge = self.coinbase_client.create_charge(
                name=description,
                description=description,
                pricing_type="fixed_price",
                local_price={
                    "amount": str(amount),
                    "currency": currency
                },
                metadata=metadata or {}
            )
            
            return {
                "id": charge.id,
                "payment_url": charge.hosted_url,
                "status": charge.status,
                "expires_at": charge.expires_at,
                "payment_method": PaymentMethod.CRYPTO
            }
        else:
            # Handle other payment methods or return error
            raise NotImplementedError(f"Payment method {payment_method} not implemented")

    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Check payment status."""
        if self.coinbase_client:
            try:
                charge = self.coinbase_client.get_charge(payment_id)
                return {
                    "status": charge.status,
                    "paid": charge.payments and any(p.status == "confirmed" for p in charge.payments),
                    "amount_paid": charge.payments[0].value.amount if charge.payments else 0,
                    "currency": charge.payments[0].value.currency if charge.payments else None
                }
            except Exception as e:
                logger.error(f"Error checking payment status: {e}")
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Payment provider not configured"}

class TeamManager:
    def __init__(self, coinbase_api_key: Optional[str] = None, coinbase_api_secret: Optional[str] = None):
        self.collaborators: Dict[str, CollaboratorProfile] = {}
        self.projects: Dict[str, Project] = {}
        self.payments: Dict[str, PaymentRequest] = {}
        self.collaborator_requests: List[Dict[str, Any]] = []
        self.external_db = None  # Will be initialized with Supabase
        self.market_rates: Dict[str, List[RateRange]] = {}
        self.payment_manager = PaymentManager(coinbase_api_key, coinbase_api_secret)

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
            payment_method=PaymentMethod.CRYPTO,
            metadata={
                "collaborator_id": request.collaborator_id,
                "payment_request_id": request.id
            }
        )
        
        # Update payment request with provider details
        request.payment_method = PaymentMethod.CRYPTO
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