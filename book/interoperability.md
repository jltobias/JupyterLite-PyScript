---
title: GeoLibre, RustGIS and JupyterGIS — exchange a real file
---

[Open the guided GIS handoff]({{HUB_BASE}}/integrations/). This lesson uses the applications as external integrations through a real GeoJSON export/import exercise.

## Prepare one known selection

In [the 2D map]({{HUB_BASE}}/apps/leaflet/), wait for ready, choose **08:00** and confirm **6** observations. Download `synthetic-nyc-hour-8.geojson`. The six features should all have `hour: 8`, `simulated: true`, and WGS 84 `[longitude, latitude]` coordinates. Metadata describes the invented dataset and selection.

## GeoLibre

Open [GeoLibre Web](https://web.geolibre.app/) and drag the downloaded GeoJSON onto its map. Zoom to the layer and inspect attributes. Confirm six points near NYC. GeoLibre also documents a `?data=` query parameter for an encoded, publicly reachable GeoJSON URL. That is useful after Pages deployment; it is a URL handoff, not arbitrary remote control of the public app.

Source: [GeoLibre embedding and data URL documentation](https://geolibre.app/user-guide/embedding/).

## RustGIS

Open [RustGIS Web](https://web.rustgis.app/), choose **Home → Add → Add Data**, and select the downloaded GeoJSON. Zoom to its extent and inspect the table. Preserve the `simulated` field when exporting again. The native RustGIS Python package targets CPython. This exercise does not claim its wheels run in Pyodide and does not install a Python bridge into the browser.

Source: [RustGIS data-format and import documentation](https://rustgis.app/user-guide/data/).

## JupyterGIS

Open [the JupyterGIS Lite preview](https://jupytergis.readthedocs.io/en/latest/lite/lab/index.html). Upload the GeoJSON through the file browser. In the same directory, use the launcher's **Other → GIS File** to create a `.jGIS` document. Use the layer panel's **+ → Add Vector Layer → GeoJSON**, set **Path** to the uploaded filename, and confirm **Ok**. Right-click the layer and select **Zoom to Layer**. Check the same six points and fields.

This is a separate JupyterLite deployment, with its own storage and runtime. Its browser preview does not provide real-time collaboration, QGIS project conversion, server raster tiling or functioning STAC search. Do not assume server-backed JupyterGIS capabilities are available in Lite.

Sources: [JupyterGIS introduction](https://jupytergis.readthedocs.io/en/latest/user_guide/tutorials/01-intro/index.html), [upstream GeoJSON import UI test](https://github.com/geojupyter/jupytergis/blob/main/ui-tests/tests/geojson-layers.spec.ts), [JupyterGIS documentation and Lite preview](https://jupytergis.readthedocs.io/en/latest/).

## Verify and repeat

Every destination should display six points with hour 8, plausible NYC coordinates near −74/40.7, and simulated labels. A different count or implausible location is a reason to inspect the selected file and coordinate order. At 00:00 the valid download has no features; some GIS applications will not add an empty layer.

The stable interoperability contract is the file. Each app may evolve its menus, and each application owns its own memory, storage and installed packages. Download your work to keep it.
