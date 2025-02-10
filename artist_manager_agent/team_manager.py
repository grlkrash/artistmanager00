"""Team management functionality for the Artist Manager Bot."""
from typing import Dict, List, Optional
from datetime import datetime
import logging
from .models import CollaboratorProfile, PaymentRequest

logger = logging.getLogger(__name__)

class TeamManager:
    """Manages team members and collaborators."""
    
    def __init__(self, team_id: str):
        self.team_id = team_id
        self.collaborators: Dict[str, CollaboratorProfile] = {}
        self.payment_requests: List[PaymentRequest] = []
        
    async def add_collaborator(self, profile: CollaboratorProfile) -> bool:
        """Add a new collaborator to the team."""
        try:
            self.collaborators[profile.id] = profile
            return True
        except Exception as e:
            logger.error(f"Error adding collaborator: {str(e)}")
            return False
            
    async def get_collaborator(self, collaborator_id: str) -> Optional[CollaboratorProfile]:
        """Get a collaborator by ID."""
        return self.collaborators.get(collaborator_id)
        
    async def update_collaborator(self, collaborator_id: str, updates: Dict) -> bool:
        """Update a collaborator's profile."""
        try:
            if collaborator_id not in self.collaborators:
                return False
            for key, value in updates.items():
                if hasattr(self.collaborators[collaborator_id], key):
                    setattr(self.collaborators[collaborator_id], key, value)
            return True
        except Exception as e:
            logger.error(f"Error updating collaborator: {str(e)}")
            return False
            
    async def remove_collaborator(self, collaborator_id: str) -> bool:
        """Remove a collaborator from the team."""
        try:
            if collaborator_id in self.collaborators:
                del self.collaborators[collaborator_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing collaborator: {str(e)}")
            return False
            
    async def add_payment_request(self, request: PaymentRequest) -> bool:
        """Add a new payment request."""
        try:
            self.payment_requests.append(request)
            return True
        except Exception as e:
            logger.error(f"Error adding payment request: {str(e)}")
            return False
            
    async def get_payment_requests(self, collaborator_id: Optional[str] = None) -> List[PaymentRequest]:
        """Get payment requests, optionally filtered by collaborator."""
        try:
            if collaborator_id:
                return [r for r in self.payment_requests if r.collaborator_id == collaborator_id]
            return self.payment_requests
        except Exception as e:
            logger.error(f"Error getting payment requests: {str(e)}")
            return [] 