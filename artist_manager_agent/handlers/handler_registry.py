"""Handler registry for managing bot handlers."""
from typing import List, Dict, Any
from telegram.ext import BaseHandler
from ..utils.logger import logger

class HandlerRegistry:
    """Registry for managing bot handlers."""
    
    def __init__(self):
        self.handlers: Dict[str, List[BaseHandler]] = {}
        
    def register_handler(self, name: str, handler: BaseHandler) -> None:
        """Register a handler with a name."""
        if name not in self.handlers:
            self.handlers[name] = []
        self.handlers[name].append(handler)
        logger.info(f"Registered handler {name}")
        
    def get_handlers(self, name: str) -> List[BaseHandler]:
        """Get all handlers registered under a name."""
        return self.handlers.get(name, []) 