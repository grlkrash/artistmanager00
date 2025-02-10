"""Handler registry for managing all bot handlers."""
from typing import Dict, Any
from telegram.ext import Application
import logging

from .base_handler import BaseHandlerMixin

logger = logging.getLogger(__name__)

class HandlerRegistry:
    """Registry for managing and registering handlers."""
    
    def __init__(self):
        """Initialize the registry."""
        self._handlers: Dict[str, BaseHandlerMixin] = {}
        
    def register_handler(self, name: str, handler: BaseHandlerMixin) -> None:
        """Register a handler with the registry.
        
        Args:
            name: Unique name for the handler
            handler: Handler instance to register
        """
        if not isinstance(handler, BaseHandlerMixin):
            raise TypeError(f"Handler must be an instance of BaseHandlerMixin, got {type(handler)}")
            
        if name in self._handlers:
            logger.warning(f"Overwriting existing handler: {name}")
            
        self._handlers[name] = handler
        logger.debug(f"Registered handler: {name}")
        
    def get_handler(self, name: str) -> BaseHandlerMixin:
        """Get a registered handler by name."""
        return self._handlers.get(name)
        
    def register_all(self, application: Application) -> None:
        """Register all handlers with the application.
        
        Handlers are registered in order of their group value (if specified).
        """
        try:
            # Sort handlers by group
            sorted_handlers = sorted(
                self._handlers.items(),
                key=lambda x: getattr(x[1], 'group', 0) or 0
            )
            
            # Register each handler
            for name, handler in sorted_handlers:
                try:
                    handler.register_handlers(application)
                    logger.debug(f"Registered handlers for: {name}")
                except Exception as e:
                    logger.error(f"Error registering handlers for {name}: {str(e)}")
                    raise
                    
            logger.info("All handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise
            
    def clear(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()
        logger.debug("Cleared all handlers") 