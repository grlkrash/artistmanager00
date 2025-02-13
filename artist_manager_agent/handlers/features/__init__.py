"""Feature-specific handlers for the Artist Manager Bot."""
from .goal_handlers import GoalHandlers
from .task_handlers import TaskHandlers
from .project_handlers import ProjectHandlers
from .music_handlers import MusicHandlers
from .blockchain_handlers import BlockchainHandlers
from .auto_handlers import AutoHandlers
from .team_handlers import TeamHandlers
from .name_change_handler import NameChangeHandlers
from .onboarding_handlers import OnboardingHandlers
from .home_handler import HomeHandlers

__all__ = [
    "GoalHandlers",
    "TaskHandlers",
    "ProjectHandlers",
    "MusicHandlers",
    "BlockchainHandlers",
    "AutoHandlers",
    "TeamHandlers",
    "NameChangeHandlers",
    "OnboardingHandlers",
    "HomeHandlers"
] 