"""PyScript owns data, filtering and export; JavaScript owns graphics."""
import json
from pathlib import Path
from pyscript import document, window
from pyodide.ffi import create_proxy
from selection import export_geojson

proxies = []  # Retain callbacks for the life of the page.


def update(event=None):
    try:
        serialized = export_geojson(dataset, str(document.getElementById("hour").value))
        window.renderSelection(serialized)
    except Exception as error:
        window.labFailure(f"Could not update the selection: {error}")


def download(event):
    window.downloadSelection()


try:
    dataset = json.loads(Path("observations.geojson").read_text())
    # Renderer downloads may finish after Python; await a JS promise explicitly.
    await window.rendererReady
    for element_id, event_name, callback in [
        ("hour", "change", update), ("download", "click", download)
    ]:
        proxy = create_proxy(callback)
        proxies.append(proxy)
        document.getElementById(element_id).addEventListener(event_name, proxy)
    update()
except Exception as error:
    window.labFailure(f"Python or renderer startup failed: {error}")
