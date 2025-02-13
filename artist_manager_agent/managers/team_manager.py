"""Team management functionality for the Artist Manager Bot."""
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from ..models import (
    CollaboratorProfile, PaymentRequest, PerformanceMetric,
    TeamSchedule, CollaboratorRole
)
import uuid

logger = logging.getLogger(__name__)

class TeamManager:
    """Manages team members and collaborators."""
    
    def __init__(self, team_id: str):
        self.team_id = team_id
        self.collaborators: Dict[str, CollaboratorProfile] = {}
        self.payment_requests: List[PaymentRequest] = []
        self.performance_metrics: Dict[str, List[PerformanceMetric]] = {}
        self.schedules: Dict[str, List[TeamSchedule]] = {}
        
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

    async def add_performance_metric(
        self,
        collaborator_id: str,
        metric_type: str,
        value: float,
        period_start: datetime,
        period_end: datetime,
        notes: str = ""
    ) -> PerformanceMetric:
        """Add a performance metric for a team member."""
        if collaborator_id not in self.collaborators:
            raise ValueError(f"Collaborator with ID {collaborator_id} not found")
            
        metric = PerformanceMetric(
            id=str(uuid.uuid4()),
            collaborator_id=collaborator_id,
            metric_type=metric_type,
            value=value,
            period_start=period_start,
            period_end=period_end,
            notes=notes
        )
        
        if collaborator_id not in self.performance_metrics:
            self.performance_metrics[collaborator_id] = []
            
        self.performance_metrics[collaborator_id].append(metric)
        return metric

    async def get_performance_metrics(
        self,
        collaborator_id: str,
        metric_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PerformanceMetric]:
        """Get performance metrics for a team member."""
        if collaborator_id not in self.collaborators:
            raise ValueError(f"Collaborator with ID {collaborator_id} not found")
            
        metrics = self.performance_metrics.get(collaborator_id, [])
        
        # Apply filters
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        if start_date:
            metrics = [m for m in metrics if m.period_end >= start_date]
        if end_date:
            metrics = [m for m in metrics if m.period_start <= end_date]
            
        return sorted(metrics, key=lambda x: x.period_start, reverse=True)

    async def add_schedule_event(
        self,
        collaborator_id: str,
        event_type: str,
        start_time: datetime,
        end_time: datetime,
        notes: str = ""
    ) -> TeamSchedule:
        """Add a schedule event for a team member."""
        if collaborator_id not in self.collaborators:
            raise ValueError(f"Collaborator with ID {collaborator_id} not found")
            
        # Check for conflicts
        existing_events = self.schedules.get(collaborator_id, [])
        for event in existing_events:
            if (
                (start_time <= event.start_time <= end_time) or
                (start_time <= event.end_time <= end_time) or
                (event.start_time <= start_time <= event.end_time)
            ):
                raise ValueError("Schedule conflict detected")
                
        event = TeamSchedule(
            id=str(uuid.uuid4()),
            collaborator_id=collaborator_id,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            status="scheduled",
            notes=notes
        )
        
        if collaborator_id not in self.schedules:
            self.schedules[collaborator_id] = []
            
        self.schedules[collaborator_id].append(event)
        return event

    async def get_schedule(
        self,
        collaborator_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TeamSchedule]:
        """Get schedule for a team member."""
        if collaborator_id not in self.collaborators:
            raise ValueError(f"Collaborator with ID {collaborator_id} not found")
            
        events = self.schedules.get(collaborator_id, [])
        
        # Apply date filters
        if start_date:
            events = [e for e in events if e.end_time >= start_date]
        if end_date:
            events = [e for e in events if e.start_time <= end_date]
            
        return sorted(events, key=lambda x: x.start_time)

    async def update_schedule_event(
        self,
        event_id: str,
        collaborator_id: str,
        updates: Dict[str, Any]
    ) -> Optional[TeamSchedule]:
        """Update a schedule event."""
        if collaborator_id not in self.collaborators:
            raise ValueError(f"Collaborator with ID {collaborator_id} not found")
            
        events = self.schedules.get(collaborator_id, [])
        for i, event in enumerate(events):
            if event.id == event_id:
                # Check for conflicts if time is being updated
                if "start_time" in updates or "end_time" in updates:
                    start_time = updates.get("start_time", event.start_time)
                    end_time = updates.get("end_time", event.end_time)
                    for other_event in events:
                        if other_event.id != event_id:
                            if (
                                (start_time <= other_event.start_time <= end_time) or
                                (start_time <= other_event.end_time <= end_time) or
                                (other_event.start_time <= start_time <= other_event.end_time)
                            ):
                                raise ValueError("Schedule conflict detected")
                                
                # Update event
                for key, value in updates.items():
                    if hasattr(event, key):
                        setattr(event, key, value)
                return event
                
        return None

    async def cancel_schedule_event(
        self,
        event_id: str,
        collaborator_id: str
    ) -> bool:
        """Cancel a schedule event."""
        if collaborator_id not in self.collaborators:
            raise ValueError(f"Collaborator with ID {collaborator_id} not found")
            
        events = self.schedules.get(collaborator_id, [])
        for event in events:
            if event.id == event_id:
                event.status = "cancelled"
                return True
                
        return False

    async def get_team_availability(
        self,
        start_date: datetime,
        end_date: datetime,
        role: Optional[CollaboratorRole] = None
    ) -> Dict[str, List[Dict[str, datetime]]]:
        """Get availability for all team members."""
        availability = {}
        
        for collaborator_id, collaborator in self.collaborators.items():
            # Filter by role if specified
            if role and collaborator.role != role:
                continue
                
            # Get scheduled events
            events = await self.get_schedule(
                collaborator_id=collaborator_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Convert to free time slots
            busy_times = [(e.start_time, e.end_time) for e in events if e.status != "cancelled"]
            free_times = []
            
            current_time = start_date
            for busy_start, busy_end in sorted(busy_times):
                if current_time < busy_start:
                    free_times.append({
                        "start": current_time,
                        "end": busy_start
                    })
                current_time = busy_end
                
            if current_time < end_date:
                free_times.append({
                    "start": current_time,
                    "end": end_date
                })
                
            availability[collaborator_id] = free_times
            
        return availability

    async def get_performance_summary(
        self,
        collaborator_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Get performance summary for a team member."""
        if collaborator_id not in self.collaborators:
            raise ValueError(f"Collaborator with ID {collaborator_id} not found")
            
        metrics = await self.get_performance_metrics(
            collaborator_id=collaborator_id,
            start_date=period_start,
            end_date=period_end
        )
        
        # Calculate averages by metric type
        summary = {}
        for metric in metrics:
            if metric.metric_type not in summary:
                summary[metric.metric_type] = {
                    "values": [],
                    "average": 0,
                    "trend": 0
                }
            summary[metric.metric_type]["values"].append(metric.value)
            
        # Calculate averages and trends
        for metric_type in summary:
            values = summary[metric_type]["values"]
            summary[metric_type]["average"] = sum(values) / len(values)
            
            # Calculate trend (positive or negative)
            if len(values) > 1:
                trend = values[-1] - values[0]  # Compare latest to earliest
                summary[metric_type]["trend"] = trend
                
        return summary 