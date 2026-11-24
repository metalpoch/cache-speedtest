from typing import Protocol


class StorageBackend(Protocol):
    """Contrato mínimo que deben cumplir las tres capas."""

    name: str

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def ping(self) -> bool: ...

    async def close(self) -> None: ...
