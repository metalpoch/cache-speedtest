import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.backends import MemoryBackend
from tests.conftest import FakeBackend


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.state.backends = {
        "memory": MemoryBackend(max_size=32, ttl=60),
        "redis": FakeBackend("redis"),
        "postgres": FakeBackend("postgres"),
    }
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"memory": True, "redis": True, "postgres": True}


async def test_put_and_read_variable(client):
    response = await client.put("/api/variables/theta", json={"value": "otro"})
    assert response.status_code == 200
    assert response.json()["value"] == "otro"

    response = await client.get("/api/variables/theta")
    assert response.json() == {"key": "theta", "value": "otro", "source": "memory"}

    response = await client.delete("/api/variables/theta")
    assert response.json()["value"] is None

    response = await client.get("/api/variables/theta")
    assert response.json()["value"] is None


async def test_benchmark_endpoint(client):
    response = await client.post(
        "/api/benchmark",
        json={
            "key": "theta",
            "value": "42",
            "iterations": 5,
            "warmup": 1,
            "concurrency": 1,
            "operations": ["read"],
            "backends": ["memory", "redis", "postgres"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["iterations"] == 5
    assert len(data["results"]) == 3
    assert data["results"][0]["operations"]["read"]["samples"] == 5


async def test_benchmark_rejects_unknown_backend(client):
    response = await client.post(
        "/api/benchmark", json={"backends": ["mysql"], "iterations": 1}
    )
    assert response.status_code == 422
    assert "mysql" in response.text


async def test_benchmark_reports_unavailable_backend():
    class BrokenBackend(FakeBackend):
        async def set(self, key: str, value: str) -> None:
            raise ConnectionError("valkey caído")

    app = FastAPI()
    app.include_router(router)
    app.state.backends = {
        "memory": MemoryBackend(max_size=8, ttl=60),
        "redis": BrokenBackend("redis"),
        "postgres": FakeBackend("postgres"),
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post(
            "/api/benchmark",
            json={"iterations": 2, "backends": ["memory", "redis"]},
        )

    assert response.status_code == 503
    assert "valkey caído" in response.json()["detail"]
