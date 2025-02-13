"""Handler package for the Artist Manager Bot."""
from .core.base_handler import BaseBotHandler
from .utils.handler_registry import HandlerRegistry
from .features.goal_handlers import GoalHandlers
from .features.task_handlers import TaskHandlers
from .features.onboarding_handlers import OnboardingHandlers
from .features.project_handlers import ProjectHandlers
from .features.team_handlers import TeamHandlers
from .features.music_handlers import MusicHandlers
from .features.blockchain_handlers import BlockchainHandlers
from .features.auto_handlers import AutoHandlers
from .features.home_handler import HomeHandlers
from .features.name_change_handler import NameChangeHandlers

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
    "AutoHandlers",
    "HomeHandlers",
    "NameChangeHandlers"
] 