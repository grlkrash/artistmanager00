from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class ReleasePhase(BaseModel):
    """A phase in the release process."""
    name: str
    description: str
    tasks: List[str]
    duration: timedelta
    completion: float = 0.0
    rewards: Dict[str, Any] = {}
    achievements: List[str] = []

class ReleaseProgress(BaseModel):
    """Track release progress and achievements."""
    total_points: int = 0
    achievements: List[str] = []
    streaks: Dict[str, int] = {}
    level: int = 1
    milestones_completed: List[str] = []

class ReleasePlan:
    """Gamified release plan management."""
    
    def __init__(self):
        self.phases: Dict[str, ReleasePhase] = {
            "pre_production": ReleasePhase(
                name="Pre-Production",
                description="Prepare your music and assets",
                tasks=[
                    "Finalize song selection",
                    "Complete arrangements",
                    "Book studio time",
                    "Create mood board"
                ],
                duration=timedelta(weeks=4),
                rewards={
                    "points": 100,
                    "badge": "Producer's Pick",
                    "streak_bonus": "Studio Warrior"
                }
            ),
            "production": ReleasePhase(
                name="Production",
                description="Record and polish your tracks",
                tasks=[
                    "Record vocals",
                    "Record instruments",
                    "Edit tracks",
                    "First mix review"
                ],
                duration=timedelta(weeks=6),
                rewards={
                    "points": 200,
                    "badge": "Sound Master",
                    "streak_bonus": "Studio Marathon"
                }
            ),
            "post_production": ReleasePhase(
                name="Post-Production",
                description="Perfect your sound",
                tasks=[
                    "Final mix approval",
                    "Mastering",
                    "Quality check",
                    "Create stems"
                ],
                duration=timedelta(weeks=2),
                rewards={
                    "points": 150,
                    "badge": "Perfectionist",
                    "streak_bonus": "Quality Guardian"
                }
            ),
            "artwork": ReleasePhase(
                name="Artwork & Assets",
                description="Create visual identity",
                tasks=[
                    "Design cover art",
                    "Create social assets",
                    "Design merch concepts",
                    "Shoot photos"
                ],
                duration=timedelta(weeks=3),
                rewards={
                    "points": 100,
                    "badge": "Visual Artist",
                    "streak_bonus": "Style Icon"
                }
            ),
            "marketing_prep": ReleasePhase(
                name="Marketing Prep",
                description="Plan your promotion strategy",
                tasks=[
                    "Create marketing plan",
                    "Draft press release",
                    "Plan content calendar",
                    "Set up pre-save"
                ],
                duration=timedelta(weeks=4),
                rewards={
                    "points": 150,
                    "badge": "Marketing Guru",
                    "streak_bonus": "Strategy Master"
                }
            ),
            "release": ReleasePhase(
                name="Release",
                description="Launch your music",
                tasks=[
                    "Submit to distributors",
                    "Pitch to playlists",
                    "Launch PR campaign",
                    "Release day activities"
                ],
                duration=timedelta(weeks=1),
                rewards={
                    "points": 300,
                    "badge": "Release Champion",
                    "streak_bonus": "Launch Expert"
                }
            )
        }
        self.progress = ReleaseProgress()
        self.current_phase: str = "pre_production"
        self.start_date: Optional[datetime] = None
        self.release_date: Optional[datetime] = None

    def calculate_dates(self, start_date: datetime) -> Dict[str, datetime]:
        """Calculate phase dates based on start date."""
        self.start_date = start_date
        dates = {"start": start_date}
        current_date = start_date

        for phase_id, phase in self.phases.items():
            dates[f"{phase_id}_start"] = current_date
            current_date += phase.duration
            dates[f"{phase_id}_end"] = current_date

        self.release_date = current_date
        dates["release"] = current_date
        return dates

    def update_progress(self, phase_id: str, task_index: int) -> Dict[str, Any]:
        """Update progress and return rewards."""
        phase = self.phases[phase_id]
        tasks_count = len(phase.tasks)
        old_completion = phase.completion
        
        # Update completion
        phase.completion = min(1.0, (task_index + 1) / tasks_count)
        
        # Calculate rewards
        rewards = {
            "points": 0,
            "badges": [],
            "achievements": [],
            "level_up": False
        }

        # Points for task completion
        task_points = phase.rewards["points"] / tasks_count
        rewards["points"] = task_points

        # Check for phase completion
        if phase.completion == 1.0 and old_completion < 1.0:
            rewards["points"] += phase.rewards["points"]  # Bonus points
            rewards["badges"].append(phase.rewards["badge"])
            
            # Check for streaks
            self.progress.streaks[phase_id] = self.progress.streaks.get(phase_id, 0) + 1
            if self.progress.streaks[phase_id] >= 3:
                rewards["achievements"].append(phase.rewards["streak_bonus"])

        # Update total points and check for level up
        old_level = self.progress.level
        self.progress.total_points += rewards["points"]
        self.progress.level = 1 + (self.progress.total_points // 1000)
        
        if self.progress.level > old_level:
            rewards["level_up"] = True

        return rewards

    async def format_progress_message(self, phase_id: Optional[str] = None) -> str:
        """Format progress message with visual indicators."""
        if not phase_id:
            phase_id = self.current_phase

        phase = self.phases[phase_id]
        progress_bar = self._create_progress_bar(phase.completion)
        
        message = f"""
🎵 Release Progress - {phase.name}

{progress_bar} {int(phase.completion * 100)}%

Current Tasks:
{"".join(f"{'✅' if i/len(phase.tasks) <= phase.completion else '⭕'} {task}\n" for i, task in enumerate(phase.tasks))}

🏆 Achievements: {len(self.progress.achievements)}
⭐ Level: {self.progress.level}
📊 Points: {self.progress.total_points}

Next milestone: {self._get_next_milestone()}
        """.strip()

        return message

    def _create_progress_bar(self, completion: float, length: int = 10) -> str:
        """Create a visual progress bar."""
        filled = int(completion * length)
        return f"[{'='*filled}{'·'*(length-filled)}]"

    def _get_next_milestone(self) -> str:
        """Get the next milestone to achieve."""
        phase = self.phases[self.current_phase]
        if phase.completion < 1.0:
            next_task_index = int(phase.completion * len(phase.tasks))
            return f"Complete '{phase.tasks[next_task_index]}'"
        else:
            next_phase_keys = list(self.phases.keys())
            current_index = next_phase_keys.index(self.current_phase)
            if current_index + 1 < len(next_phase_keys):
                next_phase = self.phases[next_phase_keys[current_index + 1]]
                return f"Start {next_phase.name} phase"
            return "Release Complete! 🎉"

    async def create_progress_keyboard(self) -> InlineKeyboardMarkup:
        """Create keyboard for progress interaction."""
        phase = self.phases[self.current_phase]
        next_task_index = int(phase.completion * len(phase.tasks))
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"✅ Complete: {phase.tasks[next_task_index][:20]}...",
                    callback_data=f"release_complete_task_{next_task_index}"
                )
            ],
            [
                InlineKeyboardButton("📊 View Progress", callback_data="release_progress"),
                InlineKeyboardButton("🏆 Achievements", callback_data="release_achievements")
            ],
            [
                InlineKeyboardButton("⬅️ Previous Phase", callback_data="release_prev_phase"),
                InlineKeyboardButton("➡️ Next Phase", callback_data="release_next_phase")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)

    async def format_achievements_message(self) -> str:
        """Format achievements and stats message."""
        return f"""
🏆 Your Release Journey

Level: {self.progress.level}
Total Points: {self.progress.total_points}

Badges Earned:
{"".join(f"• {badge}\n" for badge in self.progress.achievements)}

Active Streaks:
{"".join(f"• {k}: {v}x\n" for k, v in self.progress.streaks.items())}

Milestones Completed:
{"".join(f"• {milestone}\n" for milestone in self.progress.milestones_completed)}
        """.strip() 