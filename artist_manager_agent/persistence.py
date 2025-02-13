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
    def __init__(
        self, 
        filepath: str, 
        backup_count: int = 3,
        store_data: Dict[str, bool] = None,
        update_interval: int = 60
    ):
        self.filepath = Path(filepath)
        self.backup_count = backup_count
        self.store_data = store_data or {
            "user_data": True,
            "chat_data": True,
            "bot_data": True,
            "callback_data": True
        }
        self.backup_dir = self.filepath.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.user_data: Dict[int, Dict[str, Any]] = {}
        self.chat_data: Dict[int, Dict[str, Any]] = {}
        self.bot_data: Dict[str, Any] = {}
        self.callback_data: Dict[str, Any] = {}
        self.conversations: ConversationDict = {}
        
        self._update_task = None
        self._last_update = None
        self._lock = threading.Lock()
        self._closed = False
        
        # Initialize base class
        super().__init__()
        
    async def _start_periodic_updates(self):
        """Start periodic persistence updates."""
        while not self._closed:
            try:
                await asyncio.sleep(self.update_interval)
                if self.store_data and self._last_update:
                    await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic update: {str(e)}")
                
    async def _backup_data(self):
        """Create a backup of the current data."""
        if self._closed:
            return
            
        try:
            with self._lock:
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.backup_dir / f"persistence_backup_{current_time}.pickle"
                
                data = {
                    "user_data": self.user_data if "user_data" in self.store_data else {},
                    "chat_data": self.chat_data if "chat_data" in self.store_data else {},
                    "bot_data": self.bot_data if "bot_data" in self.store_data else {},
                    "callback_data": self.callback_data if "callback_data" in self.store_data else {},
                    "conversations": self.conversations,
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
                logger.info(f"Created backup: {backup_path}")
                
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            raise

    async def get_user_data(self) -> Dict:
        """Get user data from persistence."""
        if not hasattr(self, 'user_data'):
            self.user_data = {}
        return self.user_data

    async def get_chat_data(self) -> Dict:
        """Get chat data from persistence."""
        if not hasattr(self, 'chat_data'):
            self.chat_data = {}
        return self.chat_data

    async def get_bot_data(self) -> Dict:
        """Get bot data from persistence."""
        if not hasattr(self, 'bot_data'):
            self.bot_data = {}
        return self.bot_data

    async def get_callback_data(self) -> Optional[Dict]:
        """Get callback data from persistence."""
        if not self.store_data.get("callback_data", False):
            return None
        if not hasattr(self, 'callback_data'):
            self.callback_data = {}
        return self.callback_data

    async def get_conversations(self, name: str) -> Dict:
        """Get conversations from persistence."""
        if not hasattr(self, 'conversations'):
            self.conversations = {}
        return self.conversations.get(name, {})

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Update user data in persistence."""
        if not hasattr(self, 'user_data'):
            self.user_data = {}
        self.user_data[user_id] = data
        await self._backup_data()

    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """Update chat data in persistence."""
        if not hasattr(self, 'chat_data'):
            self.chat_data = {}
        self.chat_data[chat_id] = data
        await self._backup_data()

    async def update_bot_data(self, data: Dict) -> None:
        """Update bot data in persistence."""
        self.bot_data = data
        await self._backup_data()

    async def update_callback_data(self, data: Dict) -> None:
        """Update callback data in persistence."""
        if not self.store_data.get("callback_data", False):
            return
        self.callback_data = data
        await self._backup_data()

    async def update_conversation(self, name: str, key: tuple, new_state: Optional[object]) -> None:
        """Update conversation state in persistence."""
        if not hasattr(self, 'conversations'):
            self.conversations = {}
        
        if name not in self.conversations:
            self.conversations[name] = {}
            
        if new_state is None:
            if key in self.conversations[name]:
                del self.conversations[name][key]
        else:
            self.conversations[name][key] = new_state
            
        await self._backup_data()

    async def refresh_user_data(self, user_id: int, user_data: Dict) -> Dict:
        """Refresh user data from persistence."""
        return user_data

    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> Dict:
        """Refresh chat data from persistence."""
        return chat_data

    async def refresh_bot_data(self, bot_data: Dict) -> Dict:
        """Refresh bot data from persistence."""
        return bot_data

    async def refresh_callback_data(self, callback_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Refresh callback data from persistence."""
        if not self.store_data.get("callback_data", False):
            return None
        if callback_data is None:
            return self.callback_data
        # Merge the existing callback data with the new data
        merged_data = self.callback_data.copy()
        merged_data.update(callback_data)
        return merged_data

    async def drop_chat_data(self, chat_id: int) -> None:
        """Drop chat data from persistence."""
        if hasattr(self, 'chat_data'):
            self.chat_data.pop(chat_id, None)

    async def drop_user_data(self, user_id: int) -> None:
        """Drop user data from persistence."""
        if hasattr(self, 'user_data'):
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
                    
                if self.store_data.get("user_data", False):
                    self.user_data = data.get("user_data", {})
                if self.store_data.get("chat_data", False):
                    self.chat_data = data.get("chat_data", {})
                if self.store_data.get("bot_data", False):
                    self.bot_data = data.get("bot_data", {})
                if self.store_data.get("callback_data", False):
                    self.callback_data = data.get("callback_data", {})
                self.conversations = data.get("conversations", {})
                logger.info("Successfully loaded persistence data from main file")
                
                # Start periodic updates if enabled
                if any(self.store_data.values()):
                    self._update_task = asyncio.create_task(self._start_periodic_updates())
                return
                
        except Exception as e:
            logger.error(f"Failed to load persistence data: {str(e)}")
            
        # Try loading from backup
        data = await self._load_fallback()
        if data:
            if self.store_data.get("user_data", False):
                self.user_data = data.get("user_data", {})
            if self.store_data.get("chat_data", False):
                self.chat_data = data.get("chat_data", {})
            if self.store_data.get("bot_data", False):
                self.bot_data = data.get("bot_data", {})
            if self.store_data.get("callback_data", False):
                self.callback_data = data.get("callback_data", {})
            self.conversations = data.get("conversations", {})
            logger.info("Successfully loaded persistence data from backup")
            
            # Start periodic updates if enabled
            if any(self.store_data.values()):
                self._update_task = asyncio.create_task(self._start_periodic_updates())
        else:
            logger.warning("Could not load data from main file or backups. Starting fresh.")

    async def flush(self) -> None:
        """Save data to disk."""
        if self._closed:
            return
            
        try:
            with self._lock:
                data = {
                    "user_data": self.user_data if self.store_data.get("user_data", False) else {},
                    "chat_data": self.chat_data if self.store_data.get("chat_data", False) else {},
                    "bot_data": self.bot_data if self.store_data.get("bot_data", False) else {},
                    "callback_data": self.callback_data if self.store_data.get("callback_data", False) else {},
                    "conversations": self.conversations,
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

    async def close(self) -> None:
        """Close the persistence and cleanup."""
        if self._closed:
            return
            
        try:
            # Cancel periodic update task if running
            if self._update_task and not self._update_task.done():
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass
            
            # Final flush of data
            await self.flush()
            
            # Clear all data
            self.user_data.clear()
            self.chat_data.clear()
            self.bot_data.clear()
            self.callback_data.clear()
            self.conversations.clear()
            
            self._closed = True
            logger.info("Successfully closed persistence")
            
        except Exception as e:
            logger.error(f"Error closing persistence: {str(e)}")
            raise