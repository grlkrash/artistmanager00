from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, EmailStr
import uuid

class CollaboratorRole(str, Enum):
    """Possible roles for team members."""
    PRODUCER = "producer"
    MIXING_ENGINEER = "mixing_engineer"
    MASTERING_ENGINEER = "mastering_engineer"
    VOCAL_COACH = "vocal_coach"
    SESSION_MUSICIAN = "session_musician"
    SONGWRITER = "songwriter"
    PHOTOGRAPHER = "photographer"
    VIDEOGRAPHER = "videographer"
    PR_MANAGER = "pr_manager"
    TOUR_MANAGER = "tour_manager"
    SOCIAL_MEDIA_MANAGER = "social_media_manager"
    LEGAL_ADVISOR = "legal_advisor"
    OTHER = "other"

class PaymentStatus(str, Enum):
    """Payment status tracking."""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"

class CollaboratorProfile(BaseModel):
    """Team member profile information."""
    id: str = None
    name: str
    role: CollaboratorRole
    email: EmailStr
    phone: Optional[str] = None
    rate: Optional[float] = None
    rate_type: Optional[str] = None  # hourly, per_project, per_session
    expertise: List[str] = []
    availability: Dict[str, List[str]] = {}  # day: [time_slots]
    portfolio_link: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[float] = None
    past_projects: List[str] = []
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid.uuid4())

class PaymentRequest(BaseModel):
    """Track payment requests and status."""
    id: str = None
    collaborator_id: str
    amount: float
    currency: str = "USD"
    description: str
    due_date: datetime
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = None
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    invoice_link: Optional[str] = None
    notes: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class Project(BaseModel):
    """Track project details and team assignments."""
    id: str = None
    name: str
    description: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "active"
    team_members: List[str] = []  # collaborator_ids
    budget: Optional[float] = None
    deliverables: List[str] = []
    milestones: List[Dict] = []
    notes: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid.uuid4())

class TeamManager:
    """Manage team members, projects, and payments."""
    
    def __init__(self):
        self.collaborators: Dict[str, CollaboratorProfile] = {}
        self.projects: Dict[str, Project] = {}
        self.payments: Dict[str, PaymentRequest] = {}
        
    async def add_collaborator(self, profile: CollaboratorProfile) -> str:
        """Add a new team member."""
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
        """Update collaborator information."""
        if collaborator_id not in self.collaborators:
            return None
            
        collaborator = self.collaborators[collaborator_id]
        for key, value in updates.items():
            if hasattr(collaborator, key):
                setattr(collaborator, key, value)
                
        return collaborator
        
    async def remove_collaborator(self, collaborator_id: str) -> bool:
        """Remove a team member."""
        if collaborator_id in self.collaborators:
            del self.collaborators[collaborator_id]
            return True
        return False
        
    async def create_project(self, project: Project) -> str:
        """Create a new project."""
        self.projects[project.id] = project
        return project.id
        
    async def assign_to_project(
        self,
        project_id: str,
        collaborator_id: str
    ) -> bool:
        """Assign a team member to a project."""
        if (project_id not in self.projects or 
            collaborator_id not in self.collaborators):
            return False
            
        if collaborator_id not in self.projects[project_id].team_members:
            self.projects[project_id].team_members.append(collaborator_id)
        return True
        
    async def create_payment_request(self, request: PaymentRequest) -> str:
        """Create a new payment request."""
        self.payments[request.id] = request
        return request.id
        
    async def update_payment_status(
        self,
        payment_id: str,
        status: PaymentStatus,
        notes: Optional[str] = None
    ) -> Optional[PaymentRequest]:
        """Update payment request status."""
        if payment_id not in self.payments:
            return None
            
        payment = self.payments[payment_id]
        payment.status = status
        
        if status == PaymentStatus.PAID:
            payment.paid_at = datetime.now()
            
        if notes:
            payment.notes = notes
            
        return payment
        
    async def get_team_availability(
        self,
        role: Optional[CollaboratorRole] = None,
        date_range: Optional[tuple] = None
    ) -> Dict[str, Dict]:
        """Get team member availability, optionally filtered by role."""
        availability = {}
        
        for collaborator in self.collaborators.values():
            if role and collaborator.role != role:
                continue
                
            availability[collaborator.id] = {
                "name": collaborator.name,
                "role": collaborator.role,
                "availability": collaborator.availability
            }
            
        return availability
        
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
        
    async def get_pending_payments(
        self,
        collaborator_id: Optional[str] = None
    ) -> List[PaymentRequest]:
        """Get pending payment requests."""
        pending = [
            payment for payment in self.payments.values()
            if payment.status == PaymentStatus.PENDING
        ]
        
        if collaborator_id:
            pending = [
                payment for payment in pending
                if payment.collaborator_id == collaborator_id
            ]
            
        return pending
        
    async def generate_collaboration_message(
        self,
        collaborator_id: str,
        project_id: str,
        message_type: str
    ) -> str:
        """Generate a professional message for team communication."""
        collaborator = await self.get_collaborator(collaborator_id)
        project = self.projects.get(project_id)
        
        if not collaborator or not project:
            return "Error: Invalid collaborator or project ID"
            
        templates = {
            "invitation": f"""
Hi {collaborator.name},

I hope this message finds you well. We're working on an exciting project called "{project.name}" and would love to have you join us as our {collaborator.role.value}.

Project Details:
- Description: {project.description}
- Timeline: {project.start_date.strftime('%B %d, %Y')} to {project.end_date.strftime('%B %d, %Y') if project.end_date else 'TBD'}
- Deliverables: {', '.join(project.deliverables)}

Would you be available to discuss this opportunity further? We can schedule a call at your convenience to go over the details and your potential involvement.

Looking forward to your response!

Best regards,
[Artist Name]
            """.strip(),
            
            "brief": f"""
Project Brief: {project.name}

Dear {collaborator.name},

Here are the key details for your role as {collaborator.role.value}:

Project Overview:
{project.description}

Key Deliverables:
{chr(10).join(f"- {item}" for item in project.deliverables)}

Timeline:
Start: {project.start_date.strftime('%B %d, %Y')}
End: {project.end_date.strftime('%B %d, %Y') if project.end_date else 'TBD'}

Milestones:
{chr(10).join(f"- {m['name']}: {m['date']}" for m in project.milestones)}

Please review and let me know if you have any questions or need clarification.

Best regards,
[Artist Name]
            """.strip(),
            
            "feedback": f"""
Hi {collaborator.name},

I wanted to touch base regarding the {project.name} project. Your work has been instrumental in moving this forward, and I appreciate your dedication.

Would you be available for a quick sync to discuss the current progress and any adjustments needed?

Best regards,
[Artist Name]
            """.strip()
        }
        
        return templates.get(message_type, "Message template not found.")
        
    async def scout_collaborators(
        self,
        role: CollaboratorRole,
        expertise: List[str],
        budget_range: Optional[tuple] = None
    ) -> List[CollaboratorProfile]:
        """Find suitable collaborators based on criteria."""
        matches = []
        
        for collaborator in self.collaborators.values():
            if collaborator.role != role:
                continue
                
            # Check expertise match
            expertise_match = any(
                skill in collaborator.expertise 
                for skill in expertise
            )
            
            # Check budget if specified
            budget_match = True
            if budget_range and collaborator.rate:
                min_budget, max_budget = budget_range
                budget_match = min_budget <= collaborator.rate <= max_budget
                
            if expertise_match and budget_match:
                matches.append(collaborator)
                
        return matches
        
    async def get_project_status(self, project_id: str) -> Dict:
        """Get detailed project status and progress."""
        if project_id not in self.projects:
            return {"error": "Project not found"}
            
        project = self.projects[project_id]
        team = await self.get_project_team(project_id)
        
        # Calculate progress
        total_milestones = len(project.milestones)
        completed_milestones = sum(
            1 for m in project.milestones 
            if m.get("status") == "completed"
        )
        
        progress = (completed_milestones / total_milestones * 100) if total_milestones else 0
        
        return {
            "project_name": project.name,
            "status": project.status,
            "progress": progress,
            "team_members": [
                {
                    "name": member.name,
                    "role": member.role,
                    "status": "active"
                }
                for member in team
            ],
            "upcoming_milestones": [
                m for m in project.milestones
                if m.get("status") != "completed"
            ],
            "budget_status": {
                "total": project.budget,
                "spent": sum(
                    payment.amount
                    for payment in self.payments.values()
                    if payment.status == PaymentStatus.PAID
                )
            }
        } 