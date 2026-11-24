# Latency Lab

API para medir la latencia de lectura y escritura de una misma variable en tres capas:

- **memoria** — `cachetools.TTLCache`
- **caché distribuida** — Valkey / Redis (`redis.asyncio`)
- **PostgreSQL** — consultas directas con `asyncpg` (sin ORM)

Incluye una interfaz gótica que presenta los resultados con escalas logarítmicas y una silueta estilo justiciero nocturno.

## Arranque

```bash
cp .env.example .env
make up
```

Abre <http://localhost:8000>. Los contenedores levantan Valkey, PostgreSQL (con la tabla del `sql/init.sql`) y la app.

Para correr la app en tu máquina contra los contenedores:

```bash
docker compose up -d valkey postgres
# en .env: REDIS_URL=redis://localhost:6379/0
#          DATABASE_URL=postgresql://bench:bench@localhost:5432/bench
make dev
```

Las URIs se leen de `.env` mediante `pydantic-settings`.

## API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/health` | estado de las tres capas |
| `GET` | `/api/variables/{key}` | lectura con read-through (memoria → valkey → postgres) |
| `PUT` | `/api/variables/{key}` | escribe el valor en las tres capas |
| `DELETE` | `/api/variables/{key}` | borra la clave en las tres capas |
| `POST` | `/api/benchmark` | ejecuta la medición |

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/benchmark \
  -H 'Content-Type: application/json' \
  -d '{"key":"theta","value":"42","iterations":1000,"warmup":100,"concurrency":16,"operations":["read","write"],"backends":["memory","redis","postgres"]}'
```

## Cómo se mide

- Se siembra la clave una vez antes de cronometrar, para que las lecturas no midan un `miss`.
- Cada llamada se cronometra con `time.perf_counter_ns()`. El warmup se ejecuta antes de la fase medida.
- Con `concurrency > 1` se reparten las iteraciones entre tareas `asyncio` y se mide la latencia por operación; el rendimiento (`ops/s`) se calcula sobre el tiempo total de la fase.
- Se devuelven `min`, `media`, `p50`, `p90`, `p95`, `p99`, `máx`, `desviación`, `ops/s`, errores y una muestra de la serie temporal para dibujar la gráfica.
- Las capas se miden **secuencialmente entre sí** para que no se contaminen por competencia por CPU; dentro de cada capa la concurrencia sí es configurable.
- `comparison` contiene los factores `p50` y `p95` de cada capa respecto a memoria.

## Pruebas

```bash
make test
```
