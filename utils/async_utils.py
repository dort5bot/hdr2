#utils/async_utils.py - ÇOK FAYDALI
import asyncio
import aiofiles
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def async_open_file(path: str, mode: str = 'r') -> AsyncGenerator:
    """Async file context manager"""
    try:
        async with aiofiles.open(path, mode) as f:
            yield f
    except Exception as e:
        logger.error(f"Async file operation failed: {e}")
        raise

async def async_batch_processing(items, process_func, batch_size=10):
    """Async batch processing with rate limiting"""
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        tasks = [process_func(item) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
        
        yield results
        
        # Rate limiting
        await asyncio.sleep(0.1)

class AsyncRateLimiter:
    """Async rate limiter for API calls"""
    def __init__(self, calls_per_second: int = 5):
        self.calls_per_second = calls_per_second
        self.semaphore = asyncio.Semaphore(calls_per_second)
        self.last_call = 0

    async def __aenter__(self):
        await self.semaphore.acquire()
        now = asyncio.get_event_loop().time()
        delay = max(0, 1.0 / self.calls_per_second - (now - self.last_call))
        if delay > 0:
            await asyncio.sleep(delay)
        self.last_call = asyncio.get_event_loop().time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.semaphore.release()
