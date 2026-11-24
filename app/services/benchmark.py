import asyncio
import math
import statistics
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from app.backends.base import StorageBackend
from app.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    BackendResult,
    OperationStats,
)

TIMELINE_POINTS = 60


def percentile(sorted_values: Sequence[float], fraction: float) -> float:
    """Percentil interpolado sobre una lista ya ordenada."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _downsample(values: Sequence[float], limit: int = TIMELINE_POINTS) -> list[float]:
    if not values:
        return []
    step = max(1, len(values) // limit)
    return [round(v, 3) for v in values[::step][:limit]]


def summarize(
    samples_ns: list[int], wall_ns: int, errors: int
) -> OperationStats:
    samples_us = [v / 1000.0 for v in samples_ns]
    ordered = sorted(samples_us)
    seconds = wall_ns / 1_000_000_000
    return OperationStats(
        samples=len(samples_us),
        min_us=round(ordered[0], 3) if ordered else 0.0,
        mean_us=round(statistics.fmean(samples_us), 3) if samples_us else 0.0,
        p50_us=round(percentile(ordered, 0.50), 3),
        p90_us=round(percentile(ordered, 0.90), 3),
        p95_us=round(percentile(ordered, 0.95), 3),
        p99_us=round(percentile(ordered, 0.99), 3),
        max_us=round(ordered[-1], 3) if ordered else 0.0,
        stdev_us=round(statistics.pstdev(samples_us), 3)
        if len(samples_us) > 1
        else 0.0,
        ops_per_second=round(len(samples_us) / seconds, 1) if seconds > 0 else 0.0,
        errors=errors,
        timeline_us=_downsample(samples_us),
    )


async def measure(
    operation: Callable[[], Awaitable[Any]],
    iterations: int,
    warmup: int,
    concurrency: int,
) -> OperationStats:
    """Mide una coroutine many veces; devuelve estadísticas en microsegundos."""
    for _ in range(warmup):
        await operation()

    samples: list[int] = []
    errors = 0
    wall_start = time.perf_counter_ns()

    async def worker(count: int) -> tuple[list[int], int]:
        local_samples: list[int] = []
        local_errors = 0
        for _ in range(count):
            started = time.perf_counter_ns()
            try:
                await operation()
            except Exception:
                local_errors += 1
            local_samples.append(time.perf_counter_ns() - started)
        return local_samples, local_errors

    if concurrency <= 1:
        result_samples, result_errors = await worker(iterations)
        samples.extend(result_samples)
        errors += result_errors
    else:
        base, remainder = divmod(iterations, concurrency)
        counts = [base + (1 if i < remainder else 0) for i in range(concurrency)]
        batches = await asyncio.gather(*(worker(c) for c in counts))
        for batch_samples, batch_errors in batches:
            samples.extend(batch_samples)
            errors += batch_errors

    wall_ns = time.perf_counter_ns() - wall_start
    return summarize(samples, wall_ns, errors)


async def run_benchmark(
    backends: Sequence[StorageBackend], request: BenchmarkRequest
) -> BenchmarkResponse:
    # Sembrar la clave una vez, fuera de la medición, para que las lecturas
    # encuentren datos y no midamos un miss.
    for backend in backends:
        await backend.set(request.key, request.value)

    results: list[BackendResult] = []
    for backend in backends:
        operations: dict[str, OperationStats] = {}

        for name in request.operations:
            if name == "read":
                operation = lambda key=request.key: backend.get(key)
            else:
                operation = lambda key=request.key, value=request.value: backend.set(
                    key, value
                )

            operations[name] = await measure(
                operation,
                iterations=request.iterations,
                warmup=request.warmup,
                concurrency=request.concurrency,
            )

        results.append(BackendResult(backend=backend.name, operations=operations))

    comparison = _comparison(results)
    return BenchmarkResponse(
        key=request.key,
        iterations=request.iterations,
        warmup=request.warmup,
        concurrency=request.concurrency,
        results=results,
        comparison=comparison,
    )


def _comparison(results: Sequence[BackendResult]) -> dict[str, float]:
    by_name = {result.backend: result for result in results}
    reference_name = "memory" if "memory" in by_name else (
        results[0].backend if results else None
    )
    if reference_name is None:
        return {}

    comparison: dict[str, float] = {}
    reference = by_name[reference_name]
    for name, result in by_name.items():
        if name == reference_name:
            continue
        for operation, stats in result.operations.items():
            base = reference.operations.get(operation)
            if base is None:
                continue
            for metric in ("p50_us", "p95_us"):
                value = getattr(stats, metric)
                divisor = getattr(base, metric)
                if divisor <= 0:
                    continue
                comparison[f"{name}:{operation}:{metric}_vs_{reference_name}"] = round(
                    value / divisor, 2
                )
    return comparison
