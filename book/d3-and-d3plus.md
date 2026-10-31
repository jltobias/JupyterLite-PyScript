---
title: Python rows, D3 and D3plus graphics
---

Prepare the same synthetic NYC sample in Python, then give the rows to a JavaScript renderer. These four lessons run Python cells and show an interactive PyScript application **inside the notebook**. Each also offers a standalone launch and actual source files to explore.

| Lesson | Python preparation | Interactive view |
| --- | --- | --- |
| [04 · D3 hourly bars]({{HUB_BASE}}/lite/lab/index.html?path=04-d3-hourly-bars.ipynb) | Group by hour; sum invented values or count observations | [D3 bars]({{HUB_BASE}}/apps/d3/?view=bars&hour=all&metric=total) |
| [05 · D3 projected NYC points]({{HUB_BASE}}/lite/lab/index.html?path=05-d3-projected-points.ipynb) | Keep each selected observation and its original coordinates | [D3 points]({{HUB_BASE}}/apps/d3/?view=points&hour=all&metric=total) |
| [06 · D3plus neighborhood bars]({{HUB_BASE}}/lite/lab/index.html?path=06-d3plus-neighborhood-bars.ipynb) | Group by neighborhood; sum or count | [D3plus bars]({{HUB_BASE}}/apps/d3plus/?view=bars&hour=all&metric=total) |
| [07 · D3plus neighborhood treemap]({{HUB_BASE}}/lite/lab/index.html?path=07-d3plus-neighborhood-treemap.ipynb) | Reuse exactly the same neighborhood summary | [D3plus treemap]({{HUB_BASE}}/apps/d3plus/?view=treemap&hour=all&metric=total) |

## Run, compare, explain

Run a notebook from top to bottom using **Run → Run All Cells**. First inspect provenance, then set `hour` and `metric`, prepare summary rows and run the iframe cell. Start with all hours: hourly bars have four groups; neighborhood views have six groups; the point view has 24 marks. These are synthetic locations without a basemap.

Choose hour 8 for six observations. `count` adds observation counts; `total` adds invented values. The chart, accessible table and downloaded JSON receive the same serialized Python summary. Select hour 0 to clear every data mark and export an empty `rows` list. Invalid view, hour and metric selectors produce a visible error. Hours 0–23 are valid even when the sample has no observations at that hour.

Python owns filtering and aggregation in `chart_data.py`, which reuses the existing strict hour selection. Rows contain count, total, plotted value and longitude/latitude centroids; provenance stays in the summary metadata. JavaScript D3/D3plus owns layout, axes and graphics. The D3 point projection changes display positions without changing source coordinates. Arithmetic centroids describe these nearby synthetic observations, not neighborhood boundaries.

The point-size legend identifies the active metric and its scale. Circle sizes rescale to the selected observations; use the table's numeric values when comparing different hour selections.

## Two interpreters, an explicit URL

The notebook kernel and the PyScript app in its iframe are separate Python interpreters. Each loads its own copy of the dataset and shared module. Editing a notebook variable or its dataset does not modify the app's memory or files. Controls inside the app likewise do not change the notebook's `summary` variable.

The notebook passes its selected configuration through the iframe URL:

```python
hub = json.loads(Path('hub-config.json').read_text())
query = urlencode({'view': view, 'hour': config['hour'], 'metric': config['metric']})
app_url = f"{hub['base_url']}/apps/{renderer}/?{query}"
display(IFrame(src=app_url, width='100%', height=960,
              extras=['title="Interactive PyScript chart"']))
```

The build writes `hub-config.json` with the actual site prefix, so the root-relative URL works at `/` and `/JupyterLite-PyScript`. Markdown links use the existing build substitution. To pass edited data between runtimes, design an explicit file or message exchange; the teaching examples share source and configuration, not memory.

## Follow the actual implementation

Read [Python preparation]({{HUB_BASE}}/apps/shared/chart_data.py), [PyScript callbacks]({{HUB_BASE}}/apps/shared/charts.py), [renderer adapters]({{HUB_BASE}}/apps/shared/charts.js) and [runtime configuration]({{HUB_BASE}}/apps/shared/charts.json). The build also packages them into JupyterLite's `source/` and `source/apps/` directories. Editing those notebook copies does not publish changes; edit repository source and rebuild to change the hosted apps.

D3 7.9.0 uses scales and keyed [data joins](https://d3js.org/d3-selection/joining). D3plus core 4.10.0 uses `BarChart` with `groupBy: 'id', x: 'id', y: 'value'`, and `Treemap` with `groupBy: 'id', sum: 'value'`. Its current treemap API uses `sum`. The built-in zoom and save controls are disabled so filtering and JSON export stay aligned with the Python summary. Required library/runtime failures appear visibly and disable export while keeping navigation available.

## Sources and credits

- **D3 7.9.0:** [official project](https://d3js.org/), [source](https://github.com/d3/d3), and [ISC license, © 2010–2023 Mike Bostock](https://github.com/d3/d3/blob/v7.9.0/LICENSE). The current project site credits Mike Bostock and Observable.
- **D3 paper:** Bostock, M., Ogievetsky, V., & Heer, J. (2011). *D³: Data-Driven Documents*. IEEE Transactions on Visualization and Computer Graphics, 17(12), 2301–2309. [doi:10.1109/TVCG.2011.185](https://doi.org/10.1109/TVCG.2011.185); [author-hosted record](https://idl.uw.edu/papers/d3).
- **D3plus core 4.10.0:** [official project](https://d3plus.org/), [source and quick start](https://github.com/d3plus/d3plus/blob/main/README.md), [current core API](https://github.com/d3plus/d3plus/blob/main/packages/core/API.md), and [MIT license, © 2026 D3plus](https://github.com/d3plus/d3plus/blob/main/LICENSE). The apps pin the npm-published `@d3plus/core@4.10.0/umd/d3plus-core.full.min.js` bundle delivered by jsDelivr.

The sample remains the hub's 24 deterministic synthetic observations with its original provenance. No external basemap or geography is loaded by these chart views. Existing [data](data.md), [maps and scenes](maps-and-scenes.md), and [NYC Taxi source discussion](nyc-taxi.md) keep their own attributions.
