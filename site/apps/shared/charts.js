/* Python prepares every row. These adapters only lay out and draw those rows. */
const status = document.querySelector("#status");
const viewport = document.querySelector("#viewport");
const kind = document.body.dataset.renderer;
let current = null;
let chart = null;
let failed = false;
let revision = 0;
let latestRequest = null;
let renderQueue = Promise.resolve();
const timeout = setTimeout(
  () =>
    window.chartFailure(
      "Startup timed out. Check your internet connection and required CDN access.",
    ),
  120000,
);

window.chartFailure = (message) => {
  failed = true;
  clearTimeout(timeout);
  status.dataset.state = "error";
  status.textContent = `${message} Reload to retry. The book and navigation remain available.`;
  for (const id of ["view", "hour", "metric", "download"])
    document.getElementById(id).disabled = true;
};
window.chartQuery = () => {
  const params = new URLSearchParams(location.search);
  return JSON.stringify({
    renderer: kind,
    view: params.get("view") ?? "bars",
    hour: params.get("hour") ?? "all",
    metric: params.get("metric") ?? "total",
  });
};
if (window.pyscriptLoadFailed)
  window.chartFailure("Could not load the PyScript runtime. Check CDN access.");
window.addEventListener("py:error", (event) =>
  window.chartFailure(
    event.detail?.error?.message || "The Python runtime could not start.",
  ),
);
window.addEventListener("unhandledrejection", (event) =>
  window.chartFailure(event.reason?.message || String(event.reason)),
);

function loadScript(url, name) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = url;
    script.onload = resolve;
    script.onerror = () =>
      reject(new Error(`Could not load required ${name}. Check CDN access.`));
    document.head.append(script);
  });
}
window.chartRendererReady = loadScript(
  kind === "d3"
    ? "https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"
    : "https://cdn.jsdelivr.net/npm/@d3plus/core@4.10.0/umd/d3plus-core.full.min.js",
  kind === "d3" ? "D3" : "D3plus core",
);
window.chartRendererReady.catch((error) => window.chartFailure(error.message));

function clearChart() {
  if (chart) chart.destroy();
  chart = null;
  viewport.replaceChildren();
}

function d3Chart(summary, view, width, height) {
  const rows = summary.rows;
  const svg = d3
    .select(viewport)
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("role", "img");
  svg
    .append("title")
    .text(
      view === "points"
        ? "Synthetic NYC locations, projected without a basemap"
        : "Synthetic observations grouped by hour",
    );
  svg
    .append("desc")
    .text(
      "Values match the Python summary table below, which provides the accessible text alternative. Hover a mark for its value.",
    );
  const margin = { top: 32, right: 22, bottom: 58, left: 54 };
  if (view === "points") {
    // Fixed sample bounds keep locations stable when filtering one hour.
    const bounds = {
      type: "MultiPoint",
      coordinates: [
        [-74.025, 40.69],
        [-73.93, 40.79],
      ],
    };
    const projection = d3.geoMercator().fitExtent(
      [
        [35, 35],
        [width - 35, height - 125],
      ],
      bounds,
    );
    const radius = d3
      .scaleSqrt()
      .domain([0, d3.max(rows, (d) => d.value) || 1])
      .range([3, 14]);
    svg
      .selectAll("circle.observation")
      .data(rows, (d) => d.id)
      .join("circle")
      .attr("class", "observation")
      .attr("cx", (d) => projection([d.longitude, d.latitude])[0])
      .attr("cy", (d) => projection([d.longitude, d.latitude])[1])
      .attr("r", (d) => radius(d.value))
      .attr("fill", "#087e83")
      .attr("fill-opacity", 0.7)
      .attr("stroke", "#102e3c")
      .attr("tabindex", 0)
      .attr("aria-label", (d) => `${d.id}, ${d.label}: ${d.value}`)
      .append("title")
      .text((d) => `${d.label} (${d.id}): ${d.value}`);
    svg
      .append("text")
      .attr("x", width / 2)
      .attr("y", 20)
      .attr("text-anchor", "middle")
      .attr("class", "chart-note")
      .text("Synthetic locations · no basemap");
    const legend = svg
      .append("g")
      .attr("class", "point-legend")
      .attr("transform", `translate(18,${height - 94})`);
    legend
      .append("text")
      .attr("class", "chart-note")
      .text(
        summary.metadata.metric === "count"
          ? "Size: observation count"
          : "Size: total invented teaching units",
      );
    legend
      .append("text")
      .attr("class", "chart-note")
      .attr("y", 18)
      .text("Size scale is relative to selected observations");
    const maximum = radius.domain()[1];
    const references = [
      ...new Set([
        Math.max(1, Math.round(maximum / 4)),
        Math.max(1, Math.round(maximum / 2)),
        maximum,
      ]),
    ];
    const samples = legend
      .selectAll("g")
      .data(references)
      .join("g")
      .attr("transform", (_, index) => `translate(${14 + index * 96},58)`);
    samples
      .append("circle")
      .attr("r", (value) => radius(value))
      .attr("fill", "#087e83")
      .attr("fill-opacity", 0.7)
      .attr("stroke", "#102e3c");
    samples
      .append("text")
      .attr("class", "chart-note")
      .attr("x", 20)
      .attr("y", 4)
      .text((value) => value);
  } else {
    const x = d3
      .scaleBand()
      .domain(rows.map((d) => d.id))
      .range([margin.left, width - margin.right])
      .padding(0.25);
    const y = d3
      .scaleLinear()
      .domain([0, d3.max(rows, (d) => d.value) || 1])
      .nice()
      .range([height - margin.bottom, margin.top]);
    svg
      .append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).tickFormat((id) => `${id.padStart(2, "0")}:00`));
    svg
      .append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5));
    svg
      .selectAll("rect.hour-bar")
      .data(rows, (d) => d.id)
      .join("rect")
      .attr("class", "hour-bar")
      .attr("x", (d) => x(d.id))
      .attr("y", (d) => y(d.value))
      .attr("width", x.bandwidth())
      .attr("height", (d) => y(0) - y(d.value))
      .attr("fill", "#087e83")
      .attr("tabindex", 0)
      .attr("aria-label", (d) => `${d.label}: ${d.value}`)
      .append("title")
      .text((d) => `${d.label}: ${d.value}`);
    svg
      .append("text")
      .attr("x", margin.left)
      .attr("y", 18)
      .attr("class", "chart-note")
      .text(
        summary.metadata.metric === "count"
          ? "Observation count"
          : "Total invented teaching units",
      );
  }
}

async function draw(summary, view) {
  clearChart();
  if (!summary.rows.length) {
    const message = document.createElement("p");
    message.className = "chart-empty";
    message.textContent = "No observations at this hour. The chart is empty.";
    viewport.append(message);
    return;
  }
  const width = Math.max(260, viewport.clientWidth),
    height = viewport.clientHeight;
  if (kind === "d3") d3Chart(summary, view, width, height);
  else {
    chart = view === "treemap" ? new d3plus.Treemap() : new d3plus.BarChart();
    chart.config({
      select: viewport,
      data: summary.rows,
      groupBy: "id",
      width,
      height,
      duration: 0,
      detectVisible: false,
      detectResize: false,
      legend: false,
      zoom: false,
      saveControl: false,
      search: false,
      tableView: false,
      label: (datum) => datum.label,
      ...(view === "treemap" ? { sum: "value" } : { x: "id", y: "value" }),
    });
    await new Promise((resolve) => chart.render(resolve));
    const selector =
      view === "treemap"
        ? 'svg.d3plus-render-svg rect[data-key^="treemap-"]'
        : "svg.d3plus-render-svg rect[aria-label]";
    // Ready is based on actual graphics, not the presence of hidden No Data text.
    if (!viewport.querySelector(selector))
      throw new Error("D3plus did not produce chart marks.");
  }
}

function updateTable(summary) {
  const body = document.querySelector("#summary-body");
  body.replaceChildren();
  for (const row of summary.rows) {
    const tr = document.createElement("tr");
    for (const value of [
      row.id,
      row.label,
      row.count,
      row.total,
      row.value,
      row.longitude,
      row.latitude,
    ]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    }
    body.append(tr);
  }
  if (!summary.rows.length) {
    const tr = document.createElement("tr"),
      td = document.createElement("td");
    td.colSpan = 7;
    td.textContent = "No observations at this hour.";
    tr.append(td);
    body.append(tr);
  }
}
function enqueueRender(request) {
  if (failed) return Promise.resolve();
  const pending = { ...request, revision: ++revision };
  latestRequest = pending;
  document.getElementById("download").disabled = true;
  viewport.setAttribute("aria-busy", "true");
  status.dataset.state = "loading";
  status.textContent = "Rendering the Python summary…";
  // A D3plus callback can outlive another control/resize request. Only one draw
  // may mutate the container at a time, and superseded requests never commit.
  renderQueue = renderQueue
    .then(async () => {
      if (failed || pending !== latestRequest) return;
      const { serialized, summary, view } = pending;
      await draw(summary, view);
      if (failed || pending !== latestRequest) return;
      current = serialized;
      updateTable(summary);
      document.querySelector("#count").textContent =
        summary.metadata.feature_count;
      viewport.dataset.rowCount = summary.rows.length;
      viewport.dataset.hour = summary.metadata.selection_hour;
      viewport.dataset.metric = summary.metadata.metric;
      viewport.dataset.view = view;
      viewport.dataset.renderRevision = pending.revision;
      viewport.dataset.renderWidth = viewport.clientWidth;
      viewport.dataset.renderHeight = viewport.clientHeight;
      viewport.setAttribute("aria-busy", "false");
      // Keep selects enabled during updates so keyboard focus stays in place.
      for (const id of ["view", "hour", "metric", "download"])
        document.getElementById(id).disabled = false;
      status.dataset.state = "ready";
      status.textContent = summary.rows.length
        ? "Ready. Chart, table and JSON use the same Python summary."
        : "Ready. No observations at this hour; the chart and export are empty.";
      document.body.dataset.runtimeReady = "true";
      const params = new URLSearchParams({
        view,
        hour: String(summary.metadata.selection_hour),
        metric: summary.metadata.metric,
      });
      history.replaceState(null, "", `${location.pathname}?${params}`);
      clearTimeout(timeout);
    })
    .catch((error) => {
      window.chartFailure(error.message);
    });
  return renderQueue;
}
window.renderChart = (serialized) => {
  return enqueueRender({
    serialized,
    summary: JSON.parse(serialized),
    view: document.getElementById("view").value,
  });
};
window.downloadChart = () => {
  if (!current || failed) return;
  const url = URL.createObjectURL(
    new Blob([current], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `synthetic-nyc-${kind}-${document.getElementById("view").value}-hour-${document.getElementById("hour").value}-${document.getElementById("metric").value}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
let resizeTimer;
new ResizeObserver(() => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (latestRequest && !failed) enqueueRender(latestRequest);
  }, 150);
}).observe(viewport);
