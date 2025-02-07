from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from pydantic import BaseModel
import random

class HealthMetric(BaseModel):
    """Track a specific health metric."""
    name: str
    value: Union[int, float]
    timestamp: datetime
    notes: Optional[str] = None
    sentiment: Optional[str] = None  # positive, neutral, negative

class WellnessCheck(BaseModel):
    """Daily wellness check data."""
    date: datetime
    sleep_hours: float
    stress_level: int  # 1-5
    energy_level: int  # 1-5
    vocal_health: int  # 1-5
    exercise_minutes: int
    water_intake: float  # liters
    mood: str
    notes: Optional[str] = None

class HealthTracker:
    """Personal health tracking with supportive communication."""
    
    def __init__(self):
        self.wellness_history: List[WellnessCheck] = []
        self.metrics_history: Dict[str, List[HealthMetric]] = {}
        self.reminders: List[Dict] = []
        self.encouragement_messages = [
            "Taking care of yourself is just as important as your music. Keep it up! 🌟",
            "Your health is your greatest instrument. You're doing great! 💪",
            "Rest is not the enemy of productivity - it's fuel for creativity! 🎵",
            "Small steps lead to big changes. Proud of your commitment! ✨",
            "Your wellbeing matters. Thanks for prioritizing your health! 🙏"
        ]
        self.concern_messages = [
            "I notice you've been pushing pretty hard lately. Want to talk about it?",
            "Your energy seems a bit low. Let's find ways to help you recharge.",
            "Sometimes the most productive thing you can do is rest. How can I help?",
            "Your health is crucial for your art. Let's make sure you're taking care of yourself.",
            "I'm here to support you. What do you need right now?"
        ]

    async def add_wellness_check(self, check: WellnessCheck) -> str:
        """Add a daily wellness check and get personalized feedback."""
        self.wellness_history.append(check)
        
        # Analyze the check and generate supportive feedback
        feedback = []
        concerns = []
        
        # Sleep analysis
        if check.sleep_hours < 6:
            concerns.append("sleep")
            feedback.append("I notice you're getting less sleep than usual. "
                          "Even a small increase in sleep can boost your creativity and energy.")
        elif check.sleep_hours >= 8:
            feedback.append("Great job prioritizing sleep! Your body and mind will thank you.")

        # Stress analysis
        if check.stress_level >= 4:
            concerns.append("stress")
            feedback.append("Your stress levels seem high. Would you like to explore some "
                          "relaxation techniques that work well for musicians?")
        
        # Vocal health
        if check.vocal_health <= 2:
            concerns.append("vocal")
            feedback.append("Your vocal health needs some attention. Let's make sure "
                          "you're protecting your instrument.")
        
        # Water intake
        if check.water_intake < 2:
            concerns.append("hydration")
            feedback.append("Try to increase your water intake - it's crucial for "
                          "vocal health and overall energy.")

        # Generate response
        response = self._format_wellness_response(
            feedback, 
            concerns,
            check
        )
        
        # Set reminders if needed
        self._set_health_reminders(concerns)
        
        return response

    def _format_wellness_response(
        self, 
        feedback: List[str],
        concerns: List[str],
        check: WellnessCheck
    ) -> str:
        """Format a personalized wellness response."""
        
        # Start with a mood-appropriate greeting
        if check.mood.lower() in ['great', 'happy', 'excited']:
            response = ["That's wonderful to hear! 🌟"]
        elif check.mood.lower() in ['tired', 'exhausted', 'stressed']:
            response = ["I hear you. Those days can be tough. 💙"]
        else:
            response = ["Thanks for checking in! 💫"]
            
        # Add specific feedback
        if feedback:
            response.extend(feedback)
            
        # Add encouragement or support based on overall state
        if len(concerns) >= 2:
            response.append(random.choice(self.concern_messages))
        else:
            response.append(random.choice(self.encouragement_messages))
            
        # Add actionable suggestion if needed
        if concerns:
            response.append(self._get_health_suggestion(concerns[0]))
            
        return "\n\n".join(response)

    def _get_health_suggestion(self, concern: str) -> str:
        """Get a specific suggestion based on the health concern."""
        suggestions = {
            "sleep": [
                "Try setting a gentle bedtime reminder 30 minutes before you want to sleep.",
                "Consider a calming bedtime routine - maybe some light stretching or meditation.",
                "Even a 20-minute power nap during the day can help recover lost sleep."
            ],
            "stress": [
                "Let's take 5 minutes for some deep breathing exercises.",
                "How about a short walk to clear your mind between sessions?",
                "Music can heal - try listening to something calming during breaks."
            ],
            "vocal": [
                "Remember to warm up gradually before intensive vocal sessions.",
                "Steam inhalation can help soothe your vocal cords.",
                "Consider scheduling a check-up with your vocal coach."
            ],
            "hydration": [
                "Try keeping a water bottle at your workspace.",
                "Set hourly water break reminders during recording sessions.",
                "Herbal teas count toward hydration - find ones you enjoy!"
            ]
        }
        return random.choice(suggestions.get(concern, [
            "Let's take a moment to check in with yourself and see what you need."
        ]))

    def _set_health_reminders(self, concerns: List[str]) -> None:
        """Set appropriate health reminders based on concerns."""
        reminder_templates = {
            "sleep": {
                "title": "Bedtime Reminder",
                "message": "Time to start winding down for a restful night! 🌙",
                "frequency": "daily"
            },
            "stress": {
                "title": "Mindfulness Break",
                "message": "Take a moment to breathe and center yourself 🧘",
                "frequency": "daily"
            },
            "vocal": {
                "title": "Vocal Rest",
                "message": "Remember to give your voice regular breaks 🎤",
                "frequency": "hourly"
            },
            "hydration": {
                "title": "Hydration Check",
                "message": "Time for a water break! 💧",
                "frequency": "2_hours"
            }
        }
        
        for concern in concerns:
            if concern in reminder_templates:
                self.reminders.append(reminder_templates[concern])

    async def get_health_insights(self, days: int = 7) -> str:
        """Get insights from recent health tracking data."""
        if not self.wellness_history:
            return "No health data available yet. Start tracking to get insights!"
            
        recent_checks = [
            check for check in self.wellness_history 
            if (datetime.now() - check.date).days <= days
        ]
        
        if not recent_checks:
            return f"No health data available for the last {days} days."
            
        # Calculate averages
        avg_sleep = sum(check.sleep_hours for check in recent_checks) / len(recent_checks)
        avg_stress = sum(check.stress_level for check in recent_checks) / len(recent_checks)
        avg_energy = sum(check.energy_level for check in recent_checks) / len(recent_checks)
        avg_vocal = sum(check.vocal_health for check in recent_checks) / len(recent_checks)
        
        # Generate insights
        insights = [
            f"📊 Your Health Overview (Last {days} days)",
            "",
            f"😴 Sleep: {avg_sleep:.1f} hours on average",
            f"😓 Stress Level: {avg_stress:.1f}/5",
            f"⚡ Energy Level: {avg_energy:.1f}/5",
            f"🎤 Vocal Health: {avg_vocal:.1f}/5",
            "",
            "Key Observations:"
        ]
        
        # Add specific insights
        if avg_sleep < 7:
            insights.append("• You might benefit from a bit more sleep")
        if avg_stress > 3:
            insights.append("• Your stress levels have been elevated")
        if avg_vocal < 3:
            insights.append("• Your vocal health could use some attention")
        if avg_energy < 3:
            insights.append("• Your energy levels have been running low")
            
        # Add positive reinforcement
        if any(check.sleep_hours >= 8 for check in recent_checks):
            insights.append("• Great job getting proper rest on some days!")
        if any(check.stress_level <= 2 for check in recent_checks):
            insights.append("• You've had some good low-stress days!")
            
        # Add a supportive closing message
        insights.extend([
            "",
            "Remember: Your health is the foundation of your artistry. "
            "Small, consistent steps lead to lasting wellbeing. 💫"
        ])
        
        return "\n".join(insights)

    async def get_active_reminders(self) -> List[Dict]:
        """Get current active health reminders."""
        return self.reminders

    async def add_metric(
        self,
        name: str,
        value: Union[int, float],
        notes: Optional[str] = None,
        sentiment: Optional[str] = None
    ) -> None:
        """Add a custom health metric."""
        metric = HealthMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            notes=notes,
            sentiment=sentiment
        )
        
        if name not in self.metrics_history:
            self.metrics_history[name] = []
            
        self.metrics_history[name].append(metric)

    async def get_metric_history(
        self,
        metric_name: str,
        days: int = 30
    ) -> List[HealthMetric]:
        """Get history for a specific metric."""
        if metric_name not in self.metrics_history:
            return []
            
        cutoff = datetime.now() - timedelta(days=days)
        return [
            metric for metric in self.metrics_history[metric_name]
            if metric.timestamp >= cutoff
        ] 