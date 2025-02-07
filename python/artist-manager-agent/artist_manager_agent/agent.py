from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from cdp_agentkit_core import Agent
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from .mastering import AIMasteringIntegration
from .integrations import ServiceManager, SupabaseIntegration, TelegramIntegration
import asyncio

class Contract(BaseModel):
    title: str
    parties: List[str]
    terms: Dict[str, Any]
    status: str
    value: float
    expiration: datetime

class FinancialRecord(BaseModel):
    date: datetime
    type: str
    amount: float
    category: str
    description: str

class Event(BaseModel):
    title: str
    type: str
    date: datetime
    venue: str
    capacity: int
    budget: float
    status: str

class ArtistProfile(BaseModel):
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

class TeamMember(BaseModel):
    name: str
    role: str
    skills: List[str]
    performance_metrics: Dict[str, float]
    contact_info: Dict[str, str] = {}
    availability: Dict[str, List[str]] = {}

class Task(BaseModel):
    title: str
    description: str
    deadline: datetime
    assigned_to: str
    status: str
    priority: int
    dependencies: List[str] = []
    notes: List[str] = []

class ArtistManagerAgent(Agent):
    def __init__(
        self,
        artist_profile: ArtistProfile,
        openai_api_key: str,
        model: str = "gpt-4-turbo-preview",
        db_url: Optional[str] = None,
        telegram_token: Optional[str] = None,
        ai_mastering_key: Optional[str] = None
    ):
        super().__init__()
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

    async def _init_external_services(
        self,
        db_url: Optional[str],
        telegram_token: Optional[str],
        ai_mastering_key: Optional[str]
    ) -> None:
        """Initialize external service clients."""
        if db_url:
            supabase = SupabaseIntegration(db_url, db_url)  # Key is same as URL for now
            await self.services.initialize_service("supabase", supabase)

        if telegram_token:
            telegram = TelegramIntegration(telegram_token, self)
            await self.services.initialize_service("telegram", telegram)

        if ai_mastering_key:
            mastering = AIMasteringIntegration(ai_mastering_key)
            await self.services.initialize_service("mastering", mastering)

    async def provide_guidance(self, situation: str) -> str:
        """Provide emotionally intelligent guidance based on the situation."""
        messages = [
            SystemMessage(content=f"""You are a supportive and empathetic artist manager for {self.artist.name}.
            Your artist works in {self.artist.genre} and is currently at {self.artist.career_stage} stage.
            Their main goals are: {', '.join(self.artist.goals)}.
            Consider their health notes: {', '.join(self.artist.health_notes)}
            Provide guidance that is both encouraging and practical."""),
            HumanMessage(content=situation)
        ]
        response = await self.llm.agenerate([messages])
        return response.generations[0][0].text

    async def create_strategy(self) -> Dict[str, List[str]]:
        """Generate a strategic plan based on artist's goals and market analysis."""
        messages = [
            SystemMessage(content=f"""Analyze the following artist profile and create a detailed strategy:
            Artist: {self.artist.dict()}
            Team: {[member.dict() for member in self.team]}
            Current Tasks: {[task.dict() for task in self.tasks]}
            Create a structured plan with specific actionable steps."""),
            HumanMessage(content="Generate a strategic plan with specific milestones and actions.")
        ]
        response = await self.llm.agenerate([messages])
        return {"strategy": response.generations[0][0].text.split("\n")}

    async def negotiate_contract(self, contract_details: Dict[str, Any]) -> Contract:
        """Negotiate and evaluate contract terms."""
        messages = [
            SystemMessage(content=f"""Evaluate and negotiate this contract for {self.artist.name}:
            Artist Stage: {self.artist.career_stage}
            Contract Details: {contract_details}
            Consider market rates and artist's best interests."""),
            HumanMessage(content="Analyze contract terms and suggest negotiations.")
        ]
        response = await self.llm.agenerate([messages])
        # Process response and create contract
        return Contract(**contract_details)

    async def plan_event(self, event_type: str, details: Dict[str, Any]) -> Event:
        """Plan and organize an event."""
        messages = [
            SystemMessage(content=f"""Plan this {event_type} event for {self.artist.name}:
            Details: {details}
            Consider logistics, budget, and artist's schedule."""),
            HumanMessage(content="Create a detailed event plan.")
        ]
        response = await self.llm.agenerate([messages])
        # Process response and create event
        return Event(**details)

    async def manage_crisis(self, situation: str) -> Dict[str, Any]:
        """Handle crisis situations and conflicts."""
        messages = [
            SystemMessage(content=f"""Handle this crisis situation for {self.artist.name}:
            Situation: {situation}
            Artist Profile: {self.artist.dict()}
            Consider PR impact and artist's wellbeing."""),
            HumanMessage(content="Provide crisis management strategy.")
        ]
        response = await self.llm.agenerate([messages])
        return {
            "strategy": response.generations[0][0].text,
            "timestamp": datetime.now().isoformat()
        }

    def record_financial_transaction(self, transaction: FinancialRecord) -> None:
        """Record a financial transaction."""
        self.finances.append(transaction)

    def update_health_notes(self, note: str) -> None:
        """Update artist's health notes."""
        self.artist.health_notes.append(f"{datetime.now().isoformat()}: {note}")

    def assign_task(self, task: Task) -> bool:
        """Assign a task to a team member."""
        if any(member.name == task.assigned_to for member in self.team):
            self.tasks.append(task)
            return True
        return False

    async def evaluate_opportunity(self, opportunity: str) -> Dict[str, any]:
        """Evaluate a business opportunity for the artist."""
        messages = [
            SystemMessage(content=f"""Evaluate this opportunity for {self.artist.name}:
            Consider their current career stage: {self.artist.career_stage}
            Their goals: {', '.join(self.artist.goals)}
            Provide a detailed analysis and recommendation."""),
            HumanMessage(content=opportunity)
        ]
        response = await self.llm.agenerate([messages])
        return {
            "analysis": response.generations[0][0].text,
            "timestamp": datetime.now().isoformat()
        }

    def add_team_member(self, member: TeamMember) -> None:
        """Add a new team member."""
        self.team.append(member)

    def get_task_status(self) -> Dict[str, List[Task]]:
        """Get the current status of all tasks."""
        status_dict: Dict[str, List[Task]] = {}
        for task in self.tasks:
            if task.status not in status_dict:
                status_dict[task.status] = []
            status_dict[task.status].append(task)
        return status_dict

    async def handle_telegram_message(self, message: str, user_id: str) -> str:
        """Process incoming Telegram messages."""
        # For non-command messages, treat them as requests for guidance
        response = await self.provide_guidance(message)
        return response

    async def sync_to_database(self) -> None:
        """Sync agent state to database."""
        # To be implemented: Sync state to Supabase
        pass

    async def master_track(
        self,
        track_url: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Master a track using AI."""
        mastering = self.services.get_service("mastering")
        if not mastering:
            raise RuntimeError("AI mastering service not available")

        # Start mastering job
        job = await mastering.start_mastering(track_url, options)
        
        # Create a task to track the mastering progress
        task = Task(
            title=f"Master track: {track_url.split('/')[-1]}",
            description="AI mastering in progress",
            deadline=datetime.now(),
            assigned_to="AI Mastering",
            status="in_progress",
            priority=2
        )
        self.assign_task(task)

        # Monitor job status
        while True:
            status = await mastering.get_mastering_status(job['id'])
            if status['status'] == 'completed':
                task.status = "completed"
                download_url = await mastering.get_mastered_track(job['id'])
                comparison = await mastering.compare_versions(track_url, download_url)
                return {
                    "status": "completed",
                    "download_url": download_url,
                    "comparison": comparison
                }
            elif status['status'] == 'failed':
                task.status = "failed"
                return {
                    "status": "failed",
                    "error": status.get('error', 'Unknown error')
                }
            
            await asyncio.sleep(5) 