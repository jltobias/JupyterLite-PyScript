"""Recreate small, dependency-light teaching notebooks (no saved outputs)."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def md(text):
    # JupyterLab treats relative Markdown URLs as notebook content files.
    # The build expands this marker to a root-relative hub URL before packaging.
    text = text.replace("../../", "{{HUB_BASE}}/")
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": text.splitlines(keepends=True)}


def save(name, cells):
    for index, cell in enumerate(cells):
        cell["id"] = f"lesson-{index:02d}"
    notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"display_name": "Python (Pyodide)", "language": "python", "name": "python"},
        "language_info": {"name": "python", "version": "3.13"}}, "cells": cells}
    (ROOT / "content" / name).write_text(json.dumps(notebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def chart_lesson(name, title, renderer, view, grouping, explanation, exercise):
    """An executable Python preparation lesson with a separate live iframe."""
    iframe_attributes = [f'title="{escape(f"Interactive {title}", quote=True)}"']
    save(name, [
        md(f"# {title}\n\n{explanation}\n\nRun every cell top to bottom. Python uses only the standard library for preparation; `IPython.display.IFrame` embeds the live PyScript app. The notebook kernel and iframe each run their **own Python interpreter** and load their own dataset/module. URL parameters configure the app; changing notebook variables or data is **not shared memory**."),
        md("## 1. Inspect the shared data and provenance\n\nThese 24 synthetic NYC observations have invented hours, values and location offsets. They are not measured taxi trips, health records or observations of people."),
        code("import json\nfrom pathlib import Path\nfrom urllib.parse import urlencode\nfrom IPython.display import IFrame, display\nfrom chart_data import chart_config, chart_summary, export_summary\n\ndataset = json.loads(Path('data/nyc-observations.geojson').read_text())\nprint(dataset['metadata']['provenance'])\nprint('Synthetic observations:', len(dataset['features']))\nassert dataset['metadata']['simulated'] is True"),
        md("## 2. Set parameters and prepare real Python rows\n\nUse `hour = 'all'` for all 24 observations, `8` for six observations, or `0` for a valid empty selection. Choose `metric = 'total'` for the additive invented value, or `'count'` for the number of observations. Re-run from this cell after changing parameters."),
        code(f"hour = 'all'\nmetric = 'total'\nrenderer = {renderer!r}\nview = {view!r}\ngroup_by = {grouping!r}\nconfig = chart_config(renderer, view, hour, metric)\nsummary = chart_summary(dataset, group_by, config['hour'], config['metric'])\nprint('Selected observations:', summary['metadata']['feature_count'])\nprint('Summary groups:', len(summary['rows']))\nfor row in summary['rows']:\n    print(row['id'], row['label'], 'count =', row['count'], 'total =', row['total'], 'plotted =', row['value'])"),
        md("## 3. Verify the summary and empty selection\n\nCounts and totals are additive. Neighborhood coordinates are arithmetic centroids of the selected synthetic points; individual point rows retain their original coordinates. The export retains dataset provenance."),
        code("assert sum(row['count'] for row in summary['rows']) == summary['metadata']['feature_count']\nassert all(row['value'] == row[metric] for row in summary['rows'])\nassert json.loads(export_summary(dataset, group_by, hour, metric)) == summary\nempty = chart_summary(dataset, group_by, 0, metric)\nassert empty['rows'] == []\nassert empty['metadata']['feature_count'] == 0\nprint('Python preparation and empty-selection checks passed.')"),
        md(f"## 4. Run the interactive PyScript app here\n\nThe build writes `hub-config.json` with the actual deployment prefix. This produces a root-relative iframe URL that bypasses JupyterLab's notebook-file resolver and works at a site root or repository path. The app loads its own copy of `chart_data.py` and the dataset. Controls inside the iframe update that app; they do not change `summary` above.\n\n[Launch this view standalone](../../apps/{renderer}/?view={view}&hour=all&metric=total) · [Chart chapter](../../book/d3-and-d3plus/)."),
        code("hub = json.loads(Path('hub-config.json').read_text())\nquery = urlencode({'view': view, 'hour': config['hour'], 'metric': config['metric']})\napp_url = f\"{hub['base_url']}/apps/{renderer}/?{query}\"\nprint('Embedded app:', app_url)\n"
             + f"display(IFrame(src=app_url, width='100%', height=960, extras={iframe_attributes!r}))"),
        md("## 5. Explore the deployed source\n\nThe build packages the actual app and shared sources below. JavaScript draws the serialized Python rows; it does not perform filtering or aggregation. Changing these notebook copies does not change the deployed app."),
        code("print(Path('chart_data.py').read_text())"),
        code(f"print(Path('source/charts.py').read_text())\nprint(Path('source/apps/{renderer}/index.html').read_text())"),
        md(f"Read [the actual renderer](../../apps/shared/charts.js) and [runtime file mapping](../../apps/shared/charts.json). In JupyterLite, open `source/charts.js` to inspect the complete drawing code.\n\n## Exercises\n\n{exercise}\n\n1. Set `hour = 8` and predict the group count before rerunning. Compare the table and downloaded JSON inside the iframe with `summary`.\n2. Change `metric` to `'count'`, rerun the parameter and iframe cells, then compare the mark sizes.\n3. Set `hour = 0` and verify every data mark disappears, the table explains the empty selection and exported `rows` is empty.\n4. Change a value in the notebook's `dataset` and rerun only its summary: explain why the embedded app keeps its own data. Restore the dataset by rerunning cell 1.\n\nDownload important work from the JupyterLite file browser before clearing browser storage."),
    ])


if __name__ == "__main__":
    save("01-welcome.ipynb", [
        md("# Welcome to browser geospatial Python\n\n**James L. Tobias, MS, GISP · JupyterLite × PyScript**\n\nRun each cell with **Shift+Enter**, or choose **Run → Run All Cells**. The Python (Pyodide) kernel downloads on first use; wait until it is idle. No account or Python backend is required.\n\nJupyterLite is this notebook environment. The PyScript labs are separate pages with independent Python runtimes and files. They exchange files explicitly; they do not share notebook variables."),
        code("message = 'Hello from browser Python!'\nprint(message)\nprint('Try changing this message and running the cell again.')"),
        md("## A tiny geographic dataset\n\nThe build bundles `data/nyc-observations.geojson` beside these notebooks. It contains **24 synthetic** observations in NYC with invented hour and value fields. They are not measured taxi trips or health records."),
        code("import json\nfrom pathlib import Path\n\ndataset = json.loads(Path('data/nyc-observations.geojson').read_text())\nprint(dataset['metadata']['provenance'])\nprint('Observations:', len(dataset['features']))\nfirst = dataset['features'][0]\nfirst"),
        md("GeoJSON coordinate order is **longitude, latitude**. At NYC that is approximately −74, 40.7. The data follows WGS 84 / EPSG:4326. The scene lab changes display coordinates but exports these original coordinates."),
        code("lon, lat = first['geometry']['coordinates']\nprint(f\"{first['properties']['name']}: longitude {lon}, latitude {lat}\")\nassert first['properties']['simulated'] is True"),
        md("## Select with shared Python\n\nThis is the same module copied into the PyScript pages. Each runtime loads its own copy; shared source does not imply shared memory."),
        code("from selection import feature_collection\nselected = feature_collection(dataset, 8)\nprint('08:00 observations:', len(selected['features']))\nassert len(selected['features']) == 6"),
        md("## Next steps\n\nOpen `02-explore-data.ipynb` in the file browser. Then try the [2D PyScript map](../../apps/leaflet/), [3D map](../../apps/deck/), [3D scene](../../apps/scene/) and [companion book](../../book/). Hosted launch links work after the combined site is built/deployed.\n\nDownload important notebooks from the file browser before clearing browser storage. Each application owns its own temporary files."),
    ])
    save("02-explore-data.ipynb", [
        md("# One dataset, several views\n\nInspect the complete sample before mapping it. All 24 observations were generated by `scripts/generate_data.py`; approximate neighborhood locations give context while hour, offsets and values are invented.\n\nRun top to bottom. Only standard-library Python is needed."),
        code("import json\nfrom pathlib import Path\nfrom collections import Counter\nfrom selection import select_features, feature_collection, export_geojson\n\ndataset = json.loads(Path('data/nyc-observations.geojson').read_text())\nprint(json.dumps(dataset['metadata'], indent=2))"),
        code("counts = Counter(f['properties']['hour'] for f in dataset['features'])\nfor hour, count in sorted(counts.items()):\n    print(f'{hour:02d}:00  {count} observations')\nassert counts == {8: 6, 12: 6, 18: 6, 21: 6}"),
        md("## Choose an hour\n\nChange `hour` to 8, 12, 18 or 21. Use `'all'` for the entire sample and `0` for a valid empty selection. The shared function returns copies, preserving the input data."),
        code("hour = 8\nselected = feature_collection(dataset, hour)\nprint('Selected:', selected['metadata']['feature_count'])\nfor feature in selected['features']:\n    p = feature['properties']\n    print(feature['id'], p['name'], p['value'], feature['geometry']['coordinates'])"),
        md("## Verify the empty case\n\nZero observations should clear an app's observation layer. Map tiles or the scene grid can remain."),
        code("empty = feature_collection(dataset, 0)\nassert empty['type'] == 'FeatureCollection'\nassert empty['features'] == []\nassert empty['metadata']['feature_count'] == 0\nprint(export_geojson(dataset, 0))"),
        md("## Write an actual handoff file\n\nThe file below is created inside JupyterLite's virtual filesystem. To move it out, find it in the file browser, right-click and **Download**. Then upload/import it into another app. It does not automatically appear in a PyScript lab or another JupyterLite deployment."),
        code("path = Path(f'synthetic-nyc-hour-{hour}.geojson')\npath.write_text(export_geojson(dataset, hour))\nround_trip = json.loads(path.read_text())\nassert len(round_trip['features']) == len(selected['features'])\nassert all(f['properties']['simulated'] for f in round_trip['features'])\nprint('Created:', path, '— download it from the file browser.')"),
        md("## Compare with the maps\n\nSet the same hour in the [2D map](../../apps/leaflet/), [3D columns](../../apps/deck/) and [3D scene](../../apps/scene/). Compare the displayed count and downloaded feature IDs with this notebook.\n\nContinue to the [GeoLibre / RustGIS / JupyterGIS import exercise](../../integrations/). The CRS is EPSG:4326 and coordinate order is longitude, latitude. Metadata is a GeoJSON foreign member; the per-feature `simulated` field carries the label even if a tool drops collection metadata."),
    ])
    save("03-author-an-app.ipynb", [
        md("# Read a working PyScript app\n\nThe build packages **real deployed source** into `source/` for this lesson. No source string below is a placeholder. Editing this notebook's copy does not change the hosted app: that requires editing the repository, rebuilding and redeploying.\n\nJupyterLite and each PyScript page have independent runtimes. This lesson does not install PyScript as a kernel."),
        code("from pathlib import Path\nprint(Path('source/lab.py').read_text())"),
        md("## Find the boundary\n\nThe Python callback calls `export_geojson`, then hands its serialized string to `window.renderSelection`. That JavaScript function renders and retains the same string for download. Python callback proxies stay alive in `proxies`. The renderer-ready promise prevents an update before graphics startup."),
        code("print(Path('source/pyscript.json').read_text())\nprint('--- Shared Python filter/export ---')\nprint(Path('selection.py').read_text())"),
        md("The config maps HTTP source files to an app's virtual filesystem. Those files are separate from this notebook's filesystem even though their content is the same. The app pins PyScript and Pyodide explicitly; the notebook kernel has its own runtime version."),
        code("import json\nfrom selection import export_geojson\ndataset = json.loads(Path('data/nyc-observations.geojson').read_text())\nfor hour in ('all', 8, 0):\n    exported = json.loads(export_geojson(dataset, hour))\n    print(hour, len(exported['features']), exported['metadata']['selection_hour'])"),
        md("## Inspect the actual HTML and renderer\n\nThe HTML starts PyScript and references a `.py` file and JSON config. `lab.js` contains the three renderer adapters, visible timeout/error handling, and GeoJSON download code."),
        code("print(Path('source/apps/leaflet/index.html').read_text())"),
        code("print(Path('source/lab.js').read_text())"),
        md("## Make a change you can explain\n\n1. Change the selected hour in the previous Python cell and predict its count.\n2. In a local repository checkout, change `getFillColor` in the deck.gl adapter or change the Three.js height factor.\n3. Rebuild and open the app. Confirm the new appearance while the geographic export stays correct.\n4. Test 00:00 again so an empty selection clears observations.\n\nLaunch the [2D app](../../apps/leaflet/), [3D app](../../apps/deck/) or [scene](../../apps/scene/). Read [authoring](../../book/authoring/) and [deployment](../../book/deployment/) in the book.\n\nFor package additions, check the specific Pyodide release's support. A native CPython GIS wheel is not evidence of browser compatibility."),
    ])
    chart_lesson("04-d3-hourly-bars.ipynb", "D3 hourly bars: Python rows to SVG", "d3", "bars", "hour",
        "Start with four occupied hours. Python groups observations by hour; D3 scales, axes and a keyed data join turn each summary row into a bar.",
        "Inspect `d3Chart` in `source/charts.js`. Identify the band scale, linear scale and `.join('rect')`. Explain why grouping remains in Python while bar layout belongs to D3.")
    chart_lesson("05-d3-projected-points.ipynb", "D3 projected NYC points", "d3", "points", "point",
        "Project the original longitude/latitude coordinates with D3's Mercator projection. Each point is one synthetic observation; its radius encodes the selected count or total metric. This is a projected point display **without a basemap**.",
        "Inspect the fixed projection bounds and `geoMercator().fitExtent(...)`. Explain why geographic coordinates remain unchanged in the Python rows while SVG coordinates change when the viewport resizes.")
    chart_lesson("06-d3plus-neighborhood-bars.ipynb", "D3plus neighborhood bars", "d3plus", "bars", "neighborhood",
        "Aggregate the 24 observations into six neighborhoods in Python. D3plus BarChart receives ready-to-draw rows with `groupBy='id'`, `x='id'` and `y='value'`.",
        "Compare the hourly grouping in lesson 04 with the neighborhood grouping here. Predict which grouping has one row at 08:00 and which keeps six rows. Check your prediction using Python.")
    chart_lesson("07-d3plus-neighborhood-treemap.ipynb", "D3plus neighborhood treemap", "d3plus", "treemap", "neighborhood",
        "Use the same neighborhood rows as lesson 06. D3plus Treemap maps each additive `value` to rectangle area using its current `sum='value'` API.",
        "Compare the treemap with lesson 06 using the same hour and metric. Explain why both charts export identical Python rows despite their different layouts. Why would an average require a different interpretation from these additive totals?")
    print("Created seven teaching notebooks")
