---
title: Author a small PyScript application
---

[Open the source lesson]({{HUB_BASE}}/lite/lab/index.html?path=03-author-an-app.ipynb). It includes actual app source, exercises the same Python module and offers working launch links.

## The files and their jobs

- `site/apps/leaflet/index.html`, `deck/index.html` and `scene/index.html` provide semantic navigation, controls, loading/error text and a renderer container.
- `site/apps/shared/pyscript.json` pins the interpreter and fetches the Python module and dataset into the page's virtual filesystem.
- `site/apps/shared/lab.py` loads data, attaches event callbacks and calls the JavaScript bridge after the renderer promise resolves.
- `content/selection.py` filters data and serializes export. The build copies it into the app and JupyterLite.
- `site/apps/shared/lab.js` starts the selected renderer, updates graphics and creates a download from the exact serialized collection it just rendered.

The core page declaration is real source:

```html
<script type="module" src="https://pyscript.net/releases/2026.7.3/core.js"></script>
<script type="py" src="../shared/lab.py" config="../shared/pyscript.json"></script>
```

## Trace an interaction

```python
serialized = export_geojson(dataset, str(document.getElementById("hour").value))
window.renderSelection(serialized)
```

The hour change handler runs in Python. JavaScript parses the GeoJSON, updates the renderer and displayed count, then retains that string for export. This keeps displayed and downloaded observations aligned. Callback proxies stay alive for the page lifetime, and startup failures are caught explicitly.

## Make a local change

In the notebook, change the selected hour and inspect the export. To change a deployed app, edit repository source, rebuild and preview it with the deployment instructions. Editing a source copy inside JupyterLite does not modify the hosted page; the browser filesystem belongs to that notebook environment.

Try coloring columns by hour in `lab.js`, changing the scene scale factors, or adding a Python attribute summary. Keep provenance labels and the empty-selection behavior. Adding a Python package requires checking support for the specific browser runtime; desktop wheel availability is not sufficient evidence.

Sources: [PyScript events](https://docs.pyscript.net/2026.7.3/user-guide/events/), [PyScript files/configuration](https://docs.pyscript.net/2026.7.3/user-guide/configuration/).
