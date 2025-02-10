from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class Task:
    id: str
    title: str
    description: str
    priority: str  # "low", "medium", "high"
    status: str  # "pending", "in_progress", "completed", "blocked"
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None
    goal_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = None
    dependencies: List[str] = None
    progress: int = 0  # 0-100
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class Goal:
    id: str
    title: str
    description: str
    target_date: Optional[datetime]
    priority: str  # "low", "medium", "high"
    status: str  # "not_started", "in_progress", "completed"
    progress: int = 0  # 0-100
    tasks: List[str] = None
    metrics: Dict = None
    created_at: datetime = None
    updated_at: datetime = None

class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.goals = {}
        
    async def create_task(self, task: Task) -> str:
        """Create a new task."""
        if not task.created_at:
            task.created_at = datetime.now()
        task.updated_at = datetime.now()
        if not task.subtasks:
            task.subtasks = []
        if not task.dependencies:
            task.dependencies = []
        
        self.tasks[task.id] = task
        
        # If task is linked to a goal, update goal
        if task.goal_id and task.goal_id in self.goals:
            if not self.goals[task.goal_id].tasks:
                self.goals[task.goal_id].tasks = []
            self.goals[task.goal_id].tasks.append(task.id)
            await self._update_goal_progress(task.goal_id)
        
        return task.id

    async def update_task(self, task_id: str, updates: Dict) -> Optional[Task]:
        """Update an existing task."""
        if task_id not in self.tasks:
            return None
            
        task = self.tasks[task_id]
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.now()
        
        # Update parent task progress if this is a subtask
        if task.parent_task_id:
            await self._update_parent_task_progress(task.parent_task_id)
            
        # Update goal progress if task is linked to a goal
        if task.goal_id:
            await self._update_goal_progress(task.goal_id)
            
        return task

    async def create_goal(self, goal: Goal) -> str:
        """Create a new goal."""
        if not goal.created_at:
            goal.created_at = datetime.now()
        goal.updated_at = datetime.now()
        if not goal.tasks:
            goal.tasks = []
        if not goal.metrics:
            goal.metrics = {}
        
        self.goals[goal.id] = goal
        return goal.id

    async def update_goal(self, goal_id: str, updates: Dict) -> Optional[Goal]:
        """Update an existing goal."""
        if goal_id not in self.goals:
            return None
            
        goal = self.goals[goal_id]
        for key, value in updates.items():
            if hasattr(goal, key):
                setattr(goal, key, value)
        
        goal.updated_at = datetime.now()
        return goal

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    async def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self.goals.get(goal_id)

    async def get_tasks_by_goal(self, goal_id: str) -> List[Task]:
        """Get all tasks associated with a goal."""
        if goal_id not in self.goals:
            return []
        return [self.tasks[task_id] for task_id in self.goals[goal_id].tasks if task_id in self.tasks]

    async def get_subtasks(self, task_id: str) -> List[Task]:
        """Get all subtasks of a task."""
        if task_id not in self.tasks:
            return []
        return [self.tasks[subtask_id] for subtask_id in self.tasks[task_id].subtasks if subtask_id in self.tasks]

    async def _update_parent_task_progress(self, parent_id: str):
        """Update parent task progress based on subtasks."""
        if parent_id not in self.tasks:
            return
            
        parent = self.tasks[parent_id]
        if not parent.subtasks:
            return
            
        subtasks = await self.get_subtasks(parent_id)
        if not subtasks:
            return
            
        total_progress = sum(task.progress for task in subtasks)
        parent.progress = total_progress // len(subtasks)
        
        # Update goal progress if parent task is linked to a goal
        if parent.goal_id:
            await self._update_goal_progress(parent.goal_id)

    async def _update_goal_progress(self, goal_id: str):
        """Update goal progress based on associated tasks."""
        if goal_id not in self.goals:
            return
            
        goal = self.goals[goal_id]
        if not goal.tasks:
            return
            
        tasks = await self.get_tasks_by_goal(goal_id)
        if not tasks:
            return
            
        total_progress = sum(task.progress for task in tasks)
        goal.progress = total_progress // len(tasks)
        
        # Update goal status based on progress
        if goal.progress == 0:
            goal.status = "not_started"
        elif goal.progress == 100:
            goal.status = "completed"
        else:
            goal.status = "in_progress"

    async def get_tasks_by_status(self, status: str) -> List[Task]:
        """Get all tasks with a specific status."""
        return [task for task in self.tasks.values() if task.status == status]

    async def get_tasks_by_priority(self, priority: str) -> List[Task]:
        """Get all tasks with a specific priority."""
        return [task for task in self.tasks.values() if task.priority == priority]

    async def get_overdue_tasks(self) -> List[Task]:
        """Get all tasks that are past their due date."""
        now = datetime.now()
        return [
            task for task in self.tasks.values()
            if task.due_date and task.due_date < now and task.status != "completed"
        ]

    async def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """Get tasks due within the specified number of days."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        return [
            task for task in self.tasks.values()
            if task.due_date and now <= task.due_date <= cutoff
        ]

    async def get_blocked_tasks(self) -> List[Task]:
        """Get tasks that are blocked by dependencies."""
        blocked_tasks = []
        for task in self.tasks.values():
            if task.dependencies:
                # Check if any dependency is not completed
                has_incomplete_deps = any(
                    dep_id in self.tasks and self.tasks[dep_id].status != "completed"
                    for dep_id in task.dependencies
                )
                if has_incomplete_deps:
                    blocked_tasks.append(task)
        return blocked_tasks

    async def analyze_goal_progress(self, goal_id: str) -> Dict:
        """Analyze progress and generate metrics for a goal."""
        if goal_id not in self.goals:
            return {}
            
        goal = self.goals[goal_id]
        tasks = await self.get_tasks_by_goal(goal_id)
        
        total_tasks = len(tasks)
        if total_tasks == 0:
            return {
                "progress": 0,
                "completed_tasks": 0,
                "total_tasks": 0,
                "blocked_tasks": 0,
                "overdue_tasks": 0,
                "estimated_completion": None
            }
            
        completed_tasks = len([t for t in tasks if t.status == "completed"])
        blocked_tasks = len([t for t in tasks if t.status == "blocked"])
        overdue_tasks = len([t for t in tasks if t.due_date and t.due_date < datetime.now()])
        
        # Calculate estimated completion date based on progress rate
        if completed_tasks > 0 and goal.created_at:
            days_since_start = (datetime.now() - goal.created_at).days
            if days_since_start > 0:
                completion_rate = completed_tasks / days_since_start
                remaining_tasks = total_tasks - completed_tasks
                if completion_rate > 0:
                    days_to_completion = remaining_tasks / completion_rate
                    estimated_completion = datetime.now() + timedelta(days=days_to_completion)
                else:
                    estimated_completion = None
            else:
                estimated_completion = None
        else:
            estimated_completion = None
            
        return {
            "progress": goal.progress,
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "blocked_tasks": blocked_tasks,
            "overdue_tasks": overdue_tasks,
            "estimated_completion": estimated_completion
        }

    async def suggest_next_tasks(self, goal_id: str) -> List[Task]:
        """Suggest the next tasks to focus on for a goal."""
        if goal_id not in self.goals:
            return []
            
        tasks = await self.get_tasks_by_goal(goal_id)
        if not tasks:
            return []
            
        # Filter for incomplete tasks
        incomplete_tasks = [t for t in tasks if t.status != "completed"]
        if not incomplete_tasks:
            return []
            
        # Sort tasks by priority and blocked status
        def task_priority_score(task: Task) -> int:
            priority_scores = {"high": 3, "medium": 2, "low": 1}
            score = priority_scores.get(task.priority, 0)
            
            # Reduce score if task is blocked
            if task.dependencies:
                has_incomplete_deps = any(
                    dep_id in self.tasks and self.tasks[dep_id].status != "completed"
                    for dep_id in task.dependencies
                )
                if has_incomplete_deps:
                    score -= 5
                    
            # Increase score if task is overdue
            if task.due_date and task.due_date < datetime.now():
                score += 4
                
            return score
            
        sorted_tasks = sorted(
            incomplete_tasks,
            key=task_priority_score,
            reverse=True
        )
        
        # Return top 3 suggested tasks
        return sorted_tasks[:3]

    async def get_goal_analytics(self) -> Dict:
        """Get analytics for all goals."""
        analytics = {
            "total_goals": len(self.goals),
            "completed_goals": len([g for g in self.goals.values() if g.status == "completed"]),
            "in_progress_goals": len([g for g in self.goals.values() if g.status == "in_progress"]),
            "not_started_goals": len([g for g in self.goals.values() if g.status == "not_started"]),
            "total_tasks": len(self.tasks),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == "completed"]),
            "overdue_tasks": len(await self.get_overdue_tasks()),
            "blocked_tasks": len(await self.get_blocked_tasks()),
            "goals_by_priority": {
                "high": len([g for g in self.goals.values() if g.priority == "high"]),
                "medium": len([g for g in self.goals.values() if g.priority == "medium"]),
                "low": len([g for g in self.goals.values() if g.priority == "low"])
            }
        }
        
        # Calculate average goal progress
        if self.goals:
            total_progress = sum(goal.progress for goal in self.goals.values())
            analytics["average_goal_progress"] = total_progress / len(self.goals)
        else:
            analytics["average_goal_progress"] = 0
            
        return analytics 