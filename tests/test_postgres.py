import asyncpg

from app.backends.postgres import CREATE_TABLE_SQL, PostgresBackend


class FakeConnection:
    def __init__(self, executed: list[str]) -> None:
        self.executed = executed

    async def execute(self, sql: str) -> None:
        self.executed.append(sql)


class FakeAcquire:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(self, *args: object) -> bool:
        return False


class FakePool:
    def __init__(self, executed: list[str]) -> None:
        self.connection = FakeConnection(executed)

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.connection)

    async def close(self) -> None:
        pass


def fake_pool_factory(monkeypatch, executed: list[str]) -> None:
    async def create_pool(**kwargs):
        return FakePool(executed)

    monkeypatch.setattr(asyncpg, "create_pool", create_pool)


async def test_connect_creates_table_by_default(monkeypatch):
    executed: list[str] = []
    fake_pool_factory(monkeypatch, executed)

    backend = PostgresBackend("postgresql://example/db")
    await backend.connect()

    assert executed == [CREATE_TABLE_SQL]
    await backend.close()


async def test_connect_can_skip_migration(monkeypatch):
    executed: list[str] = []
    fake_pool_factory(monkeypatch, executed)

    backend = PostgresBackend(
        "postgresql://example/db", auto_migrate=False
    )
    await backend.connect()

    assert executed == []
    await backend.close()
