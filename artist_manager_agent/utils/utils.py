"""Utility functions and decorators."""
import asyncio
from functools import wraps
from typing import Any, Callable, Type, Union, List
import time
from .logger import get_logger, log_event, log_error

logger = get_logger(__name__)

def async_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception
):
    """Retry async function with exponential backoff."""
    if isinstance(exceptions, type):
        exceptions = (exceptions,)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries - 1:
                        log_event("retry_attempt", {
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "delay": current_delay,
                            "error": str(e)
                        })
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        log_error(e, {
                            "function": func.__name__,
                            "final_attempt": True,
                            "total_attempts": retries
                        })
            raise last_exception

        return wrapper
    return decorator

class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self.timestamps = []

    async def acquire(self):
        """Acquire a rate limit token."""
        now = time.time()
        
        # Remove timestamps outside the window
        self.timestamps = [ts for ts in self.timestamps if ts > now - self.period]
        
        if len(self.timestamps) >= self.calls:
            sleep_time = self.timestamps[0] - (now - self.period)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.timestamps.append(now)

def validate_input(func: Callable):
    """Validate function input parameters."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Log function call
        log_event("function_call", {
            "function": func.__name__,
            "args": str(args),
            "kwargs": str(kwargs)
        })
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            log_error(e, {
                "function": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs)
            })
            raise

    return wrapper

def measure_performance(func: Callable):
    """Measure function execution time."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            log_event("performance_metric", {
                "function": func.__name__,
                "execution_time": execution_time,
                "success": True
            })
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            log_event("performance_metric", {
                "function": func.__name__,
                "execution_time": execution_time,
                "success": False,
                "error": str(e)
            })
            raise
            
    return wrapper 