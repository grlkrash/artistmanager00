"""Task manager integration for the Artist Manager Bot."""
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import logging
from .task_manager import TaskManager, Task, Goal

logger = logging.getLogger(__name__)

class TaskManagerIntegration:
    """Integration layer between the bot and task manager."""
    
    def __init__(self, persistence=None):
        """Initialize the integration layer."""
        self.task_manager = TaskManager()
        self.persistence = persistence
        
    async def load_from_persistence(self):
        """Load tasks and goals from persistence."""
        try:
            if self.persistence and hasattr(self.persistence, 'bot_data'):
                tasks = self.persistence.bot_data.get('tasks', {})
                goals = self.persistence.bot_data.get('goals', {})
                self.task_manager.tasks = tasks
                self.task_manager.goals = goals
                logger.info("Loaded tasks and goals from persistence")
        except Exception as e:
            logger.error(f"Error loading from persistence: {str(e)}")
            
    async def save_to_persistence(self):
        """Save tasks and goals to persistence."""
        try:
            if self.persistence and hasattr(self.persistence, 'bot_data'):
                self.persistence.bot_data['tasks'] = self.task_manager.tasks
                self.persistence.bot_data['goals'] = self.task_manager.goals
                await self.persistence._backup_data()
                logger.info("Saved tasks and goals to persistence")
        except Exception as e:
            logger.error(f"Error saving to persistence: {str(e)}")
            
    async def create_task(self, task: Task) -> str:
        """Create a new task with persistence."""
        try:
            task_id = await self.task_manager.create_task(task)
            await self.save_to_persistence()
            return task_id
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise
            
    async def create_goal(self, goal: Goal) -> str:
        """Create a new goal with persistence."""
        try:
            goal_id = await self.task_manager.create_goal(goal)
            await self.save_to_persistence()
            return goal_id
        except Exception as e:
            logger.error(f"Error creating goal: {str(e)}")
            raise
            
    async def update_task(self, task_id: str, updates: Dict) -> Optional[Task]:
        """Update a task with persistence."""
        try:
            task = await self.task_manager.update_task(task_id, updates)
            if task:
                await self.save_to_persistence()
            return task
        except Exception as e:
            logger.error(f"Error updating task: {str(e)}")
            raise
            
    async def update_goal(self, goal_id: str, updates: Dict) -> Optional[Goal]:
        """Update a goal with persistence."""
        try:
            goal = await self.task_manager.update_goal(goal_id, updates)
            if goal:
                await self.save_to_persistence()
            return goal
        except Exception as e:
            logger.error(f"Error updating goal: {str(e)}")
            raise
            
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return await self.task_manager.get_task(task_id)
        
    async def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return await self.task_manager.get_goal(goal_id)
        
    async def get_tasks_by_status(self, status: str) -> List[Task]:
        """Get all tasks with a specific status."""
        return await self.task_manager.get_tasks_by_status(status)
        
    async def get_tasks_by_priority(self, priority: str) -> List[Task]:
        """Get all tasks with a specific priority."""
        return await self.task_manager.get_tasks_by_priority(priority)
        
    async def get_overdue_tasks(self) -> List[Task]:
        """Get all overdue tasks."""
        return await self.task_manager.get_overdue_tasks()
        
    async def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """Get tasks due within the specified number of days."""
        return await self.task_manager.get_upcoming_tasks(days)
        
    async def get_blocked_tasks(self) -> List[Task]:
        """Get tasks that are blocked by dependencies."""
        return await self.task_manager.get_blocked_tasks()
        
    async def get_tasks_by_goal(self, goal_id: str) -> List[Task]:
        """Get all tasks associated with a goal."""
        return await self.task_manager.get_tasks_by_goal(goal_id)
        
    async def get_goal_analytics(self) -> Dict:
        """Get analytics for all goals."""
        return await self.task_manager.get_goal_analytics()
        
    async def analyze_goal_progress(self, goal_id: str) -> Dict:
        """Analyze progress and generate metrics for a goal."""
        return await self.task_manager.analyze_goal_progress(goal_id)
        
    async def suggest_next_tasks(self, goal_id: str) -> List[Task]:
        """Suggest the next tasks to focus on for a goal."""
        return await self.task_manager.suggest_next_tasks(goal_id) 