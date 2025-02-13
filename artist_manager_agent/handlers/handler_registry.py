"""Handler registry for managing bot handlers."""
from typing import List, Dict, Any
from telegram.ext import BaseHandler
from ..utils.logger import logger

class HandlerRegistry:
    """Registry for managing bot handlers."""
    
    def __init__(self):
        """Initialize the handler registry."""
        self._handlers = {}
        self._groups = {}
        self._priorities = {}
        
    def register(self, handler, group: int = 0, priority: int = 0):
        """Register a handler with group and priority."""
        handler_id = id(handler)
        self._handlers[handler_id] = handler
        self._groups[handler_id] = group
        self._priorities[handler_id] = priority
        
    def unregister(self, handler):
        """Unregister a handler."""
        handler_id = id(handler)
        if handler_id in self._handlers:
            del self._handlers[handler_id]
            del self._groups[handler_id]
            del self._priorities[handler_id]
            
    def get_handlers(self, group: int = None) -> list:
        """Get all handlers, optionally filtered by group."""
        if group is None:
            return list(self._handlers.values())
        return [h for h_id, h in self._handlers.items() if self._groups[h_id] == group]
        
    def clear(self):
        """Clear all registered handlers."""
        self._handlers.clear()
        self._groups.clear()
        self._priorities.clear()
        
    def get_handler_info(self, handler) -> tuple:
        """Get group and priority for a handler."""
        handler_id = id(handler)
        return (
            self._groups.get(handler_id, 0),
            self._priorities.get(handler_id, 0)
        )

    def register_handler(self, name: str, handler: BaseHandler) -> None:
        """Register a handler with a name."""
        if name not in self._handlers:
            self._handlers[name] = []
        self._handlers[name].append(handler)
        logger.info(f"Registered handler {name}")
        
    def get_handlers_by_name(self, name: str) -> List[BaseHandler]:
        """Get all handlers registered under a name."""
        return self._handlers.get(name, []) 