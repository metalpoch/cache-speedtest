import contextlib
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.backends import MemoryBackend, PostgresBackend, RedisBackend
from app.config import get_settings

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    backends = {
        "memory": MemoryBackend(
            max_size=settings.memory_max_size,
            ttl=settings.memory_ttl_seconds,
        ),
        "redis": RedisBackend(settings.redis_url),
        "postgres": PostgresBackend(
            settings.database_url,
            min_size=settings.pg_pool_min_size,
            max_size=settings.pg_pool_max_size,
            auto_migrate=settings.pg_auto_migrate,
        ),
    }

    errors: dict[str, str] = defaultdict(str)
    try:
        await backends["postgres"].connect()
    except Exception as exc:  # la app arranca aunque PostgreSQL no esté listo
        errors["postgres"] = str(exc)

    app.state.backends = backends
    app.state.startup_errors = dict(errors)

    try:
        yield
    finally:
        for backend in backends.values():
            with contextlib.suppress(Exception):
                await backend.close()


app = FastAPI(title="Latency Lab", lifespan=lifespan)
app.include_router(router)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
