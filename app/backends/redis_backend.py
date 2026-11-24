import redis.asyncio as aioredis


class RedisBackend:
    """Valkey o Redis: mismo protocolo, mismo cliente."""

    name = "redis"

    def __init__(self, url: str) -> None:
        self._client = aioredis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str) -> None:
        await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def ping(self) -> bool:
        return bool(await self._client.ping())

    async def close(self) -> None:
        await self._client.aclose()
