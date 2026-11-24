from typing import Literal

from pydantic import BaseModel, Field

BackendName = Literal["memory", "redis", "postgres"]
OperationName = Literal["read", "write"]


class BenchmarkRequest(BaseModel):
    key: str = "theta"
    value: str = "42"
    iterations: int = Field(default=500, ge=1, le=100_000)
    warmup: int = Field(default=50, ge=0, le=10_000)
    concurrency: int = Field(default=1, ge=1, le=256)
    operations: list[OperationName] = Field(
        default_factory=lambda: ["read", "write"]
    )
    backends: list[BackendName] = Field(
        default_factory=lambda: ["memory", "redis", "postgres"]
    )


class OperationStats(BaseModel):
    samples: int
    min_us: float
    mean_us: float
    p50_us: float
    p90_us: float
    p95_us: float
    p99_us: float
    max_us: float
    stdev_us: float
    ops_per_second: float
    errors: int
    timeline_us: list[float]


class BackendResult(BaseModel):
    backend: BackendName
    operations: dict[str, OperationStats]


class BenchmarkResponse(BaseModel):
    key: str
    iterations: int
    warmup: int
    concurrency: int
    results: list[BackendResult]
    comparison: dict[str, float]


class HealthResponse(BaseModel):
    memory: bool
    redis: bool
    postgres: bool


class VariableRequest(BaseModel):
    value: str


class VariableResponse(BaseModel):
    key: str
    value: str | None
    source: str | None
