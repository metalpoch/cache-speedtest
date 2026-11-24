import asyncio

from app.schemas import BenchmarkRequest
from app.services.benchmark import measure, percentile, run_benchmark, summarize
from app.services.variables import read_variable, write_variable


def test_percentile_interpolates():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([7], 0.99) == 7


def test_summarize_returns_microseconds_and_throughput():
    stats = summarize([1_000, 2_000, 3_000, 4_000], 4_000_000, 0)
    assert stats.p50_us == 2.5
    assert stats.min_us == 1.0
    assert stats.max_us == 4.0
    assert stats.ops_per_second == 1_000.0
    assert len(stats.timeline_us) == 4


async def test_measure_sequential_and_concurrent():
    async def operation():
        await asyncio.sleep(0.001)

    sequential = await measure(operation, 10, warmup=2, concurrency=1)
    concurrent = await measure(operation, 10, warmup=2, concurrency=5)

    assert sequential.samples == 10
    assert concurrent.samples == 10
    assert sequential.errors == concurrent.errors == 0
    assert sequential.p50_us > 0


async def test_measure_counts_errors():
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        if calls % 2 == 0:
            raise ValueError("fallo simulado")

    stats = await measure(operation, 6, warmup=0, concurrency=1)
    assert stats.errors == 3
    assert stats.samples == 6


async def test_read_through_populates_upper_layers(backend_factory):
    memory = backend_factory("memory")
    redis = backend_factory("redis", {"clave": "desde-redis"})
    postgres = backend_factory("postgres", {"clave": "desde-pg"})
    backends = {"memory": memory, "redis": redis, "postgres": postgres}

    value, source = await read_variable(backends, "clave")
    assert (value, source) == ("desde-redis", "redis")
    assert memory.store["clave"] == "desde-redis"

    memory.store.clear()
    redis.store.clear()
    value, source = await read_variable(backends, "clave")
    assert (value, source) == ("desde-pg", "postgres")
    assert redis.store["clave"] == "desde-pg"
    assert memory.store["clave"] == "desde-pg"


async def test_benchmark_read_and_write(backend_factory):
    backends = [
        backend_factory("memory"),
        backend_factory("redis"),
        backend_factory("postgres"),
    ]
    request = BenchmarkRequest(
        key="theta",
        value="42",
        iterations=8,
        warmup=2,
        concurrency=2,
        operations=["read", "write"],
        backends=["memory", "redis", "postgres"],
    )

    response = await run_benchmark(backends, request)

    assert [result.backend for result in response.results] == [
        "memory",
        "redis",
        "postgres",
    ]
    for result in response.results:
        assert set(result.operations) == {"read", "write"}
        assert all(stats.samples == 8 for stats in result.operations.values())
        assert all(stats.errors == 0 for stats in result.operations.values())
    assert any("vs_memory" in key for key in response.comparison)
