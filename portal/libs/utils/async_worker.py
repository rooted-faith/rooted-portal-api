"""
Task concurrency
"""
import asyncio
from collections.abc import Coroutine

CONCURRENT_NUMBER = 10
semaphore = asyncio.Semaphore(CONCURRENT_NUMBER)


async def concurrency_worker(futures: list[asyncio.Future | Coroutine], return_exceptions: bool = False):
    """
    concurrency worker
    :param futures:
    :param return_exceptions:
    :return:
    """
    async with semaphore:
        return await asyncio.gather(*futures, return_exceptions=return_exceptions)
