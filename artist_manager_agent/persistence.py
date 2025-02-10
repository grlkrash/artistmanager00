"""Persistence handling for the Artist Manager Bot."""
from typing import Dict, Optional
from telegram.ext import PicklePersistence
import pickle
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RobustPersistence(PicklePersistence):
    """Custom persistence handler with backup and recovery mechanisms."""
    
    def __init__(self, filepath: str, backup_count: int = 3):
        super().__init__(filepath=filepath)
        self.backup_count = backup_count
        self.backup_dir = Path(filepath).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    async def _backup_data(self):
        """Create a backup of the current persistence file."""
        try:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"persistence_backup_{current_time}.pickle"
            
            # Create backup data dictionary
            data = {
                "user_data": self.user_data,
                "chat_data": self.chat_data,
                "bot_data": self.bot_data,
                "callback_data": self.callback_data,
                "conversations": self.conversations
            }
            
            # Save backup
            with open(backup_path, "wb") as f:
                pickle.dump(data, f)
            
            # Remove old backups if we exceed backup_count
            backups = sorted(self.backup_dir.glob("persistence_backup_*.pickle"))
            while len(backups) > self.backup_count:
                backups[0].unlink()
                backups = backups[1:]
                
            logger.info(f"Created persistence backup: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create persistence backup: {str(e)}")
    
    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Override to add backup after update."""
        await super().update_user_data(user_id, data)
        await self._backup_data()
        
    async def _load_fallback(self) -> Optional[Dict]:
        """Try to load from the most recent backup if main file fails."""
        try:
            backups = sorted(self.backup_dir.glob("persistence_backup_*.pickle"), reverse=True)
            for backup in backups:
                try:
                    with open(backup, "rb") as f:
                        data = pickle.load(f)
                    logger.info(f"Successfully loaded data from backup: {backup}")
                    return data
                except:
                    continue
        except Exception as e:
            logger.error(f"Failed to load from backups: {str(e)}")
        return None
        
    async def load_data(self) -> None:
        """Load data with fallback support."""
        try:
            # Try loading from main file first
            if Path(self.filepath).exists():
                with open(self.filepath, "rb") as f:
                    data = pickle.load(f)
                    
                self.user_data = data.get("user_data", {})
                self.chat_data = data.get("chat_data", {})
                self.bot_data = data.get("bot_data", {})
                self.callback_data = data.get("callback_data", {})
                self.conversations = data.get("conversations", {})
                return
                
        except Exception as e:
            logger.error(f"Failed to load persistence data: {str(e)}")
            
        # Try loading from backup
        data = await self._load_fallback()
        if data:
            self.user_data = data.get("user_data", {})
            self.chat_data = data.get("chat_data", {})
            self.bot_data = data.get("bot_data", {})
            self.callback_data = data.get("callback_data", {})
            self.conversations = data.get("conversations", {})
        else:
            logger.warning("Could not load data from main file or backups. Starting fresh.")
            self.user_data = {}
            self.chat_data = {}
            self.bot_data = {}
            self.callback_data = {}
            self.conversations = {} 