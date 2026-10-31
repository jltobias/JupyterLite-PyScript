/* This bridge receives serialized GeoJSON; no Python objects leak to renderers. */
const status = document.querySelector("#status");
const viewport = document.querySelector("#viewport");
const kind = document.body.dataset.renderer;
let renderer;
let current = null;
let failed = false;
let interrupted = false;
const timeout = setTimeout(
  () =>
    window.labFailure(
      "Startup timed out. Check your internet connection and CDN access, then reload this page.",
    ),
  120000,
);
window.labFailure = (message) => {
  failed = true;
  clearTimeout(timeout);
  status.dataset.state = "error";
  status.textContent = `${message} Reload to retry. The book and navigation remain available.`;
  document.querySelector("#download").disabled = true;
  document.querySelector("#hour").disabled = true;
};
if (window.pyscriptLoadFailed) {
  window.labFailure("Could not load the PyScript runtime. Check CDN access.");
}
window.addEventListener("py:error", (event) =>
  window.labFailure(
    event.detail?.error?.message || "The Python runtime could not start.",
  ),
);
window.addEventListener("unhandledrejection", (event) =>
  window.labFailure(event.reason?.message || String(event.reason)),
);

const loadScript = (url) =>
  new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = url;
    script.onload = resolve;
    script.onerror = () =>
      reject(
        new Error(`Could not load ${new URL(url).hostname}. Check CDN access.`),
      );
    document.head.append(script);
  });

const loadStylesheet = (url) =>
  new Promise((resolve, reject) => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = url;
    link.onload = resolve;
    link.onerror = () =>
      reject(
        new Error(
          "Could not load the required Leaflet stylesheet. Check CDN access.",
        ),
      );
    document.head.append(link);
  });

async function leafletRenderer() {
  await Promise.all([
    loadScript("https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"),
    loadStylesheet(
      "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css",
    ),
  ]);
  const map = L.map(viewport).setView([40.744, -73.98], 12);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  })
    .on("tileerror", () => {
      document.querySelector("#renderer-note").textContent =
        "Basemap tiles could not load. Synthetic points and export still work; check network access.";
    })
    .addTo(map);
  const layer = L.geoJSON(null, {
    pointToLayer: (_, latlng) =>
      L.circleMarker(latlng, {
        radius: 7,
        color: "#064d59",
        weight: 1,
        fillColor: "#13a295",
        fillOpacity: 0.8,
      }),
    onEachFeature: (feature, marker) => {
      const p = feature.properties;
      marker.bindTooltip(
        `${p.name} · ${p.hour}:00 · simulated value ${p.value}`,
      );
    },
  }).addTo(map);
  return (collection) => {
    layer.clearLayers();
    layer.addData(collection);
  };
}

async function deckRenderer() {
  await loadScript("https://cdn.jsdelivr.net/npm/deck.gl@9.1.14/dist.min.js");
  const display = new deck.DeckGL({
    container: viewport,
    initialViewState: {
      longitude: -73.98,
      latitude: 40.745,
      zoom: 11.5,
      pitch: 48,
      bearing: -20,
    },
    controller: true,
    getTooltip: ({ object }) =>
      object
        ? `${object.properties.name}\nSimulated value: ${object.properties.value}`
        : null,
    onError: (error) =>
      window.labFailure(`WebGL renderer error: ${error.message}`),
    layers: [],
  });
  const basemap = new deck.TileLayer({
    id: "osm-basemap",
    data: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    minZoom: 0,
    maxZoom: 19,
    tileSize: 256,
    onTileError: () => {
      document.querySelector("#renderer-note").textContent =
        "Basemap tiles could not load; synthetic columns and export still work.";
    },
    renderSubLayers: (props) => {
      const { west, south, east, north } = props.tile.bbox;
      return new deck.BitmapLayer(props, {
        data: null,
        image: props.data,
        bounds: [west, south, east, north],
      });
    },
  });
  return (collection) =>
    display.setProps({
      layers: [
        basemap,
        new deck.ColumnLayer({
          id: "synthetic-columns",
          data: collection.features,
          diskResolution: 12,
          radius: 140,
          extruded: true,
          pickable: true,
          elevationScale: 12,
          getPosition: (f) => f.geometry.coordinates,
          getElevation: (f) => f.properties.value,
          getFillColor: [8, 145, 140, 220],
          getLineColor: [16, 46, 60],
          lineWidthMinPixels: 1,
        }),
        new deck.ScatterplotLayer({
          id: "column-base",
          data: collection.features,
          getPosition: (f) => f.geometry.coordinates,
          getRadius: 150,
          getFillColor: [233, 186, 92],
          opacity: 0.6,
        }),
      ],
    });
}

async function sceneRenderer() {
  const THREE = await import(
    "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js"
  );
  const { OrbitControls } = await import(
    "https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/controls/OrbitControls.js"
  );
  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#e5efed");
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 1000);
  camera.position.set(30, 34, 42);
  const display = new THREE.WebGLRenderer({ antialias: true });
  display.setPixelRatio(Math.min(devicePixelRatio, 2));
  display.domElement.tabIndex = 0;
  display.domElement.setAttribute(
    "aria-label",
    "3D scene. Arrow keys pan; Shift and arrows rotate; plus and minus zoom.",
  );
  viewport.prepend(display.domElement);
  const controls = new OrbitControls(camera, display.domElement);
  controls.target.set(0, 2, 0);
  controls.enableDamping = true;
  controls.minDistance = 5;
  controls.maxDistance = 160;
  controls.listenToKeyEvents(display.domElement);
  display.domElement.addEventListener("keydown", (event) => {
    if (!["+", "=", "-", "_"].includes(event.key) || interrupted) return;
    event.preventDefault();
    const offset = camera.position.clone().sub(controls.target);
    const factor = ["+", "="].includes(event.key) ? 0.9 : 1.1;
    const distance = Math.max(
      controls.minDistance,
      Math.min(controls.maxDistance, offset.length() * factor),
    );
    camera.position.copy(controls.target).add(offset.setLength(distance));
    controls.update();
  });
  display.domElement.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    interrupted = true;
    controls.enabled = false;
    status.dataset.state = "interrupted";
    status.textContent =
      "Graphics were interrupted. Waiting for WebGL to restore; your selection is retained. Reload if it does not recover.";
    document.querySelector("#download").disabled = true;
    document.querySelector("#hour").disabled = true;
  });
  display.domElement.addEventListener("webglcontextrestored", () => {
    if (failed) return;
    interrupted = false;
    controls.enabled = true;
    if (current) window.renderSelection(current);
    else {
      status.dataset.state = "loading";
      status.textContent =
        "Graphics restored. Waiting for Python to finish loading…";
    }
  });
  scene.add(new THREE.HemisphereLight(0xffffff, 0x547467, 2.5));
  const sunlight = new THREE.DirectionalLight(0xffffff, 2);
  sunlight.position.set(10, 20, 10);
  scene.add(sunlight);
  scene.add(new THREE.GridHelper(52, 26, 0x8bada0, 0xc6d8d0));
  const bars = new THREE.Group();
  scene.add(bars);
  new ResizeObserver(() => {
    const width = viewport.clientWidth,
      height = viewport.clientHeight;
    display.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }).observe(viewport);
  display.setAnimationLoop(() => {
    controls.update();
    display.render(scene, camera);
  });
  return (collection) => {
    while (bars.children.length) {
      const old = bars.children[0];
      bars.remove(old);
      old.geometry.dispose();
      old.material.dispose();
    }
    for (const f of collection.features) {
      const [lon, lat] = f.geometry.coordinates,
        height = f.properties.value / 8;
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(1, height, 1),
        new THREE.MeshStandardMaterial({ color: "#087e83", roughness: 0.5 }),
      );
      mesh.position.set((lon + 73.98) * 350, height / 2, -(lat - 40.745) * 460);
      bars.add(mesh);
    }
  };
}

window.rendererReady = (async () => {
  if (
    kind !== "leaflet" &&
    !document.createElement("canvas").getContext("webgl2")
  )
    throw new Error(
      "WebGL 2 is unavailable. Try a browser with hardware acceleration, or use the 2D map.",
    );
  renderer = await {
    leaflet: leafletRenderer,
    deck: deckRenderer,
    scene: sceneRenderer,
  }[kind]();
  document.body.dataset.rendererReady = "true";
})();
// Handle renderer failure even if Python has not reached its await yet.
window.rendererReady.catch((error) => window.labFailure(error.message));

function updateObservationTable(collection) {
  const body = document.querySelector("#observations-body");
  body.replaceChildren();
  for (const feature of collection.features) {
    const row = document.createElement("tr");
    const p = feature.properties;
    const values = [
      feature.id,
      p.name,
      p.hour,
      p.value,
      ...feature.geometry.coordinates,
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    body.append(row);
  }
  if (!collection.features.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.textContent = "No observations at this hour.";
    row.append(cell);
    body.append(row);
  }
}

window.renderSelection = (serialized) => {
  if (failed) return;
  const collection = JSON.parse(serialized);
  current = serialized;
  if (interrupted) return;
  renderer(collection);
  updateObservationTable(collection);
  document.querySelector("#count").textContent = collection.features.length;
  document.querySelector("#hour").disabled = false;
  document.querySelector("#download").disabled = false;
  status.dataset.state = "ready";
  status.textContent = collection.features.length
    ? "Ready. Python selection and renderer are in sync."
    : "Ready. No observations at this hour; the layer is empty.";
  viewport.dataset.featureCount = collection.features.length;
  document.body.dataset.runtimeReady = "true";
  clearTimeout(timeout);
};
window.downloadSelection = () => {
  if (!current || failed) return;
  const url = URL.createObjectURL(
    new Blob([current], { type: "application/geo+json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `synthetic-nyc-hour-${document.querySelector("#hour").value}.geojson`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
