"""Handler registry for managing all bot handlers."""
from typing import Dict, Any
from telegram.ext import Application, ConversationHandler
import logging

from .base_handler import BaseHandlerMixin

logger = logging.getLogger(__name__)

class HandlerRegistry:
    """Registry for managing and registering handlers."""
    
    def __init__(self):
        """Initialize the registry."""
        self._handlers: Dict[int, BaseHandlerMixin] = {}
        
    def register_handler(self, group: int, handler: BaseHandlerMixin) -> None:
        """Register a handler with the registry.
        
        Args:
            group: Integer group number for the handler
            handler: Handler instance to register
        """
        if not isinstance(handler, BaseHandlerMixin):
            raise TypeError(f"Handler must be an instance of BaseHandlerMixin, got {type(handler)}")
            
        if group in self._handlers:
            logger.warning(f"Overwriting existing handler in group {group}")
            
        self._handlers[group] = handler
        logger.debug(f"Registered handler in group {group}")
        
    def get_handler(self, group: int) -> BaseHandlerMixin:
        """Get a registered handler by group number."""
        return self._handlers.get(group)
        
    def register_all(self, application: Application) -> None:
        """Register all handlers with the application.
        
        Handlers are registered in order of their group number.
        Conversation handlers are registered first within each group.
        """
        try:
            # Sort handlers by group number
            sorted_handlers = sorted(self._handlers.items())
            
            # First pass: register conversation handlers
            for group, handler in sorted_handlers:
                try:
                    handlers = handler.get_handlers()
                    for h in handlers:
                        if isinstance(h, ConversationHandler):
                            application.add_handler(h, group=group)
                            logger.debug(f"Registered conversation handler in group {group}")
                except Exception as e:
                    logger.error(f"Error registering conversation handlers for group {group}: {str(e)}")
                    raise
                    
            # Second pass: register regular handlers
            for group, handler in sorted_handlers:
                try:
                    handlers = handler.get_handlers()
                    for h in handlers:
                        if not isinstance(h, ConversationHandler):
                            application.add_handler(h, group=group)
                            logger.debug(f"Registered handler {h.__class__.__name__} in group {group}")
                except Exception as e:
                    logger.error(f"Error registering regular handlers for group {group}: {str(e)}")
                    raise
                    
            logger.info("All handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise
            
    def clear(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()
        logger.debug("Cleared all handlers") 