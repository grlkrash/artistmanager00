from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import uuid
from enum import Enum
from pathlib import Path

class NetworkType(str, Enum):
    """Blockchain network types."""
    BASE_SEPOLIA = "base-sepolia"
    BASE_MAINNET = "base-mainnet"

class BaseModelWithId(BaseModel):
    """Base model with ID field and hash support."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier")
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.id == other.id

class Project(BaseModelWithId):
    """Model for project management."""
    title: str
    description: str
    start_date: datetime
    end_date: datetime
    status: str
    team_members: List[str]
    tasks: List[str] = []  # List of task IDs
    budget: Optional[float] = None
    milestones: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class CollaboratorRole(str, Enum):
    """Roles for team members."""
    PRODUCER = "producer"
    SONGWRITER = "songwriter"
    MUSICIAN = "musician"
    VOCALIST = "vocalist"
    ENGINEER = "engineer"
    MANAGER = "manager"
    DESIGNER = "designer"
    MARKETING = "marketing"
    OTHER = "other"

class CollaboratorProfile(BaseModelWithId):
    """Model for team member profiles."""
    name: str
    role: CollaboratorRole
    skills: List[str]
    availability: Dict[str, List[str]]  # Day of week -> time slots
    rate: Optional[float] = None
    contact_info: Dict[str, str]
    portfolio_url: Optional[str] = None
    social_media: Dict[str, str] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ArtistProfile(BaseModel):
    """Model for artist profile information."""
    id: str
    name: str
    genre: str
    career_stage: str
    goals: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]
    achievements: List[str]
    social_media: Dict[str, str]
    streaming_profiles: Dict[str, str]
    health_notes: List[str] = []
    brand_guidelines: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Task(BaseModelWithId):
    """Model for task management."""
    title: str
    description: str
    deadline: datetime
    assigned_to: str
    status: str
    priority: int
    access_level: str = "public"  # public or restricted
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Event(BaseModelWithId):
    """Model for event management."""
    title: str
    type: str
    date: datetime
    venue: str
    capacity: int
    budget: float
    status: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Contract(BaseModelWithId):
    """Model for contract information."""
    title: str
    parties: List[str]
    terms: Dict[str, Any]
    status: str
    value: float
    expiration: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class FinancialRecord(BaseModel):
    id: str
    date: datetime
    type: str
    amount: float
    currency: str
    description: str
    category: str
    payment_method: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(days=730))
    updated_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(days=730))

    @property
    def record_id(self) -> str:
        return self.id

class PaymentMethod(str, Enum):
    """Payment method options."""
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"

class PaymentStatus(str, Enum):
    """Payment status options."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentRequest(BaseModelWithId):
    """Model for payment requests."""
    collaborator_id: str
    amount: float
    currency: str
    description: str
    due_date: datetime
    payment_method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    paid_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)

class Track(BaseModel):
    """Represents a music track."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    artist: str
    duration: int  # Duration in seconds
    genre: str
    release_date: datetime
    streaming_url: Optional[str] = None
    download_url: Optional[str] = None
    file_path: Optional[Path] = None
    metadata: Dict[str, Any] = {}

class ReleaseType(str, Enum):
    """Type of music release."""
    ALBUM = "album"
    EP = "ep"
    SINGLE = "single"
    COMPILATION = "compilation"
    REMIX = "remix"

class Release(BaseModelWithId):
    """Represents a music release."""
    title: str
    artist: str
    release_date: datetime
    tracks: List[Track]
    type: ReleaseType = ReleaseType.ALBUM
    genre: Optional[str] = None
    label: Optional[str] = None
    distributor: Optional[str] = None
    cover_art_url: Optional[str] = None
    metadata: Dict[str, Any] = {}

class MasteringJob(BaseModelWithId):
    """Represents an AI mastering job."""
    track_id: str
    status: str  # pending, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    input_url: str
    output_url: Optional[str] = None
    settings: Dict[str, Any] = {}
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

class MasteringPreset(str, Enum):
    BALANCED = "balanced"
    LOUD = "loud"
    WARM = "warm"
    BRIGHT = "bright"
    BASS_BOOST = "bass_boost"

class DistributionPlatform(str, Enum):
    """Music distribution platforms."""
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    AMAZON_MUSIC = "amazon_music"
    YOUTUBE_MUSIC = "youtube_music"
    TIDAL = "tidal"
    DEEZER = "deezer"
    SOUNDCLOUD = "soundcloud"
    BANDCAMP = "bandcamp"

class NFTCollection(BaseModel):
    id: str
    name: str
    symbol: str
    base_uri: str
    contract_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    @property
    def address(self) -> str:
        """Get the contract address."""
        if not self.contract_address:
            raise ValueError("Contract address not set")
        return self.contract_address

    model_config = {
        "validate_assignment": True,
        "extra": "allow",
        "arbitrary_types_allowed": True
    }

class Token(BaseModel):
    id: str
    name: str
    symbol: str
    total_supply: str
    contract_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    @property
    def address(self) -> str:
        """Get the contract address."""
        if not self.contract_address:
            raise ValueError("Contract address not set")
        return self.contract_address

    model_config = {
        "validate_assignment": True,
        "extra": "allow",
        "arbitrary_types_allowed": True
    }

class StreamingStats(BaseModelWithId):
    """Model for streaming statistics."""
    track_id: str
    platform: DistributionPlatform
    streams: int
    unique_listeners: int
    saves: int
    playlist_adds: int
    revenue: float
    period_start: datetime
    period_end: datetime
    metadata: Dict[str, Any] = {}

class PromotionCampaign(BaseModelWithId):
    """Model for promotion campaigns."""
    title: str
    type: str  # social, playlist, pr, etc.
    target_platforms: List[str]
    budget: float
    start_date: datetime
    end_date: datetime
    status: str
    metrics: Dict[str, Any] = {}

class TransactionRecord(BaseModelWithId):
    """Model for blockchain transactions."""
    tx_hash: str
    from_address: str
    to_address: str
    amount: str
    asset: str
    gas_used: int
    gas_price: int
    status: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class GasEstimate(BaseModel):
    """Model for gas estimates."""
    operation: str
    gas_limit: int
    gas_price: int
    total_cost: float
    timestamp: datetime

class PerformanceMetric(BaseModelWithId):
    """Model for team member performance metrics."""
    collaborator_id: str
    metric_type: str
    value: float
    period_start: datetime
    period_end: datetime
    notes: str = ""
    metadata: Dict[str, Any] = {}

class TeamSchedule(BaseModelWithId):
    """Model for team scheduling."""
    collaborator_id: str
    event_type: str
    start_time: datetime
    end_time: datetime
    status: str
    notes: str = ""
    metadata: Dict[str, Any] = {}

class ResourceAllocation(BaseModelWithId):
    """Model for project resource allocation."""
    project_id: str
    resource_type: str
    amount: float
    unit: str
    start_date: datetime
    end_date: datetime
    status: str
    cost: float = 0
    metadata: Dict[str, Any] = {}

class BudgetEntry(BaseModelWithId):
    """Model for project budget tracking."""
    project_id: str
    category: str
    amount: float
    entry_type: str  # planned, actual
    date: datetime
    description: str = ""
    metadata: Dict[str, Any] = {}

class Goal(BaseModelWithId):
    """Model for goal management."""
    title: str
    description: str
    target_date: Optional[datetime]
    priority: str  # "low", "medium", "high"
    status: str  # "not_started", "in_progress", "completed"
    user_id: Optional[int] = None
    progress: int = 0  # 0-100
    tasks: List[str] = []  # List of task IDs
    metrics: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)