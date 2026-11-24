import pytest


class FakeBackend:
    def __init__(self, name: str, store: dict[str, str] | None = None) -> None:
        self.name = name
        self.store = store if store is not None else {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass


@pytest.fixture
def backend_factory():
    return FakeBackend
