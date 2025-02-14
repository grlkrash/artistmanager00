"""Persistence handling for the Artist Manager Bot."""
from typing import Dict, Optional, Set, Any, Tuple, Union
from telegram.ext import BasePersistence
import pickle
from pathlib import Path
import logging
from datetime import datetime
import asyncio
import json
import threading
from collections import defaultdict

# Type aliases
ConversationDict = Dict[str, Dict[Tuple[Any, ...], Optional[object]]]
CallbackData = Dict[str, Any]

logger = logging.getLogger(__name__)

class RobustPersistence(BasePersistence):
    """Robust persistence implementation with backup support."""
    
    def __init__(
        self, 
        filepath: str,
        update_interval: int = 60,
        backup_count: int = 3
    ):
        # Initialize base class with default settings
        super().__init__(
            store_data=None,  # Let PTB handle defaults
            update_interval=update_interval
        )
        
        # Initialize storage flags
        self._store_user_data = True
        self._store_chat_data = True
        self._store_bot_data = True
        self._store_callback_data = True
        
        self.filepath = Path(filepath)
        self.backup_count = backup_count
        self.backup_dir = self.filepath.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize data containers
        self._user_data = defaultdict(dict)
        self._chat_data = defaultdict(dict)
        self._bot_data = {}
        self._callback_data = None
        self._conversations = {}
        
        # Initialize state tracking
        self._update_task = None
        self._last_update = None
        self._lock = threading.Lock()
        self._closed = False

    @property
    def store_user_data(self) -> bool:
        """Return whether user_data should be stored."""
        return self._store_user_data

    @property
    def store_chat_data(self) -> bool:
        """Return whether chat_data should be stored."""
        return self._store_chat_data

    @property
    def store_bot_data(self) -> bool:
        """Return whether bot_data should be stored."""
        return self._store_bot_data

    @property
    def store_callback_data(self) -> bool:
        """Return whether callback_data should be stored."""
        return self._store_callback_data

    async def get_user_data(self) -> Dict[int, Dict[str, Any]]:
        """Return user_data from persistence."""
        if not self.store_user_data:
            return {}
        return self._user_data.copy()

    async def get_chat_data(self) -> Dict[int, Dict[str, Any]]:
        """Return chat_data from persistence."""
        if not self.store_chat_data:
            return {}
        return self._chat_data.copy()

    async def get_bot_data(self) -> Dict[str, Any]:
        """Return bot_data from persistence."""
        if not self.store_bot_data:
            return {}
        return self._bot_data.copy()

    async def get_callback_data(self) -> Optional[Dict[str, Any]]:
        """Return callback_data from persistence."""
        if not self.store_callback_data:
            return None
        return self._callback_data.copy()

    async def get_conversations(self, name: str) -> Dict[Tuple[int, ...], object]:
        """Return conversations from persistence."""
        return self._conversations.get(name, {}).copy()

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Update user_data in persistence."""
        if self.store_user_data:
            self._user_data[user_id] = data
            await self._backup_data()

    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """Update chat_data in persistence."""
        if self.store_chat_data:
            self._chat_data[chat_id] = data
            await self._backup_data()

    async def update_bot_data(self, data: Dict) -> None:
        """Update bot_data in persistence."""
        if self.store_bot_data:
            self._bot_data = data
            await self._backup_data()

    async def update_callback_data(self, data: Dict[str, Any]) -> None:
        """Update callback_data in persistence."""
        if self.store_callback_data:
            self._callback_data = data
            await self._backup_data()

    async def update_conversation(self, name: str, key: Tuple[int, ...], new_state: Optional[object]) -> None:
        """Update conversation data in persistence."""
        if name not in self._conversations:
            self._conversations[name] = {}
        
        if new_state is None:
            self._conversations[name].pop(key, None)
        else:
            self._conversations[name][key] = new_state
            
        await self._backup_data()

    async def flush(self) -> None:
        """Flush all data to disk."""
        if self._closed:
            return
            
        try:
            with self._lock:
                data = {
                    "user_data": self._user_data if self.store_user_data else {},
                    "chat_data": self._chat_data if self.store_chat_data else {},
                    "bot_data": self._bot_data if self.store_bot_data else {},
                    "callback_data": self._callback_data if self.store_callback_data else {},
                    "conversations": self._conversations,
                    "timestamp": datetime.now().isoformat()
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
                
                self._last_update = datetime.now()
                logger.info("Successfully flushed persistence data")
                
        except Exception as e:
            logger.error(f"Error flushing persistence data: {str(e)}")
            raise

    async def _backup_data(self) -> None:
        """Create a backup of the current data."""
        if self._closed:
            return
            
        try:
            with self._lock:
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.backup_dir / f"persistence_backup_{current_time}.pickle"
                
                data = {
                    "user_data": self._user_data if self.store_user_data else {},
                    "chat_data": self._chat_data if self.store_chat_data else {},
                    "bot_data": self._bot_data if self.store_bot_data else {},
                    "callback_data": self._callback_data if self.store_callback_data else {},
                    "conversations": self._conversations,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Write to temporary file first
                temp_path = backup_path.with_suffix('.tmp')
                with open(temp_path, "wb") as f:
                    pickle.dump(data, f)
                    
                # Rename temporary file to actual backup
                temp_path.replace(backup_path)
                
                # Clean up old backups
                backups = sorted(self.backup_dir.glob("persistence_backup_*.pickle"))
                while len(backups) > self.backup_count:
                    backups[0].unlink()
                    backups = backups[1:]
                    
                self._last_update = datetime.now()
                logger.debug(f"Created backup: {backup_path}")
                
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            raise

    async def close(self) -> None:
        """Close the persistence."""
        if self._closed:
            return
            
        try:
            # Final flush of data
            await self.flush()
            
            # Clear all data
            self._user_data.clear()
            self._chat_data.clear()
            self._bot_data.clear()
            self._callback_data.clear()
            self._conversations.clear()
            
            self._closed = True
            logger.info("Successfully closed persistence")
            
        except Exception as e:
            logger.error(f"Error closing persistence: {str(e)}")
            raise

    async def refresh_user_data(self, user_id: int, user_data: Dict) -> Dict:
        """Refresh user data from persistence."""
        if not self.store_user_data:
            return user_data
        self._user_data[user_id] = user_data
        return user_data

    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> Dict:
        """Refresh chat data from persistence."""
        if not self.store_chat_data:
            return chat_data
        self._chat_data[chat_id] = chat_data
        return chat_data

    async def refresh_bot_data(self, bot_data: Dict) -> Dict:
        """Refresh bot data from persistence."""
        if not self.store_bot_data:
            return bot_data
        self._bot_data = bot_data
        return bot_data

    async def drop_chat_data(self, chat_id: int) -> None:
        """Drop chat data from persistence."""
        if self.store_chat_data:
            self._chat_data.pop(chat_id, None)
            await self._backup_data()

    async def drop_user_data(self, user_id: int) -> None:
        """Drop user data from persistence."""
        if self.store_user_data:
            self._user_data.pop(user_id, None)
            await self._backup_data()

    async def refresh_callback_data(self, callback_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Refresh callback data from persistence."""
        if not self.store_callback_data:
            return None
        if callback_data is None:
            return self._callback_data.copy()
        # Merge existing callback data with new data
        merged = self._callback_data.copy()
        merged.update(callback_data)
        self._callback_data = merged
        return merged

    async def load(self) -> None:
        """Load data from disk with backup support."""
        try:
            if self.filepath.exists():
                with open(self.filepath, "rb") as f:
                    data = pickle.load(f)
                    
                if self.store_user_data:
                    self._user_data = data.get("user_data", {})
                if self.store_chat_data:
                    self._chat_data = data.get("chat_data", {})
                if self.store_bot_data:
                    self._bot_data = data.get("bot_data", {})
                if self.store_callback_data:
                    self._callback_data = data.get("callback_data", {})
                self._conversations = data.get("conversations", {})
                logger.info("Successfully loaded persistence data")
                return
                
        except Exception as e:
            logger.error(f"Error loading persistence data: {str(e)}")
            
        # Try loading from backup
        try:
            backups = sorted(self.backup_dir.glob("persistence_backup_*.pickle"), reverse=True)
            for backup in backups:
                try:
                    with open(backup, "rb") as f:
                        data = pickle.load(f)
                        
                    if self.store_user_data:
                        self._user_data = data.get("user_data", {})
                    if self.store_chat_data:
                        self._chat_data = data.get("chat_data", {})
                    if self.store_bot_data:
                        self._bot_data = data.get("bot_data", {})
                    if self.store_callback_data:
                        self._callback_data = data.get("callback_data", {})
                    self._conversations = data.get("conversations", {})
                    logger.info(f"Successfully loaded persistence data from backup: {backup}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load from backup {backup}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error loading from backups: {str(e)}")
            
        logger.warning("Could not load data from main file or backups. Starting fresh.")