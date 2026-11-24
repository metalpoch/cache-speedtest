from collections.abc import Mapping

from app.backends.base import StorageBackend


async def read_variable(
    backends: Mapping[str, StorageBackend], key: str
) -> tuple[str | None, str | None]:
    """Read-through: memoria -> Redis/Valkey -> PostgreSQL.

    En un miss se pueblan las capas superiores para que la siguiente
    lectura ya encuentre el valor en memoria.
    """
    value = await backends["memory"].get(key)
    if value is not None:
        return value, "memory"

    if "redis" in backends:
        value = await backends["redis"].get(key)
        if value is not None:
            await backends["memory"].set(key, value)
            return value, "redis"

    if "postgres" in backends:
        value = await backends["postgres"].get(key)
        if value is not None:
            if "redis" in backends:
                await backends["redis"].set(key, value)
            await backends["memory"].set(key, value)
            return value, "postgres"

    return None, None


async def write_variable(
    backends: Mapping[str, StorageBackend], key: str, value: str
) -> None:
    for backend in backends.values():
        await backend.set(key, value)


async def delete_variable(
    backends: Mapping[str, StorageBackend], key: str
) -> None:
    for backend in backends.values():
        await backend.delete(key)
