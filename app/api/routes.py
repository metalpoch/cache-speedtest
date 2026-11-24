from collections.abc import Mapping

from fastapi import APIRouter, HTTPException, Request

from app.backends.base import StorageBackend
from app.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    HealthResponse,
    VariableRequest,
    VariableResponse,
)
from app.services.benchmark import run_benchmark
from app.services.variables import (
    delete_variable,
    read_variable,
    write_variable,
)

router = APIRouter(prefix="/api")


def _backends(request: Request) -> Mapping[str, StorageBackend]:
    return request.app.state.backends


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    status: dict[str, bool] = {}
    for name, backend in _backends(request).items():
        try:
            status[name] = await backend.ping()
        except Exception:
            status[name] = False
    return HealthResponse(**status)


@router.get("/variables/{key}", response_model=VariableResponse)
async def get_variable(key: str, request: Request) -> VariableResponse:
    value, source = await read_variable(_backends(request), key)
    return VariableResponse(key=key, value=value, source=source)


@router.put("/variables/{key}", response_model=VariableResponse)
async def put_variable(
    key: str, payload: VariableRequest, request: Request
) -> VariableResponse:
    await write_variable(_backends(request), key, payload.value)
    return VariableResponse(key=key, value=payload.value, source="all")


@router.delete("/variables/{key}", response_model=VariableResponse)
async def remove_variable(key: str, request: Request) -> VariableResponse:
    await delete_variable(_backends(request), key)
    return VariableResponse(key=key, value=None, source=None)


@router.post("/benchmark", response_model=BenchmarkResponse)
async def benchmark(
    payload: BenchmarkRequest, request: Request
) -> BenchmarkResponse:
    available = _backends(request)
    names = list(dict.fromkeys(payload.backends))
    unknown = [name for name in names if name not in available]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"Backend desconocido: {', '.join(unknown)}"
        )
    if not names:
        raise HTTPException(status_code=400, detail="Selecciona al menos un backend")

    selected = [available[name] for name in names]
    try:
        return await run_benchmark(selected, payload)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Algún backend no está disponible: {exc}",
        ) from exc
