"""Handler registry for managing bot command handlers."""
from typing import Dict, Any, List, Set, Tuple
from telegram.ext import Application, BaseHandler
from ...utils.logger import get_logger

logger = get_logger(__name__)

class HandlerRegistry:
    """Registry for managing bot command handlers."""
    
    def __init__(self):
        """Initialize an empty handler registry."""
        self._handlers: Dict[int, List[Any]] = {}  # Group -> List of handlers
        self._registered_handlers: Set[int] = set()  # Set of handler IDs
        self._command_registry: Dict[str, List[int]] = {}  # Command -> List of group numbers
        
    def register_handler(self, group: int, handler: Any) -> None:
        """Register a handler with a specific group number."""
        try:
            handler_id = id(handler)
            if handler_id in self._registered_handlers:
                logger.warning(f"Handler {handler.__class__.__name__} already registered")
                return
            
            # Initialize group if not exists
            if group not in self._handlers:
                self._handlers[group] = []
            
            # Register handler
            self._handlers[group].append(handler)
            self._registered_handlers.add(handler_id)
            
            # Register commands if it's a command handler
            if hasattr(handler, 'command'):
                command = handler.command
                if command not in self._command_registry:
                    self._command_registry[command] = []
                self._command_registry[command].append(group)
                logger.debug(f"Registered command '{command}' in group {group}")
            
            logger.debug(f"Registered handler {handler.__class__.__name__} in group {group}")
            
        except Exception as e:
            logger.error(f"Error registering handler: {str(e)}", exc_info=True)
            raise
            
    def register_all(self, application: Application) -> None:
        """Register all handlers with the application in group order."""
        try:
            # Sort handlers by group number
            sorted_groups = sorted(self._handlers.items())
            
            # Check for command conflicts
            self._check_command_conflicts()
            
            # Register each handler group
            for group, handlers in sorted_groups:
                try:
                    logger.debug(f"Registering handlers for group {group}")
                    for handler in handlers:
                        try:
                            application.add_handler(handler, group=group)
                            logger.debug(f"Added handler {handler.__class__.__name__} to group {group}")
                        except Exception as e:
                            logger.error(f"Error adding handler {handler.__class__.__name__}: {e}", exc_info=True)
                            raise
                except Exception as e:
                    logger.error(f"Error registering handlers for group {group}: {e}", exc_info=True)
                    raise
                    
            logger.info(f"Registered {len(self._registered_handlers)} handlers in {len(sorted_groups)} groups")
            
        except Exception as e:
            logger.error(f"Error registering handlers: {e}", exc_info=True)
            raise
            
    def _check_command_conflicts(self) -> None:
        """Check for command conflicts between handlers."""
        for command, groups in self._command_registry.items():
            if len(groups) > 1:
                logger.warning(
                    f"Command '{command}' is registered in multiple groups: {groups}. "
                    f"This may cause duplicate responses."
                )
    
    def clear(self) -> None:
        """Clear all registered handlers."""
        try:
            self._handlers.clear()
            self._registered_handlers.clear()
            self._command_registry.clear()
            logger.debug("Cleared all handlers")
            
        except Exception as e:
            logger.error(f"Error clearing handlers: {e}", exc_info=True)
            raise
            
    def get_handler(self, group: int) -> List[Any]:
        """Get handlers for a specific group."""
        return self._handlers.get(group, [])
        
    def get_all_handlers(self) -> Dict[int, List[Any]]:
        """Get all registered handlers."""
        return dict(self._handlers)
        
    def get_command_handlers(self, command: str) -> List[Tuple[int, Any]]:
        """Get all handlers for a specific command."""
        handlers = []
        if command in self._command_registry:
            for group in self._command_registry[command]:
                for handler in self._handlers[group]:
                    if hasattr(handler, 'command') and handler.command == command:
                        handlers.append((group, handler))
        return handlers
        
    def __len__(self) -> int:
        """Get the number of registered handlers."""
        return len(self._registered_handlers) 