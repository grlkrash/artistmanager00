from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel
import uuid
import pytz
from icalendar import Calendar, Event, vText

class EventType(str, Enum):
    """Types of calendar events."""
    RECORDING = "recording"
    REHEARSAL = "rehearsal"
    PERFORMANCE = "performance"
    MEETING = "meeting"
    INTERVIEW = "interview"
    PHOTOSHOOT = "photoshoot"
    VIDEOSHOOT = "videoshoot"
    TRAVEL = "travel"
    SOUNDCHECK = "soundcheck"
    PROMOTION = "promotion"
    RELEASE = "release"
    HEALTH = "health"
    OTHER = "other"

class EventPriority(str, Enum):
    """Event priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class RecurrenceType(str, Enum):
    """Types of event recurrence."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class Reminder(BaseModel):
    """Event reminder settings."""
    time: timedelta
    type: str = "notification"  # notification, email, sms
    message: Optional[str] = None

class Location(BaseModel):
    """Event location information."""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    coordinates: Optional[tuple] = None
    venue_contact: Optional[str] = None
    notes: Optional[str] = None

class CalendarEvent(BaseModel):
    """Calendar event information."""
    id: str = None
    title: str
    type: EventType
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    location: Optional[Location] = None
    description: Optional[str] = None
    priority: EventPriority = EventPriority.MEDIUM
    reminders: List[Reminder] = []
    recurrence: Optional[RecurrenceType] = None
    recurrence_end: Optional[datetime] = None
    attendees: List[str] = []
    notes: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid.uuid4())

class Schedule:
    """Manage artist's schedule and calendar."""
    
    def __init__(self, timezone: str = "UTC"):
        self.events: Dict[str, CalendarEvent] = {}
        self.default_timezone = pytz.timezone(timezone)
        self.calendar = Calendar()
        self.calendar.add('prodid', '-//Artist Manager//artistmanager.ai//')
        self.calendar.add('version', '2.0')
        
    async def add_event(self, event: CalendarEvent) -> str:
        """Add a new event to the calendar."""
        # Validate time conflicts
        if self._check_conflicts(event):
            return {
                "error": "Time conflict with existing events",
                "conflicts": self._get_conflicting_events(event)
            }
            
        # Add to events dictionary
        self.events[event.id] = event
        
        # Add to iCalendar
        cal_event = Event()
        cal_event.add('summary', event.title)
        cal_event.add('dtstart', event.start_time)
        cal_event.add('dtend', event.end_time)
        cal_event.add('priority', self._priority_to_number(event.priority))
        
        if event.location:
            cal_event.add('location', vText(event.location.name))
            
        if event.description:
            cal_event.add('description', event.description)
            
        if event.recurrence:
            cal_event.add('rrule', self._get_recurrence_rule(event))
            
        self.calendar.add_component(cal_event)
        
        return event.id
        
    async def update_event(
        self,
        event_id: str,
        updates: Dict
    ) -> Optional[CalendarEvent]:
        """Update an existing event."""
        if event_id not in self.events:
            return None
            
        event = self.events[event_id]
        
        # Check for time conflicts if time is being updated
        if ('start_time' in updates or 'end_time' in updates):
            new_event = event.copy(
                update={
                    'start_time': updates.get('start_time', event.start_time),
                    'end_time': updates.get('end_time', event.end_time)
                }
            )
            if self._check_conflicts(new_event, exclude_id=event_id):
                return {
                    "error": "Time conflict with existing events",
                    "conflicts": self._get_conflicting_events(new_event)
                }
                
        # Update event
        for key, value in updates.items():
            if hasattr(event, key):
                setattr(event, key, value)
                
        event.updated_at = datetime.now()
        
        # Update iCalendar
        self._rebuild_calendar()
        
        return event
        
    async def delete_event(self, event_id: str) -> bool:
        """Delete an event from the calendar."""
        if event_id in self.events:
            del self.events[event_id]
            self._rebuild_calendar()
            return True
        return False
        
    async def get_events(
        self,
        start_date: datetime,
        end_date: datetime,
        event_type: Optional[EventType] = None,
        priority: Optional[EventPriority] = None
    ) -> List[CalendarEvent]:
        """Get events within a date range."""
        events = []
        for event in self.events.values():
            if (event.start_time >= start_date and 
                event.end_time <= end_date):
                if event_type and event.type != event_type:
                    continue
                if priority and event.priority != priority:
                    continue
                events.append(event)
                
        return sorted(events, key=lambda x: x.start_time)
        
    async def get_conflicts(
        self,
        event: CalendarEvent,
        buffer_minutes: int = 0
    ) -> List[CalendarEvent]:
        """Get conflicting events for a time slot."""
        return self._get_conflicting_events(
            event,
            buffer_minutes=buffer_minutes
        )
        
    async def export_calendar(
        self,
        file_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> bool:
        """Export calendar to iCalendar file."""
        try:
            # Filter events if date range is specified
            if start_date and end_date:
                filtered_calendar = Calendar()
                filtered_calendar.add('prodid', self.calendar['prodid'])
                filtered_calendar.add('version', self.calendar['version'])
                
                for component in self.calendar.walk('VEVENT'):
                    event_start = component['dtstart'].dt
                    if start_date <= event_start <= end_date:
                        filtered_calendar.add_component(component)
                        
                calendar_data = filtered_calendar.to_ical()
            else:
                calendar_data = self.calendar.to_ical()
                
            with open(file_path, 'wb') as f:
                f.write(calendar_data)
                
            return True
        except Exception:
            return False
            
    async def get_availability(
        self,
        start_date: datetime,
        end_date: datetime,
        duration: timedelta,
        buffer_minutes: int = 30
    ) -> List[Dict]:
        """Find available time slots."""
        busy_periods = []
        for event in self.events.values():
            if (event.start_time <= end_date and 
                event.end_time >= start_date):
                busy_periods.append({
                    'start': event.start_time,
                    'end': event.end_time
                })
                
        # Sort busy periods
        busy_periods.sort(key=lambda x: x['start'])
        
        # Find gaps
        available_slots = []
        current_time = start_date
        
        for period in busy_periods:
            if current_time + duration <= period['start']:
                available_slots.append({
                    'start': current_time,
                    'end': period['start']
                })
            current_time = period['end']
            
        # Add final slot if needed
        if current_time + duration <= end_date:
            available_slots.append({
                'start': current_time,
                'end': end_date
            })
            
        return available_slots
        
    async def suggest_schedule(
        self,
        events: List[CalendarEvent],
        start_date: datetime,
        end_date: datetime,
        priorities: Optional[Dict[str, int]] = None
    ) -> List[CalendarEvent]:
        """Suggest optimal schedule for multiple events."""
        # Sort events by priority and duration
        if not priorities:
            priorities = {
                EventPriority.HIGH: 3,
                EventPriority.MEDIUM: 2,
                EventPriority.LOW: 1
            }
            
        sorted_events = sorted(
            events,
            key=lambda x: (
                priorities[x.priority],
                (x.end_time - x.start_time).total_seconds()
            ),
            reverse=True
        )
        
        scheduled_events = []
        for event in sorted_events:
            # Find available slots
            available_slots = await self.get_availability(
                start_date,
                end_date,
                event.end_time - event.start_time
            )
            
            if available_slots:
                # Schedule at first available slot
                slot = available_slots[0]
                event_duration = event.end_time - event.start_time
                new_event = event.copy(
                    update={
                        'start_time': slot['start'],
                        'end_time': slot['start'] + event_duration
                    }
                )
                scheduled_events.append(new_event)
                
        return scheduled_events
        
    def _check_conflicts(
        self,
        event: CalendarEvent,
        exclude_id: Optional[str] = None
    ) -> bool:
        """Check if an event conflicts with existing events."""
        return bool(
            self._get_conflicting_events(
                event,
                exclude_id=exclude_id
            )
        )
        
    def _get_conflicting_events(
        self,
        event: CalendarEvent,
        exclude_id: Optional[str] = None,
        buffer_minutes: int = 0
    ) -> List[CalendarEvent]:
        """Get list of conflicting events."""
        buffer = timedelta(minutes=buffer_minutes)
        conflicts = []
        
        for existing in self.events.values():
            if exclude_id and existing.id == exclude_id:
                continue
                
            if (
                (event.start_time - buffer <= existing.end_time) and
                (event.end_time + buffer >= existing.start_time)
            ):
                conflicts.append(existing)
                
        return conflicts
        
    def _priority_to_number(self, priority: EventPriority) -> int:
        """Convert priority enum to number for iCalendar."""
        return {
            EventPriority.HIGH: 1,
            EventPriority.MEDIUM: 5,
            EventPriority.LOW: 9
        }.get(priority, 5)
        
    def _get_recurrence_rule(self, event: CalendarEvent) -> Dict:
        """Generate recurrence rule for iCalendar."""
        rule = {
            'freq': event.recurrence.upper()
        }
        
        if event.recurrence_end:
            rule['until'] = event.recurrence_end
            
        return rule
        
    def _rebuild_calendar(self):
        """Rebuild iCalendar from events dictionary."""
        self.calendar = Calendar()
        self.calendar.add('prodid', '-//Artist Manager//artistmanager.ai//')
        self.calendar.add('version', '2.0')
        
        for event in self.events.values():
            cal_event = Event()
            cal_event.add('summary', event.title)
            cal_event.add('dtstart', event.start_time)
            cal_event.add('dtend', event.end_time)
            cal_event.add('priority', self._priority_to_number(event.priority))
            
            if event.location:
                cal_event.add('location', vText(event.location.name))
                
            if event.description:
                cal_event.add('description', event.description)
                
            if event.recurrence:
                cal_event.add('rrule', self._get_recurrence_rule(event))
                
            self.calendar.add_component(cal_event) 