"""Bot class for the Artist Manager Bot."""
from pathlib import Path
from .bot_main import ArtistManagerBot
from telegram.ext import Application, ApplicationBuilder
from .persistence import RobustPersistence

class Bot(ArtistManagerBot):
    """Main bot class that inherits from ArtistManagerBot."""
    
    def __init__(self, token: str, data_dir: Path):
        """Initialize the bot."""
        super().__init__(token, data_dir)
        self.persistence = RobustPersistence(str(data_dir / "persistence.pickle"))
        
        self.application = (
            ApplicationBuilder()
            .token(self.token)
            .persistence(self.persistence)
                .build()
            ) 