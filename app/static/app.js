const BACKEND_LABEL = {
  memory: "memoria",
  redis: "valkey",
  postgres: "postgres",
};
const OPERATION_LABEL = { read: "lectura", write: "escritura" };

const form = document.getElementById("bench-form");
const runButton = document.getElementById("run");
const actionHint = document.getElementById("action-hint");
const resultsNode = document.getElementById("results");
const resultsMeta = document.getElementById("results-meta");
const errorNode = document.getElementById("error");

function showError(message) {
  errorNode.textContent = message;
  errorNode.hidden = false;
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("sin respuesta del servidor");
    const data = await response.json();
    document.querySelectorAll(".status-item").forEach((item) => {
      const name = item.dataset.backend;
      item.classList.toggle("is-up", Boolean(data[name]));
      item.classList.toggle("is-down", !data[name]);
    });
  } catch {
    document.querySelectorAll(".status-item").forEach((item) => {
      item.classList.add("is-down");
    });
  }
}

function fmt(value) {
  if (value === 0) return "0";
  if (value < 1) return value.toFixed(3);
  if (value < 100) return value.toFixed(2);
  return Math.round(value).toLocaleString("es-ES");
}

function sparkline(values) {
  const data = values.length ? values : [0];
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const points = data
    .map((value, index) => {
      const x = (index / Math.max(1, data.length - 1)) * 100;
      const y = 42 - ((value - min) / span) * 36;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return `<svg viewBox="0 0 100 46" preserveAspectRatio="none" aria-hidden="true">
    <line class="baseline" x1="0" y1="45" x2="100" y2="45" />
    <polyline class="line" points="${points}" />
  </svg>`;
}

function panel(backend, operation, stats, minP50, maxP50, comparison) {
  let width = 100;
  if (maxP50 > minP50 && stats.p50_us > 0 && minP50 > 0) {
    const ratio =
      (Math.log10(stats.p50_us) - Math.log10(minP50)) /
      (Math.log10(maxP50) - Math.log10(minP50));
    width = Math.max(3, Math.min(100, ratio * 100));
  }

  const ratioKey = `${backend}:${operation}:p50_us_vs_memory`;
  const ratio = comparison[ratioKey];
  const compareNote =
    backend === "memory"
      ? "referencia de la comparación"
      : ratio !== undefined
        ? `${fmt(ratio)}× frente a memoria`
        : "sin referencia disponible";

  return `<article class="result is-new" data-backend="${backend}">
    <div class="result-head">
      <span class="result-name"><i></i>${BACKEND_LABEL[backend] || backend}</span>
      <span class="result-op">${OPERATION_LABEL[operation] || operation}</span>
    </div>
    <div class="result-main">
      <div class="big-number">${fmt(stats.p50_us)}<small>µs</small></div>
      <div class="metric-label">mediana · p50</div>
    </div>
    <div class="stat-row">
      <div><div class="stat-value">${fmt(stats.p95_us)}</div><div class="stat-label">p95 µs</div></div>
      <div><div class="stat-value">${fmt(stats.p99_us)}</div><div class="stat-label">p99 µs</div></div>
      <div><div class="stat-value">${fmt(stats.ops_per_second)}</div><div class="stat-label">ops/s</div></div>
    </div>
    <div class="spark">${sparkline(stats.timeline_us)}</div>
    <div class="compare">
      <div class="compare-label">latencia relativa · escala logarítmica</div>
      <div class="bar-track"><div class="bar-fill" style="width:${width.toFixed(1)}%"></div></div>
      <div class="compare-note">${compareNote} · ${stats.samples} muestras · ${stats.errors} errores</div>
    </div>
  </article>`;
}

function render(data) {
  const panels = [];
  for (const result of data.results) {
    for (const [operation, stats] of Object.entries(result.operations)) {
      panels.push({ backend: result.backend, operation, stats });
    }
  }

  resultsNode.innerHTML = "";
  if (!panels.length) {
    resultsNode.innerHTML =
      '<div class="empty-state"><span class="empty-mark">◇</span><p>Sin datos.</p></div>';
    return;
  }

  for (const operation of Object.keys(OPERATION_LABEL)) {
    const group = panels.filter((item) => item.operation === operation);
    if (!group.length) continue;
    const values = group.map((item) => item.stats.p50_us).filter((v) => v > 0);
    const min = values.length ? Math.min(...values) : 0;
    const max = values.length ? Math.max(...values) : 0;
    for (const item of group) {
      resultsNode.insertAdjacentHTML(
        "beforeend",
        panel(item.backend, operation, item.stats, min, max, data.comparison),
      );
    }
  }

  resultsMeta.textContent = `${data.iterations.toLocaleString("es-ES")} iteraciones · ${data.concurrency} tareas · clave ${data.key}`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorNode.hidden = true;

  const operations = [...form.querySelectorAll('input[name="operation"]:checked')].map(
    (input) => input.value,
  );
  const backends = [...form.querySelectorAll('input[name="backend"]:checked')].map(
    (input) => input.value,
  );

  if (!operations.length || !backends.length) {
    showError("Selecciona al menos una operación y una capa.");
    return;
  }

  const field = (name) => form.elements.namedItem(name).value;
  const payload = {
    key: field("key"),
    value: field("value"),
    iterations: Number(field("iterations")),
    warmup: Number(field("warmup")),
    concurrency: Number(field("concurrency")),
    operations,
    backends,
  };

  runButton.disabled = true;
  actionHint.textContent = "midiendo…";

  try {
    const response = await fetch("/api/benchmark", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `error ${response.status}`);
    }
    render(data);
  } catch (error) {
    showError(`No se pudo completar la medición: ${error.message}`);
  } finally {
    runButton.disabled = false;
    actionHint.textContent = "las capas se miden por separado, no en paralelo";
  }
});

checkHealth();
