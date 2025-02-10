"""Base handler mixin for consistent handler registration."""
from typing import List
from telegram.ext import BaseHandler, Application
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
        
    def register_handlers(self, application) -> None:
        """Register all handlers with the application."""
        handlers = self.get_handlers()
        group = getattr(self, 'group', None)
        
        for handler in handlers:
            if group is not None:
                application.add_handler(handler, group=group)
            else:
                application.add_handler(handler)

    def register_handlers_with_application(self, application: Application) -> None:
        """Register handlers with the application."""
        try:
            handlers = self.get_handlers()
            for handler in handlers:
                application.add_handler(handler)
                logger.debug(f"Registered handler: {handler.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise 