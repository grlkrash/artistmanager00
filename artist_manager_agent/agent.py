from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from .team_management import TeamMember, CollaboratorRole
from .integrations import ServiceManager, SupabaseIntegration, TelegramIntegration, AIMasteringIntegration

class ArtistProfile(BaseModel):
    """Artist profile information."""
    name: str
    genre: str
    career_stage: str
    goals: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]
    achievements: List[str]
    social_media: Dict[str, str] = {}
    streaming_profiles: Dict[str, str] = {}
    health_notes: List[str] = []
    brand_guidelines: Dict[str, Any] = {}
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class Contract(BaseModel):
    """Contract information."""
    title: str
    parties: List[str]
    terms: Dict[str, Any]
    status: str
    value: float
    expiration: datetime

class FinancialRecord(BaseModel):
    """Financial record information."""
    date: datetime
    type: str
    amount: float
    category: str
    description: str

class Event(BaseModel):
    """Event information."""
    title: str
    type: str
    date: datetime
    venue: str
    capacity: int
    budget: float
    status: str

class Task(BaseModel):
    """Task information."""
    title: str
    description: str
    deadline: datetime
    assigned_to: str
    status: str
    priority: int
    dependencies: List[str] = []
    notes: List[str] = []

class ArtistManagerAgent:
    """Main agent for managing artists."""
    
    def __init__(
        self,
        artist_profile: ArtistProfile,
        openai_api_key: str,
        model: str = "gpt-4-turbo-preview",
        db_url: Optional[str] = None,
        telegram_token: Optional[str] = None,
        ai_mastering_key: Optional[str] = None
    ):
        self.artist = artist_profile
        self.team: List[TeamMember] = []
        self.tasks: List[Task] = []
        self.contracts: List[Contract] = []
        self.events: List[Event] = []
        self.finances: List[FinancialRecord] = []
        self.llm = ChatOpenAI(
            model=model,
            openai_api_key=openai_api_key,
            temperature=0.7
        )
        self.services = ServiceManager()
        self._init_external_services(db_url, telegram_token, ai_mastering_key)

    async def create_artist(self, artist_id: str, name: str, **kwargs) -> ArtistProfile:
        if artist_id in self.artists:
            raise ValueError(f"Artist with ID {artist_id} already exists")
        
        profile = ArtistProfile(artist_id=artist_id, name=name, **kwargs)
        self.artists[artist_id] = profile
        return profile

    async def get_artist(self, artist_id: str) -> Optional[ArtistProfile]:
        return self.artists.get(artist_id)

    async def update_artist(self, artist_id: str, **kwargs) -> Optional[ArtistProfile]:
        if artist_id not in self.artists:
            return None
        
        profile = self.artists[artist_id]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now()
        return profile

    async def delete_artist(self, artist_id: str) -> bool:
        if artist_id in self.artists:
            del self.artists[artist_id]
            return True
        return False 