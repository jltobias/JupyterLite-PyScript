---
title: A little Python. A new view of the world.
---

Welcome to **JupyterLite × PyScript**, a browser geospatial learning hub by **James L. Tobias, MS, GISP**. Start with a few Python cells, then connect one tiny dataset to maps, a 3D scene and other GIS tools.

Everything learners run here lives in the browser. No account, access token, local Python installation or Python backend is required. The first visit downloads runtimes, JavaScript libraries and map assets, so allow a minute and keep an internet connection available.

[Return to the hub]({{HUB_BASE}}/) · [Open JupyterLite]({{HUB_BASE}}/lite/lab/index.html?path=01-welcome.ipynb)

## Your learning path

1. **Run a notebook.** Open `01-welcome.ipynb` in JupyterLite. Run cells from top to bottom, change a value and rerun. Read [the runtime explanation](runtimes.md).
2. **Understand the data.** Open `02-explore-data.ipynb`. Inspect 24 synthetic observations and count them by hour. Read [the data lesson](data.md).
3. **Compare views.** Try the [2D map]({{HUB_BASE}}/apps/leaflet/), [3D map]({{HUB_BASE}}/apps/deck/) and [3D scene]({{HUB_BASE}}/apps/scene/). Select 08:00, then 00:00. Read [maps and scenes](maps-and-scenes.md).
4. **Read and change code.** Use `03-author-an-app.ipynb` and [the authoring lesson](authoring.md) to trace Python → GeoJSON → JavaScript.
5. **Exchange data.** Download a selection and follow [the GIS handoff]({{HUB_BASE}}/integrations/) into GeoLibre, RustGIS or JupyterGIS.

## What you will make

A small interaction with a clear contract: choose an hour, let Python filter, render exactly those features, and export the same geographic data. A zero-feature selection is valid and should clear the layer.

The sample is invented for teaching. It is neither measured taxi data nor health data. The separate [NYC Taxi study](nyc-taxi.md) introduces the Panel/deck.gl inspiration with attribution and explains how its subject differs from this sample.

## Keep your work

Browser storage is useful but temporary. Download important notebooks and GeoJSON files before clearing browser data or changing computers. Each application has its own files and runtime; moving a file is an explicit step.
