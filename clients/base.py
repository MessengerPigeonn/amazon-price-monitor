from __future__ import annotations

import asyncio
import threading
import time
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter."""

    def __init__(self, max_calls: float, period_seconds: float = 1.0):
        self.max_calls = max_calls
        self.period = period_seconds
        self._tokens = max_calls
        self._last_refill = time.monotonic()
        self._async_lock = None
        self._sync_lock = threading.Lock()

    def _get_async_lock(self):
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    async def acquire(self):
        async with self._get_async_lock():
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.max_calls, self._tokens + elapsed * (self.max_calls / self.period))
            self._last_refill = now

            if self._tokens < 1:
                wait = (1 - self._tokens) * (self.period / self.max_calls)
                logger.debug(f"Rate limiter waiting {wait:.2f}s")
                await asyncio.sleep(wait)
                self._tokens = 0
            else:
                self._tokens -= 1

    def acquire_sync(self):
        with self._sync_lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.max_calls, self._tokens + elapsed * (self.max_calls / self.period))
            self._last_refill = now

            if self._tokens < 1:
                wait = (1 - self._tokens) * (self.period / self.max_calls)
                logger.debug(f"Rate limiter waiting {wait:.2f}s")
                time.sleep(wait)
                self._tokens = 0
            else:
                self._tokens -= 1


class BaseClient(ABC):
    """Abstract base for API clients."""

    def __init__(self, rate_limiter: RateLimiter | None = None):
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if API credentials are set."""
        ...

    async def _rate_limit(self):
        if self.rate_limiter:
            await self.rate_limiter.acquire()

    def _rate_limit_sync(self):
        if self.rate_limiter:
            self.rate_limiter.acquire_sync()
