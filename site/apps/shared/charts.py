"""Each app prepares its own data; only serialized summaries cross to JS."""
import json
from pathlib import Path
from pyscript import document, window
from pyodide.ffi import create_proxy
from chart_data import chart_config, export_summary

proxies = []


async def update(event=None):
    try:
        config = chart_config(renderer, str(document.getElementById("view").value),
                              str(document.getElementById("hour").value),
                              str(document.getElementById("metric").value))
        group = "point" if config["view"] == "points" else "hour" if renderer == "d3" else "neighborhood"
        await window.renderChart(export_summary(dataset, group, config["hour"], config["metric"]))
    except Exception as error:
        window.chartFailure(f"Could not update chart: {error}")


def download(event):
    window.downloadChart()


try:
    dataset = json.loads(Path("observations.geojson").read_text())
    incoming = json.loads(window.chartQuery())
    renderer = incoming.pop("renderer")
    config = chart_config(renderer, **incoming)
    for name in ("view", "hour", "metric"):
        document.getElementById(name).value = str(config[name])
    await window.chartRendererReady
    for element_id, event_name, callback in [
        ("view", "change", update), ("hour", "change", update),
        ("metric", "change", update), ("download", "click", download)
    ]:
        proxy = create_proxy(callback)
        proxies.append(proxy)
        document.getElementById(element_id).addEventListener(event_name, proxy)
    await update()
except Exception as error:
    window.chartFailure(f"Python or chart startup failed: {error}")
