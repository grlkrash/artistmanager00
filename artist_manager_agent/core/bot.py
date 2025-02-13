from telegram.ext import Application, ApplicationBuilder
from .persistence import RobustPersistence

    def __init__(self, token: str, data_dir: Path):
        """Initialize the bot with the given token."""
        self.token = token
        self.data_dir = data_dir
        self.persistence = RobustPersistence(str(data_dir / "persistence.pickle"))
        
        self.application = (
            ApplicationBuilder()
            .token(self.token)
            .persistence(self.persistence)
                .build()
            ) 