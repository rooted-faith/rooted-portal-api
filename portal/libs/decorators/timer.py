"""
decorator for timing functions
"""
import inspect
import time
from functools import wraps
from typing import Callable

from portal.libs.logger import logger


def timer(func: Callable) -> Callable:
    """
    decorator for timing functions
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        wrapper
        :param args:
        :param kwargs:
        :return:
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds.")
        return result

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        """
        wrapper
        :param args:
        :param kwargs:
        :return:
        """
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds.")
        return result

    wrapper = async_wrapper if inspect.iscoroutinefunction(func) else wrapper
    return wrapper
