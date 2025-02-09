from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import uuid
from enum import Enum

class BaseModelWithId(BaseModel):
    """Base model with ID field and hash support."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier")
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.id == other.id

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

class FinancialRecord(BaseModelWithId):
    """Model for financial record keeping."""
    date: datetime
    type: str  # income, expense
    amount: float
    category: str
    description: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

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

class Track(BaseModelWithId):
    """Represents a music track."""
    title: str
    artist: str
    duration: int  # in seconds
    genre: Optional[str] = None
    release_date: Optional[datetime] = None
    streaming_url: Optional[str] = None
    download_url: Optional[str] = None
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

class MasteringPreset(BaseModelWithId):
    """Represents a mastering preset configuration."""
    name: str
    description: Optional[str] = None
    settings: Dict[str, Any] = {
        "loudness": -14.0,  # LUFS
        "true_peak": -1.0,  # dB
        "bass_boost": 0.0,  # dB
        "high_boost": 0.0,  # dB
        "stereo_width": 100,  # %
        "compression": 0.5,  # ratio
    }
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

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