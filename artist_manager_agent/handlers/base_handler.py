"""Base handler mixin for consistent handler registration."""
from typing import List
from telegram.ext import BaseHandler, Application, ConversationHandler
import logging

logger = logging.getLogger(__name__)

class BaseHandlerMixin:
    """Base mixin class for handlers."""
    
    group = None  # Override in subclass to specify handler group
    
    def get_handlers(self) -> List[BaseHandler]:
        """Get list of handlers to register.
        
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_handlers()")
        
    def register_handlers(self, application: Application) -> None:
        """Register all handlers with the application."""
        try:
            handlers = self.get_handlers()
            group = getattr(self, 'group', None)
            
            for handler in handlers:
                if isinstance(handler, ConversationHandler):
                    # Register conversation handlers with persistence
                    application.add_handler(handler, group=group)
                    logger.debug(f"Registered conversation handler in group {group}")
                else:
                    # Register regular handlers
                    application.add_handler(handler, group=group)
                    logger.debug(f"Registered handler {handler.__class__.__name__} in group {group}")
                    
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise 