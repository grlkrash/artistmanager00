"""Handler registry for managing bot command handlers."""
from typing import Dict, Any
from telegram.ext import Application, ConversationHandler
from ..log import logger

class HandlerRegistry:
    """Registry for managing bot command handlers."""
    
    def __init__(self):
        """Initialize an empty handler registry."""
        self._handlers: Dict[int, Any] = {}
        self._registered_handlers = set()
        
    def register_handler(self, group: int, handler: Any) -> None:
        """Register a handler with a specific group number."""
        try:
            if handler in self._registered_handlers:
                logger.warning(f"Handler {handler.__class__.__name__} already registered")
                return
                
            self._handlers[group] = handler
            self._registered_handlers.add(handler)
            logger.debug(f"Registered handler {handler.__class__.__name__} in group {group}")
            
        except Exception as e:
            logger.error(f"Error registering handler: {str(e)}")
            raise
            
    def register_all(self, application: Application) -> None:
        """Register all handlers with the application in group order."""
        try:
            # Sort handlers by group number
            sorted_handlers = sorted(self._handlers.items())
            
            # First pass: register conversation handlers
            for group, handler in sorted_handlers:
                try:
                    logger.debug(f"Registering conversation handlers from {handler.__class__.__name__}")
                    handlers = handler.get_handlers()
                    for h in handlers:
                        if isinstance(h, ConversationHandler):
                            application.add_handler(h, group=group)
                            logger.debug(f"Registered conversation handler in group {group}")
                except Exception as e:
                    logger.error(f"Error registering conversation handlers from {handler.__class__.__name__}: {str(e)}")
                    raise
                    
            # Second pass: register regular handlers
            for group, handler in sorted_handlers:
                try:
                    logger.debug(f"Registering regular handlers from {handler.__class__.__name__}")
                    handlers = handler.get_handlers()
                    for h in handlers:
                        if not isinstance(h, ConversationHandler):
                            application.add_handler(h, group=group)
                            logger.debug(f"Registered handler {h.__class__.__name__} in group {group}")
                except Exception as e:
                    logger.error(f"Error registering regular handlers from {handler.__class__.__name__}: {str(e)}")
                    raise
                    
            logger.info(f"Registered {len(sorted_handlers)} handler groups")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise
            
    def clear(self) -> None:
        """Clear all registered handlers."""
        try:
            self._handlers.clear()
            self._registered_handlers.clear()
            logger.debug("Cleared all handlers")
            
        except Exception as e:
            logger.error(f"Error clearing handlers: {str(e)}")
            raise
            
    def get_handler(self, group: int) -> Any:
        """Get a handler by group number."""
        return self._handlers.get(group)
        
    def get_all_handlers(self) -> Dict[int, Any]:
        """Get all registered handlers."""
        return dict(self._handlers)
        
    def __len__(self) -> int:
        """Get the number of registered handlers."""
        return len(self._handlers) 