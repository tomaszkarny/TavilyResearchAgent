import time
import logging
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')

def retry(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """
    Retry decorator for handling transient API errors
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {attempts} failed: {str(e)}. Retrying...")
                    time.sleep(delay * attempts)  # Exponential backoff
            
            raise Exception(f"Failed after {max_attempts} attempts")
        return wrapper
    return decorator 