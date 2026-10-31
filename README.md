# JupyterLite × PyScript

**Browser Geospatial Lab · James L. Tobias, MS, GISP**

Explore Python in your browser, from your first JupyterLite notebook to PyScript maps and 3D scenes. A companion **Jupyter Book 2** connects the lessons, and one small synthetic NYC dataset travels through every activity.

![An original illustration connects a Python notebook, a geographic map and a three-dimensional city through GeoJSON.](site/assets/splash.svg)

No learner account, access token, local Python installation or Python backend is required. First loads need internet access for browser runtimes, graphics libraries and map tiles. **Public links below become available after the GitHub Pages workflow is deployed.**

| Start here | Launch | What you will do |
| --- | --- | --- |
| Learning hub | [Open the hub](https://jltobias.github.io/JupyterLite-PyScript/) | Choose a lesson or lab |
| Companion book | [Read the book](https://jltobias.github.io/JupyterLite-PyScript/book/) | Follow the learning path and understand the runtimes |
| JupyterLite | [First notebook](https://jltobias.github.io/JupyterLite-PyScript/lite/lab/index.html?path=01-welcome.ipynb) | Run Python cells and inspect the shared sample |
| Data exploration | [Explore the data](https://jltobias.github.io/JupyterLite-PyScript/lite/lab/index.html?path=02-explore-data.ipynb) | Filter, count and export observations |
| Leaflet 2D map | [Open the map](https://jltobias.github.io/JupyterLite-PyScript/apps/leaflet/) | Show selected points over OpenStreetMap |
| deck.gl 3D map | [Open the columns](https://jltobias.github.io/JupyterLite-PyScript/apps/deck/) | Compare simulated magnitudes in geographic space |
| Three.js 3D scene | [Open the scene](https://jltobias.github.io/JupyterLite-PyScript/apps/scene/) | Compare a local teaching scene with a geographic map |
| App authoring | [Read working source](https://jltobias.github.io/JupyterLite-PyScript/lite/lab/index.html?path=03-author-an-app.ipynb) | Trace the Python-to-JavaScript interaction |
| GIS interoperability | [Try the file handoff](https://jltobias.github.io/JupyterLite-PyScript/integrations/) | Import an exported selection into GeoLibre, RustGIS or JupyterGIS |

JupyterLite's notebook kernel and each PyScript app have **separate Python runtimes and virtual filesystems**. They reuse source and data; they do not share memory or installed packages. PyScript is not a JupyterLite kernel. Move files explicitly with download and upload/import.

## Run locally

Build tools require **Python 3.11+** and **Node.js 22+ with npm on PATH**. Network access is needed to install dependencies and obtain JupyterLite/MyST assets. Use an isolated Python environment:

```sh
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` in bash. Then:

```sh
python -m pip install -r requirements.txt
python scripts/build.py
python scripts/check_site.py
python scripts/preview.py
```

Open **http://127.0.0.1:8000/**. The build produces one `_site/` tree containing the landing page, labs, book and JupyterLite. It packages the sample dataset, notebooks and actual app source into JupyterLite. Source lessons can be run without installing extra Python packages.

For the GitHub Pages repository path, build and preview with:

```sh
python scripts/build.py --base-url /JupyterLite-PyScript
python scripts/check_site.py
python scripts/preview.py
```

Open **http://127.0.0.1:8000/JupyterLite-PyScript/**. `preview.py` mounts the build at its recorded prefix. MyST receives the corresponding `/JupyterLite-PyScript/book` base URL; app and landing links are relative.

## Verify the live apps

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m unittest discover -s scripts -p "test_*.py"
python scripts/browser_smoke.py
```

An existing Chrome/Chromium can be selected with `--browser-executable "path/to/chrome"`. The check starts its own local server and exercises the recorded URL prefix. It loads actual browser Python and all three renderers, selects six points at 08:00, checks filtered and zero-feature downloads, verifies mobile layouts and book/Lab routes, and tests blocked-CDN and unavailable-WebGL messages. Screenshots are written under `tmp/browser/`.

`check_site.py` validates generated launch routes and local links, notebook schemas and packaged sources, deterministic data, and shared Python filtering/export including empty results. These artifact checks complement live browser checks; they do not replace them.

## Publish with GitHub Pages

[The workflow](.github/workflows/pages.yml) installs the pinned build tools, builds the combined tree, runs artifact and browser checks, and uploads one Pages artifact. Pushes to `main` deploy through Actions; pull requests build and check without deploying.

A repository maintainer selects **Settings → Pages → Source: GitHub Actions** once, then commits and pushes the source to `main`. The workflow derives the base path from the repository name. Adjust that path if using a custom domain or a user-site repository.

## Source map

| Location | Purpose |
| --- | --- |
| [site/](site/) | Responsive landing page, original SVG splash and PyScript app routes |
| [site/apps/shared/](site/apps/shared/) | Python callbacks, pinned runtime config and JavaScript renderer adapters |
| [content/selection.py](content/selection.py) | Shared standard-library filtering and GeoJSON serialization |
| [content/](content/) | Three notebooks and the shared teaching dataset |
| [book/](book/) | Jupyter Book 2 / MyST chapters and navigation |
| [scripts/](scripts/) | Assembly, preview, deterministic source generators and verification |
| [.github/workflows/pages.yml](.github/workflows/pages.yml) | Combined build/check/deploy pipeline |

Regenerate source artifacts with `python scripts/generate_data.py` and `python scripts/create_notebooks.py` when their generators change. Avoid editing `_site/`: it is generated.

## Data, inspiration and boundaries

The sample has **24 deterministic synthetic NYC observations**, generated by [scripts/generate_data.py](scripts/generate_data.py). Neighborhood coordinates are approximate; hours, offsets and values are invented. These are **not measured taxi trips, health records or observations of people**. Dataset metadata and every feature carry synthetic labels. GeoJSON uses WGS 84 / EPSG:4326, in longitude/latitude order, and export retains provenance and selection count.

Explore the independently maintained [NYC Taxi Panel/deck.gl example hosted under @ambv](https://pyscript.com/@ambv/nyc-taxi-panel-deckgl-copy/latest?files=README.md). For related inspectable source, see [HoloViz Panel's NYC deck.gl gallery](https://panel.holoviz.org/gallery/nyc_deckgl.html), by HoloViz/Panel and contributors. Their work is external inspiration; our synthetic sample is separate. Respect upstream licensing and attribution when reusing code or data.

The integration lesson exchanges GeoJSON through [GeoLibre Web](https://web.geolibre.app/), [RustGIS Web](https://web.rustgis.app/) and [JupyterGIS Lite](https://jupytergis.readthedocs.io/en/latest/lite/lab/index.html). RustGIS Python targets native CPython; JupyterGIS Lite has preview limitations, including no real-time collaboration, QGIS project conversion, server raster tiling or functioning STAC search. See [GeoLibre URL handoff docs](https://geolibre.app/user-guide/embedding/), [RustGIS import formats](https://rustgis.app/user-guide/data/) and [JupyterGIS documentation](https://jupytergis.readthedocs.io/en/latest/).

The apps pin [PyScript 2026.7.3](https://docs.pyscript.net/2026.7.3/user-guide/configuration/) with Pyodide 0.29.0, Leaflet 1.9.4, deck.gl 9.1.14 and Three.js 0.180.0. The separately built JupyterLite kernel manages its own Pyodide runtime. Build packages are pinned in [requirements.txt](requirements.txt); the book uses [MyST static export](https://mystmd.org/guide/deployment). Maps use © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). The splash illustration is original SVG artwork.

Browser storage can be cleared; download important work. The 3D labs need WebGL 2. If graphics assets or runtimes are blocked, visible messages explain the failure and navigation remains usable.
