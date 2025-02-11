"""Handler package for the Artist Manager Bot."""
from .base_handler import BaseBotHandler
from .handler_registry import HandlerRegistry
from .goal_handlers import GoalHandlers
from .task_handlers import TaskHandlers
from .onboarding_handlers import OnboardingHandlers
from .project_handlers import ProjectHandlers
from .team_handlers import TeamHandlers
from .music_handlers import MusicHandlers
from .blockchain_handlers import BlockchainHandlers
from .auto_handlers import AutoHandlers

__all__ = [
    "BaseBotHandler",
    "HandlerRegistry",
    "GoalHandlers",
    "TaskHandlers",
    "OnboardingHandlers",
    "ProjectHandlers",
    "TeamHandlers",
    "MusicHandlers",
    "BlockchainHandlers",
    "AutoHandlers"
] 