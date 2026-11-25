import asyncpg

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runtime_variables (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


class PostgresBackend:
    """Consultas directas con asyncpg, sin ORM."""

    name = "postgres"

    def __init__(
        self,
        dsn: str,
        min_size: int = 1,
        max_size: int = 10,
        auto_migrate: bool = True,
    ) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._auto_migrate = auto_migrate
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("El pool de PostgreSQL no está conectado")
        return self._pool

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn, min_size=self._min_size, max_size=self._max_size
        )
        if self._auto_migrate:
            async with self._pool.acquire() as connection:
                await connection.execute(CREATE_TABLE_SQL)

    async def get(self, key: str) -> str | None:
        return await self.pool.fetchval(
            "SELECT value FROM runtime_variables WHERE key = $1", key
        )

    async def set(self, key: str, value: str) -> None:
        await self.pool.execute(
            """
            INSERT INTO runtime_variables (key, value)
            VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = now()
            """,
            key,
            value,
        )

    async def delete(self, key: str) -> None:
        await self.pool.execute(
            "DELETE FROM runtime_variables WHERE key = $1", key
        )

    async def ping(self) -> bool:
        return await self.pool.fetchval("SELECT 1") == 1

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
