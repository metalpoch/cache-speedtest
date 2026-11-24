import asyncio

from cachetools import TTLCache


class MemoryBackend:
    name = "memory"

    def __init__(self, max_size: int = 4096, ttl: int = 3600) -> None:
        self._cache: TTLCache[str, str] = TTLCache(maxsize=max_size, ttl=ttl)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            self._cache[key] = value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        async with self._lock:
            self._cache.clear()
