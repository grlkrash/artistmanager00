"""Persistence handling for the Artist Manager Bot."""
from typing import Dict, Optional
from telegram.ext import BasePersistence
import pickle
from pathlib import Path
import logging
from datetime import datetime
import asyncio
import json
import threading

logger = logging.getLogger(__name__)

class RobustPersistence(BasePersistence):
    def __init__(
        self, 
        filepath: str, 
        backup_count: int = 3,
        store_data: bool = True,
        update_interval: int = 60
    ):
        self.filepath = Path(filepath)
        self.backup_count = backup_count
        self.store_data = store_data
        self.backup_dir = self.filepath.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}
        self.callback_data = None
        self.conversations = {}
        
        self._update_task = None
        self._last_update = None
        self._lock = threading.Lock()
        self._closed = False
        
        # Initialize base class last
        super().__init__(update_interval=update_interval)
        
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
                    "user_data": self.user_data,
                    "chat_data": self.chat_data,
                    "bot_data": self.bot_data,
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
        return self.user_data

    async def get_chat_data(self) -> Dict:
        """Get chat data from persistence."""
        return self.chat_data

    async def get_bot_data(self) -> Dict:
        """Get bot data from persistence."""
        return self.bot_data

    async def get_callback_data(self) -> Optional[Dict]:
        """Get callback data from persistence."""
        return self.callback_data

    async def get_conversations(self, name: str) -> Dict:
        """Get conversations from persistence."""
        return self.conversations.get(name, {})

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Update user data in persistence."""
        self.user_data[user_id] = data
        if self.store_data:
            await self._backup_data()

    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """Update chat data in persistence."""
        self.chat_data[chat_id] = data
        if self.store_data:
            await self._backup_data()

    async def update_bot_data(self, data: Dict) -> None:
        """Update bot data in persistence."""
        self.bot_data = data
        if self.store_data:
            await self._backup_data()

    async def update_callback_data(self, data: Dict) -> None:
        """Update callback data in persistence."""
        self.callback_data = data
        if self.store_data:
            await self._backup_data()

    async def update_conversation(self, name: str, key: tuple, new_state: Optional[object]) -> None:
        """Update conversation state in persistence."""
        if name not in self.conversations:
            self.conversations[name] = {}
        
        if new_state is None:
            if key in self.conversations[name]:
                del self.conversations[name][key]
        else:
            self.conversations[name][key] = new_state
            
        if self.store_data:
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

    async def drop_chat_data(self, chat_id: int) -> None:
        """Drop chat data from persistence."""
        self.chat_data.pop(chat_id, None)

    async def drop_user_data(self, user_id: int) -> None:
        """Drop user data from persistence."""
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
                self.conversations = data.get("conversations", {})
                logger.info("Successfully loaded persistence data from main file")
                
                # Start periodic updates if enabled
                if self.store_data:
                    self._update_task = asyncio.create_task(self._start_periodic_updates())
                return
                
        except Exception as e:
            logger.error(f"Failed to load persistence data: {str(e)}")
            
        # Try loading from backup
        data = await self._load_fallback()
        if data:
            self.user_data = data.get("user_data", {})
            self.chat_data = data.get("chat_data", {})
            self.bot_data = data.get("bot_data", {})
            self.conversations = data.get("conversations", {})
            logger.info("Successfully loaded persistence data from backup")
            
            # Start periodic updates if enabled
            if self.store_data:
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
                    "user_data": self.user_data,
                    "chat_data": self.chat_data,
                    "bot_data": self.bot_data,
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
                logger.info("Successfully saved persistence data")
                
        except Exception as e:
            logger.error(f"Failed to save persistence data: {str(e)}")
            raise

    async def close(self) -> None:
        """Close persistence and cleanup."""
        try:
            with self._lock:
                if self._closed:
                    return
                    
                self._closed = True
                
                # Cancel periodic update task if running
                if self._update_task:
                    self._update_task.cancel()
                    try:
                        await self._update_task
                    except asyncio.CancelledError:
                        pass
                    
                # Final flush
                if self.store_data:
                    await self.flush()
                    
        except Exception as e:
            logger.error(f"Error closing persistence: {str(e)}")
            raise