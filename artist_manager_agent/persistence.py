"""Persistence handling for the Artist Manager Bot."""
from typing import Dict, Optional
from telegram.ext import BasePersistence
import pickle
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RobustPersistence(BasePersistence):
    def __init__(self, filepath: str, backup_count: int = 3):
        super().__init__()
        self.filepath = Path(filepath)
        self.backup_count = backup_count
        self.backup_dir = self.filepath.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}
        self.callback_data = {}
        self.conversations = {}
        
    async def _backup_data(self):
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"persistence_backup_{current_time}.pickle"
        
        data = {
            "user_data": self.user_data,
            "chat_data": self.chat_data,
            "bot_data": self.bot_data,
            "callback_data": self.callback_data,
            "conversations": self.conversations
        }
        
        with open(backup_path, "wb") as f:
            pickle.dump(data, f)
        
        backups = sorted(self.backup_dir.glob("persistence_backup_*.pickle"))
        while len(backups) > self.backup_count:
            backups[0].unlink()
            backups = backups[1:]
            
        logger.info(f"Created backup: {backup_path}")

    async def get_user_data(self) -> Dict:
        return self.user_data

    async def get_chat_data(self) -> Dict:
        return self.chat_data

    async def get_bot_data(self) -> Dict:
        return self.bot_data

    async def get_callback_data(self) -> Optional[Dict]:
        return self.callback_data

    async def get_conversations(self, name: str) -> Dict:
        return self.conversations.get(name, {})

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        self.user_data[user_id] = data
        await self._backup_data()

    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        self.chat_data[chat_id] = data
        await self._backup_data()

    async def update_bot_data(self, data: Dict) -> None:
        self.bot_data = data
        await self._backup_data()

    async def update_callback_data(self, data: Dict) -> None:
        self.callback_data = data
        await self._backup_data()

    async def update_conversation(self, name: str, key: tuple, new_state: Optional[object]) -> None:
        if name not in self.conversations:
            self.conversations[name] = {}
        
        if new_state is None:
            if key in self.conversations[name]:
                del self.conversations[name][key]
        else:
            self.conversations[name][key] = new_state
            
        await self._backup_data()

    async def refresh_user_data(self, user_id: int, user_data: Dict) -> Dict:
        return user_data

    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> Dict:
        return chat_data

    async def refresh_bot_data(self, bot_data: Dict) -> Dict:
        return bot_data

    async def drop_chat_data(self, chat_id: int) -> None:
        self.chat_data.pop(chat_id, None)

    async def drop_user_data(self, user_id: int) -> None:
        self.user_data.pop(user_id, None)

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

    async def load(self) -> None:
        """Load data with fallback support."""
        try:
            if self.filepath.exists():
                with open(self.filepath, "rb") as f:
                    data = pickle.load(f)
                    
                self.user_data = data.get("user_data", {})
                self.chat_data = data.get("chat_data", {})
                self.bot_data = data.get("bot_data", {})
                self.callback_data = data.get("callback_data", {})
                self.conversations = data.get("conversations", {})
                logger.info("Successfully loaded persistence data from main file")
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
            logger.info("Successfully loaded persistence data from backup")
        else:
            logger.warning("Could not load data from main file or backups. Starting fresh.")

    async def flush(self) -> None:
        """Save data to disk."""
        try:
            data = {
                "user_data": self.user_data,
                "chat_data": self.chat_data,
                "bot_data": self.bot_data,
                "callback_data": self.callback_data,
                "conversations": self.conversations
            }
            
            # Create parent directory if it doesn't exist
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to temporary file first
            temp_path = self.filepath.with_suffix('.tmp')
            with open(temp_path, "wb") as f:
                pickle.dump(data, f)
                
            # Rename temporary file to actual file
            temp_path.replace(self.filepath)
            
            # Create backup
            await self._backup_data()
            logger.info("Successfully saved persistence data")
            
        except Exception as e:
            logger.error(f"Failed to save persistence data: {str(e)}")
            raise