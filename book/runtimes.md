---
title: Two browser environments, distinct runtimes
---

JupyterLite is a notebook environment delivered as static assets. This repository includes a **Pyodide kernel** for its Python notebooks. PyScript is a way to author separate web applications that run Python; these labs also use Pyodide, managed by PyScript. Opening a map does not open a notebook kernel.

| Activity | Python runs in | UI owned by | Files |
| --- | --- | --- | --- |
| JupyterLite notebook | JupyterLite's Pyodide kernel | JupyterLab interface and notebook cells | Notebook browser storage and bundled content |
| PyScript app | Its page's Pyodide interpreter | HTML, controls and JavaScript renderer | That page's virtual filesystem and downloads |
| External GIS | Whatever that tool supports | The external tool | Explicitly imported or exported files |

The environments do **not** share Python variables, memory, installed packages or a live filesystem. PyScript is not installed as a JupyterLite kernel. Reusing `selection.py` means loading a copy of the same source into each runtime.

## A concrete boundary

1. A PyScript lab loads `observations.geojson` into its own virtual filesystem.
2. Python selects features and serializes a GeoJSON FeatureCollection.
3. JavaScript parses that string and updates Leaflet, deck.gl or Three.js.
4. A download places a file on your computer. Uploading that file into JupyterLite or another GIS is a separate action.

Both the notebook and app can calculate `6`, but their variables are unrelated. Their agreement comes from shared inputs and code, not shared memory.

## Packages and startup

WebAssembly Python has a different package boundary from native CPython. Pure Python packages and packages built for the pinned Pyodide release may work; native wheels built for a desktop OS cannot simply be assumed to work. These lessons use only the Python standard library and small JavaScript adapters. They make no RustGIS-wheel or GIS bridge compatibility claim.

The app pins PyScript **2026.7.3** and Pyodide **0.29.0**. JupyterLite's separately bundled Pyodide kernel manages its own runtime. They can have different versions.

If a lab stays on “Loading,” wait for its visible timeout or error. Check internet/CDN access and reload. The 3D views require WebGL 2 and hardware/browser support; [the 2D map]({{HUB_BASE}}/apps/leaflet/) remains an alternative. No Python service is needed after static deployment.

Sources: [JupyterLite documentation](https://jupyterlite.readthedocs.io/en/stable/), [PyScript configuration and interpreter/files options](https://docs.pyscript.net/2026.7.3/user-guide/configuration/), [PyScript DOM and JavaScript](https://docs.pyscript.net/2026.7.3/user-guide/dom/), [Pyodide package loading](https://pyodide.org/en/stable/usage/loading-packages.html).
