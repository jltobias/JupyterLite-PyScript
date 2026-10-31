"""Live runtime, renderer, notebook and failure checks against the built site.

Run after build/check_site; needs Playwright Chromium (or --browser-executable).
The preview mount uses build-info.json, so CI exercises a repository subpath.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import threading
import time

from playwright.sync_api import sync_playwright
from preview import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "content"))
from chart_data import chart_summary

CHART_LESSONS = [
    ("04-d3-hourly-bars.ipynb", "d3", "bars", "hour"),
    ("05-d3-projected-points.ipynb", "d3", "points", "point"),
    ("06-d3plus-neighborhood-bars.ipynb", "d3plus", "bars", "neighborhood"),
    ("07-d3plus-neighborhood-treemap.ipynb", "d3plus", "treemap", "neighborhood"),
]


def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "Horizontal page overflow"


def check_table(page, collection):
    details = page.locator("#observations")
    if not details.evaluate("node => node.open"):
        details.locator("summary").click()
    rows = page.locator("#observations-body tr")
    features = collection["features"]
    if not features:
        assert rows.count() == 1
        assert rows.inner_text() == "No observations at this hour."
        assert rows.locator("td").get_attribute("colspan") == "6"
        return
    assert rows.count() == len(features)
    for index, feature in enumerate(features):
        p = feature["properties"]
        expected = [feature["id"], p["name"], p["hour"], p["value"], *feature["geometry"]["coordinates"]]
        assert rows.nth(index).locator("td").all_text_contents() == list(map(str, expected))


def check_download(page, expected, hour):
    with page.expect_download() as info:
        page.locator("#download").click()
    collection = json.loads(Path(info.value.path()).read_text(encoding="utf-8"))
    assert collection["type"] == "FeatureCollection"
    assert len(collection["features"]) == collection["metadata"]["feature_count"] == expected
    assert collection["metadata"]["selection_hour"] == hour
    assert all(f["properties"]["hour"] == hour and f["properties"]["simulated"] is True for f in collection["features"])
    check_table(page, collection)
    return [f["id"] for f in collection["features"]]


def stable_viewport(page):
    """Capture actual settled pixels, independent of bridge/table metadata."""
    page.mouse.move(0, 0)
    page.wait_for_load_state("networkidle")
    previous, equal_frames = None, 0
    for _ in range(40):
        page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
        image = page.locator("#viewport").screenshot()
        equal_frames = equal_frames + 1 if image == previous else 0
        if equal_frames >= 2:
            return image
        previous = image
        page.wait_for_timeout(100)
    raise AssertionError("Viewport pixels did not settle")


def check_scene_recovery_and_keyboard(page):
    before = stable_viewport(page)
    available = page.locator("#viewport canvas").evaluate("""canvas => {
        window.testLostContext = canvas.getContext('webgl2').getExtension('WEBGL_lose_context');
        if (!window.testLostContext) return false;
        window.testLostContext.loseContext();
        return true;
    }""")
    assert available, "Test browser lacks WEBGL_lose_context"
    page.wait_for_function("document.querySelector('#status').dataset.state === 'interrupted'")
    assert page.locator("#download").is_disabled()
    assert "selection is retained" in page.locator("#status").inner_text()
    page.evaluate("window.testLostContext.restoreContext()")
    page.wait_for_function("document.querySelector('#status').dataset.state === 'ready'", timeout=30000)
    assert not page.locator("#download").is_disabled()
    assert stable_viewport(page) == before, "Scene geometry did not recover after context restoration"
    canvas = page.locator("#viewport canvas")
    assert canvas.get_attribute("tabindex") == "0"
    canvas.focus()
    previous = stable_viewport(page)
    for key in ["ArrowRight", "Shift+ArrowRight", "Shift+Equal"]:
        canvas.press(key)
        image = stable_viewport(page)
        assert image != previous, f"Scene keyboard control had no visual effect: {key}"
        previous = image


def check_app(page, origin, route, diagnostics):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(f"{origin}/apps/{route}/", wait_until="domcontentloaded")
    page.wait_for_function("document.body.dataset.runtimeReady === 'true' || document.querySelector('#status').dataset.state === 'error'", timeout=150000)
    assert page.locator("#status").get_attribute("data-state") == "ready", page.locator("#status").inner_text()
    assert page.locator("#count").inner_text() == "24"
    assert not page.locator("#observations").evaluate("node => node.open"), "Observation details should start collapsed"
    if route == "leaflet":
        assert page.locator(".leaflet-interactive").count() == 24
    else:
        assert page.locator("#viewport canvas").count() > 0
    page.locator("#hour").select_option("8")
    page.wait_for_function("document.querySelector('#count').textContent === '6'")
    ids = check_download(page, 6, 8)
    if route == "scene":
        check_scene_recovery_and_keyboard(page)
    selected_image = stable_viewport(page) if route != "leaflet" else None
    page.screenshot(path=str(diagnostics / f"{route}-desktop.png"), full_page=True)
    page.locator("#hour").select_option("0")
    page.wait_for_function("document.querySelector('#count').textContent === '0'")
    check_download(page, 0, 0)
    if route == "leaflet":
        assert page.locator(".leaflet-interactive").count() == 0
    else:
        empty_image = stable_viewport(page)
        assert selected_image != empty_image, f"{route}: six-feature and empty GPU output are identical"
    page.set_viewport_size({"width": 390, "height": 844})
    no_overflow(page)
    assert page.locator(".table-scroll").evaluate("node => node.scrollWidth > node.clientWidth && getComputedStyle(node).overflowX === 'auto'")
    page.screenshot(path=str(diagnostics / f"{route}-mobile.png"), full_page=True)
    return ids


def chart_marks(renderer, view):
    if renderer == "d3":
        return "#viewport circle.observation" if view == "points" else "#viewport rect.hour-bar"
    return '#viewport svg.d3plus-render-svg rect[data-key^="treemap-"]' if view == "treemap" else "#viewport svg.d3plus-render-svg rect[aria-label]"


def wait_chart(page, hour="all", metric="total", view=None, after_revision=None, dimensions=False):
    # Timer polling also works when Chrome suspends a frame's animation frames.
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        state = page.evaluate("""() => {
            const status = document.querySelector('#status'), viewport = document.querySelector('#viewport');
            return {state: status.dataset.state, message: status.textContent, ...viewport.dataset,
                    width: viewport.clientWidth, height: viewport.clientHeight};
        }""")
        assert state["state"] != "error", state["message"]
        if (state["state"] == "ready" and state.get("hour") == str(hour)
                and state.get("metric") == metric and (view is None or state.get("view") == view)
                and (after_revision is None or int(state.get("renderRevision", 0)) > after_revision)
                and (not dimensions or (int(state.get("renderWidth", 0)) == state["width"]
                                        and int(state.get("renderHeight", 0)) == state["height"]))):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"Chart did not reach the requested completed render: {state}")


def verify_chart_geometry(page, expected, renderer, view):
    """Compare actual SVG attributes with independent numeric references."""
    rows = expected["rows"]
    if not rows:
        return
    marks = page.locator(chart_marks(renderer, view)).evaluate_all("""nodes => nodes.map(node => ({
        label: node.getAttribute('aria-label'), key: node.getAttribute('data-key'),
        x: Number(node.getAttribute('x')), y: Number(node.getAttribute('y')),
        width: Number(node.getAttribute('width')), height: Number(node.getAttribute('height')),
        cx: Number(node.getAttribute('cx')), cy: Number(node.getAttribute('cy')), radius: Number(node.getAttribute('r'))
    }))""")
    maximum = max(row["value"] for row in rows)
    if renderer == "d3":
        width, height = page.locator("#viewport > svg").evaluate(
            "node => [node.viewBox.baseVal.width, node.viewBox.baseVal.height]")
        if view == "points":
            def mercator(longitude, latitude):
                return math.radians(longitude), -math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2))
            # Fixed geographic bounds and fit extent, independent of D3/data
            # attached to the DOM. Mercator uses north-negative display y.
            left, bottom = mercator(-74.025, 40.69)
            right, top = mercator(-73.93, 40.79)
            scale = min((width - 70) / (right - left), (height - 160) / (bottom - top))
            tx = width / 2 - scale * (left + right) / 2
            ty = (35 + height - 125) / 2 - scale * (top + bottom) / 2
            for row, mark in zip(rows, marks):
                assert mark["label"] == f"{row['id']}, {row['label']}: {row['value']}"
                x, y = mercator(row["longitude"], row["latitude"])
                assert abs(mark["cx"] - (scale * x + tx)) < .05, f"Wrong projected x: {row['id']}"
                assert abs(mark["cy"] - (scale * y + ty)) < .05, f"Wrong projected y: {row['id']}"
                assert abs(mark["radius"] - (3 + 11 * math.sqrt(row["value"] / maximum))) < .01
            legend = page.locator(".point-legend").text_content()
            assert "relative to selected observations" in legend
            assert ("observation count" if expected["metadata"]["metric"] == "count" else "invented teaching units") in legend
        else:
            # Independent band-scale spacing and the standard 1/2/5/10 nice
            # tick step used by a linear scale with ten requested ticks.
            power = math.floor(math.log10(maximum / 10))
            error = maximum / 10 / 10 ** power
            factor = 10 if error >= math.sqrt(50) else 5 if error >= math.sqrt(10) else 2 if error >= math.sqrt(2) else 1
            step = factor * 10 ** power
            upper = math.ceil(maximum / step) * step
            band_step = (width - 76) / (len(rows) + .25)
            for index, (row, mark) in enumerate(zip(rows, marks)):
                assert mark["label"] == f"{row['label']}: {row['value']}"
                plotted_height = (height - 90) * row["value"] / upper
                assert abs(mark["x"] - (54 + band_step * (.25 + index))) < .05
                assert abs(mark["width"] - band_step * .75) < .05
                assert abs(mark["height"] - plotted_height) < .05, f"Wrong hourly height: {row['id']}"
                assert abs(mark["y"] - (height - 58 - plotted_height)) < .05
    elif view == "bars":
        by_key = {mark["key"]: mark for mark in marks}
        assert set(by_key) == {f"{row['id']}_{row['id']}" for row in rows}
        tallest = max(mark["height"] for mark in marks)
        for row in rows:
            mark = by_key[f"{row['id']}_{row['id']}"]
            assert mark["label"] == f"{row['label']}, x: {row['id']}, y: {row['value']}."
            assert abs(mark["height"] - tallest * row["value"] / maximum) < .5, f"Wrong neighborhood height: {row['id']}"
            assert abs(mark["y"] + mark["height"]) < .5, "Bar baseline is not zero"
    else:
        by_key = {mark["key"]: mark for mark in marks}
        assert set(by_key) == {f"treemap-{row['id']}" for row in rows}
        area = sum(mark["width"] * mark["height"] for mark in marks)
        total = sum(row["value"] for row in rows)
        for row in rows:
            mark = by_key[f"treemap-{row['id']}"]
            assert mark["label"].startswith(f"{row['label']}, {row['value']}, ")
            # Upstream tiling rounds pixels and pads leaves by a pixel. The
            # area share must still encode the corresponding row's value.
            assert math.isclose(mark["width"] * mark["height"] / area, row["value"] / total,
                                rel_tol=.02, abs_tol=.002), f"Wrong treemap area: {row['id']}"
    if renderer == "d3plus":
        labels = page.locator("#viewport svg.d3plus-render-svg text").all_text_contents()
        assert not any(label.strip() == "label" for label in labels)
        normalized = [re.sub(r"[\s-]", "", label) for label in labels]
        assert any(re.sub(r"[\s-]", "", row["label"]) in text for row in rows for text in normalized), "No real neighborhood labels rendered"


def verify_chart_dimensions(page, renderer):
    assert page.locator("#viewport > svg").evaluate("""node => {
        const viewport = document.querySelector('#viewport'), box = node.getBoundingClientRect();
        const drawing = node.querySelector('svg.d3plus-render-svg') || node;
        const view = drawing.viewBox.baseVal;
        return Math.abs(box.width - viewport.clientWidth) < 2 && Math.abs(box.height - viewport.clientHeight) < 2
          && Math.abs(view.width - viewport.clientWidth) < 2 && Math.abs(view.height - viewport.clientHeight) < 2
          && (drawing === node || (drawing.width.baseVal.value === viewport.clientWidth
                                  && drawing.height.baseVal.value === viewport.clientHeight));
    }"""), "Chart SVG has stale dimensions after resize"


def verify_chart(page, dataset, renderer, view, group, hour, metric):
    wait_chart(page, hour, metric, view)
    expected = chart_summary(dataset, group, hour, metric)
    marks = page.locator(chart_marks(renderer, view))
    assert marks.count() == len(expected["rows"]), f"{renderer}/{view}: actual SVG marks disagree with Python rows"
    assert page.locator("#count").inner_text() == str(expected["metadata"]["feature_count"])
    for mark in marks.all():
        assert mark.evaluate("node => { const box = node.getBBox(); return box.width > 0 && box.height > 0; }"), "Invisible chart mark"
    verify_chart_geometry(page, expected, renderer, view)
    with page.expect_download() as info:
        page.locator("#download").click()
    downloaded = json.loads(Path(info.value.path()).read_text(encoding="utf-8"))
    assert downloaded == expected, f"{renderer}/{view}: downloaded summary differs from Python preparation"
    details = page.locator("#summary")
    if not details.evaluate("node => node.open"):
        details.locator("summary").click()
    rows = page.locator("#summary-body tr")
    if not expected["rows"]:
        assert rows.count() == 1 and rows.inner_text() == "No observations at this hour."
        assert rows.locator("td").get_attribute("colspan") == "7"
        assert page.locator("#viewport svg").count() == 0, "Empty chart retained SVG marks"
        return
    assert rows.count() == len(expected["rows"])
    for index, row in enumerate(expected["rows"]):
        values = rows.nth(index).locator("td").all_text_contents()
        assert values[:2] == [row["id"], row["label"]]
        assert list(map(float, values[2:])) == [row[key] for key in ["count", "total", "value", "longitude", "latitude"]]


def check_chart_resize_overlap(page, dataset):
    """Keep D3plus's callback pending while the resize debounce fires."""
    page.evaluate("""() => {
        const prototype = d3plus.BarChart.prototype, original = prototype.render;
        window.restoreChartRender = () => { prototype.render = original; };
        prototype.render = function(callback) {
            return original.call(this, () => setTimeout(callback, 450));
        };
    }""")
    try:
        before = int(page.locator("#viewport").get_attribute("data-render-revision"))
        page.locator("#hour").focus()
        page.locator("#hour").select_option("8")
        page.wait_for_function("document.querySelector('#status').dataset.state === 'loading'")
        page.set_viewport_size({"width": 1100, "height": 900})
        wait_chart(page, 8, "total", "bars", after_revision=before + 1, dimensions=True)
        assert page.evaluate("document.activeElement.id") == "hour", "Updating a select lost keyboard focus"
        assert page.locator("#hour").input_value() == "8"
        verify_chart(page, dataset, "d3plus", "bars", "neighborhood", 8, "total")
        verify_chart_dimensions(page, "d3plus")
    finally:
        page.evaluate("window.restoreChartRender()")
    before = int(page.locator("#viewport").get_attribute("data-render-revision"))
    page.set_viewport_size({"width": 1280, "height": 900})
    page.locator("#hour").select_option("all")
    wait_chart(page, "all", "total", "bars", after_revision=before, dimensions=True)


def check_chart_app(page, origin, lesson, diagnostics):
    _, renderer, view, group = lesson
    dataset = json.loads((ROOT / "content/data/nyc-observations.geojson").read_text())
    page.set_viewport_size({"width": 1280, "height": 900})
    response = page.goto(f"{origin}/apps/{renderer}/?view={view}", wait_until="domcontentloaded")
    assert response.ok
    verify_chart(page, dataset, renderer, view, group, "all", "total")
    if renderer == "d3plus" and view == "bars":
        check_chart_resize_overlap(page, dataset)
    total_geometry = page.locator(chart_marks(renderer, view)).evaluate_all(
        "nodes => nodes.map(node => { const b = node.getBBox(); return [b.x, b.y, b.width, b.height]; })")
    page.screenshot(path=str(diagnostics / f"{renderer}-{view}-desktop.png"), full_page=True)
    page.locator("#metric").focus()
    page.locator("#metric").select_option("count")
    wait_chart(page, "all", "count", view)
    assert page.evaluate("document.activeElement.id") == "metric", "Metric update lost keyboard focus"
    verify_chart(page, dataset, renderer, view, group, "all", "count")
    count_geometry = page.locator(chart_marks(renderer, view)).evaluate_all(
        "nodes => nodes.map(node => { const b = node.getBBox(); return [b.x, b.y, b.width, b.height]; })")
    assert count_geometry != total_geometry, f"{renderer}/{view}: changing metric did not change SVG geometry"
    page.locator("#hour").select_option("8")
    verify_chart(page, dataset, renderer, view, group, 8, "count")
    page.locator("#metric").select_option("total")
    verify_chart(page, dataset, renderer, view, group, 8, "total")
    page.locator("#hour").select_option("0")
    verify_chart(page, dataset, renderer, view, group, 0, "total")
    page.locator("#hour").select_option("all")
    verify_chart(page, dataset, renderer, view, group, "all", "total")
    # Exercise the view control and clearing after a renderer instance switch.
    other = "points" if renderer == "d3" and view == "bars" else "bars" if view != "bars" else "treemap"
    other_group = "point" if other == "points" else "hour" if renderer == "d3" else "neighborhood"
    page.locator("#view").select_option(other)
    verify_chart(page, dataset, renderer, other, other_group, "all", "total")
    page.locator("#view").select_option(view)
    verify_chart(page, dataset, renderer, view, group, "all", "total")
    before = int(page.locator("#viewport").get_attribute("data-render-revision"))
    page.set_viewport_size({"width": 390, "height": 844})
    wait_chart(page, "all", "total", view, after_revision=before, dimensions=True)
    verify_chart_dimensions(page, renderer)
    verify_chart_geometry(page, chart_summary(dataset, group), renderer, view)
    no_overflow(page)
    assert page.locator(".table-scroll").evaluate("node => node.scrollWidth > node.clientWidth && getComputedStyle(node).overflowX === 'auto'")
    page.screenshot(path=str(diagnostics / f"{renderer}-{view}-mobile.png"), full_page=True)
    # A fresh app interpreter must honor the same parameters on initial load.
    # At this width its chart starts below the fold; rendering must not wait
    # for visibility or rely on a prior desktop render.
    page.goto(f"{origin}/apps/{renderer}/?view={view}&hour=8&metric=count", wait_until="domcontentloaded")
    assert page.locator("#viewport").bounding_box()["y"] > 844
    verify_chart(page, dataset, renderer, view, group, 8, "count")
    verify_chart_dimensions(page, renderer)


def open_notebook(page, origin, name):
    """Wait for the requested document, rather than a restored adjacent tab."""
    response = page.goto(f"{origin}/lite/lab/index.html?path={name}", wait_until="domcontentloaded")
    assert response.ok
    tab = page.locator(".lm-TabBar-tabLabel").filter(has_text=re.compile(f"^{re.escape(name)}$"))
    tab.wait_for(state="visible", timeout=90000)
    tab.click()
    source = json.loads((ROOT / "content" / name).read_text(encoding="utf-8"))
    title = "".join(source["cells"][0]["source"]).splitlines()[0].removeprefix("# ")
    panel = page.locator(".jp-NotebookPanel").filter(has=page.locator("h1").filter(has_text=title))
    panel.wait_for(state="visible", timeout=90000)
    editor = panel.locator(".jp-CodeCell .cm-content").first
    editor.wait_for(state="visible", timeout=90000)
    editor.click()
    page.keyboard.press("Escape")
    return panel, source, title


def run_chart_notebook(page, origin, lesson, diagnostics):
    name, renderer, view, group = lesson
    page.set_viewport_size({"width": 1280, "height": 1000})
    panel, source, title = open_notebook(page, origin, name)
    hour, metric = (8, "count") if name.startswith("04-") else ("all", "total")
    if hour == 8:
        parameters = next("".join(cell["source"]) for cell in source["cells"]
                          if cell["cell_type"] == "code" and "".join(cell["source"]).startswith("hour = 'all'"))
        editor = panel.locator(".jp-CodeCell").filter(has_text="hour = 'all'").locator(".cm-content")
        editor.click()
        editor.press("ControlOrMeta+A")
        page.keyboard.insert_text(parameters.replace("hour = 'all'", "hour = 8").replace("metric = 'total'", "metric = 'count'"))
        page.keyboard.press("Escape")
    page.get_by_role("menuitem", name="Run", exact=True).click()
    page.locator(".lm-Menu-itemLabel").filter(has_text=re.compile(r"^Run All Cells$")).click()
    panel.locator(".jp-OutputArea").filter(has_text="Python preparation and empty-selection checks passed.").wait_for(state="attached", timeout=150000)
    iframe = panel.locator('.jp-OutputArea iframe[src*="/apps/"]').last
    iframe.wait_for(timeout=150000, state="attached")
    iframe.scroll_into_view_if_needed()
    assert iframe.evaluate("node => node.src") == f"{origin}/apps/{renderer}/?view={view}&hour={hour}&metric={metric}"
    assert iframe.get_attribute("title") == f"Interactive {title}"
    frame = iframe.element_handle().content_frame()
    assert frame is not None, "Notebook iframe did not attach a browsing context"
    wait_chart(frame, hour, metric, view)
    dataset = json.loads((ROOT / "content/data/nyc-observations.geojson").read_text())
    verify_chart_geometry(frame, chart_summary(dataset, group, hour, metric), renderer, view)
    assert frame.locator("#count").inner_text() == str(6 if hour == 8 else 24)
    assert frame.locator(chart_marks(renderer, view)).count() == len(chart_summary(dataset, group, hour, metric)["rows"])
    frame.locator("#hour").select_option("8")
    wait_chart(frame, 8, metric, view)
    assert frame.locator("#count").inner_text() == "6"
    assert frame.locator(chart_marks(renderer, view)).count() == (1 if group == "hour" else 6)
    frame.locator("#hour").select_option("0")
    wait_chart(frame, 0, metric, view)
    assert frame.locator(chart_marks(renderer, view)).count() == 0
    assert panel.locator(".jp-OutputArea-error").count() == 0
    assert f"Selected observations: {6 if hour == 8 else 24}" in "\n".join(panel.locator(".jp-OutputArea").all_inner_texts())
    frame.locator("#hour").select_option("all")
    wait_chart(frame, "all", metric, view)
    verify_chart_geometry(frame, chart_summary(dataset, group, metric=metric), renderer, view)
    assert frame.locator(chart_marks(renderer, view)).count() == {"hour": 4, "point": 24, "neighborhood": 6}[group]
    iframe.scroll_into_view_if_needed()
    page.screenshot(path=str(diagnostics / f"{name.removesuffix('.ipynb')}-embedded.png"))


def run_welcome_notebook(page, origin):
    page.set_viewport_size({"width": 1280, "height": 900})
    open_notebook(page, origin, "01-welcome.ipynb")
    page.get_by_role("menuitem", name="Run", exact=True).click()
    page.locator(".lm-Menu-itemLabel").filter(has_text=re.compile(r"^Run All Cells$")).click()
    page.wait_for_function("document.body.innerText.includes('08:00 observations: 6')", timeout=150000)
    outputs = "\n".join(page.locator(".jp-OutputArea").all_inner_texts())
    assert "Observations: 24" in outputs
    assert page.locator(".jp-OutputArea-error").count() == 0
    page.locator(".jp-Notebook").evaluate("node => { node.scrollTop = node.scrollHeight; }")
    app_link = page.get_by_role("link", name="2D PyScript map", exact=True)
    app_link.wait_for(state="visible", timeout=30000)
    assert app_link.evaluate("node => node.href") == origin + "/apps/leaflet/"
    if app_link.get_attribute("target") == "_blank":
        with page.expect_popup() as popup:
            app_link.click()
        launched = popup.value
    else:
        app_link.click()
        launched = page
    launched.wait_for_url(origin + "/apps/leaflet/")
    launched.wait_for_selector('body[data-renderer="leaflet"]')
    assert launched.locator("h1").inner_text() == "Put your data on the map."
    if launched != page:
        launched.close()


def check_failure_cases(context, origin):
    for route, pattern, expected in [
        ("deck", "https://cdn.jsdelivr.net/npm/deck.gl@*/*", "Could not load"),
        ("leaflet", "https://cdn.jsdelivr.net/npm/leaflet@*/dist/leaflet.css", "required Leaflet stylesheet"),
        ("leaflet", "https://pyscript.net/releases/*/core.js", "PyScript runtime"),
        ("d3", "https://cdn.jsdelivr.net/npm/d3@*/dist/d3.min.js", "required D3"),
        ("d3plus", "https://cdn.jsdelivr.net/npm/@d3plus/core@*/umd/d3plus-core.full.min.js", "required D3plus core"),
        ("d3", "https://pyscript.net/releases/*/core.js", "PyScript runtime"),
    ]:
        blocked = context.new_page()
        blocked.route(pattern, lambda request: request.abort())
        blocked.goto(f"{origin}/apps/{route}/", wait_until="domcontentloaded")
        blocked.wait_for_function("document.querySelector('#status').dataset.state === 'error'", timeout=15000)
        assert expected in blocked.locator("#status").inner_text()
        assert blocked.locator("#download").is_disabled()
        assert blocked.locator("nav a").first.is_visible()
        blocked.close()
    unavailable = context.new_page()
    unavailable.add_init_script("const getContext = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function(type, ...args) { return type.startsWith('webgl') ? null : getContext.call(this, type, ...args); };")
    unavailable.goto(origin + "/apps/scene/")
    unavailable.wait_for_function("document.querySelector('#status').dataset.state === 'error'", timeout=15000)
    assert "WebGL" in unavailable.locator("#status").inner_text()
    assert unavailable.locator("#download").is_disabled()
    unavailable.close()
    for route in ["d3/?view=treemap", "d3plus/?view=points", "d3/?hour=24", "d3plus/?metric=mean"]:
        invalid = context.new_page()
        invalid.goto(f"{origin}/apps/{route}", wait_until="domcontentloaded")
        invalid.wait_for_function("document.querySelector('#status').dataset.state === 'error'", timeout=150000)
        assert any(text in invalid.locator("#status").inner_text() for text in ["Invalid view", "Hour must", "Metric must"])
        assert invalid.locator("#download").is_disabled()
        invalid.close()


def capture_failure(context, diagnostics, messages, failed_requests, error):
    captures = []
    for index, page in enumerate(context.pages):
        if page.is_closed():
            continue
        try:
            path = diagnostics / f"failure-page-{index}.png"
            page.screenshot(path=str(path), full_page=True, timeout=10000)
            captures.append({"url": page.url, "screenshot": path.name})
        except Exception as capture_error:
            captures.append({"url": page.url, "capture_error": str(capture_error)})
    (diagnostics / "failure.json").write_text(json.dumps({"error": repr(error), "pages": captures,
        "console": messages, "failed_requests": failed_requests}, indent=2, ensure_ascii=False), encoding="utf-8")


def main(executable=None):
    diagnostics = ROOT / "tmp/browser"
    diagnostics.mkdir(parents=True, exist_ok=True)
    server, base = make_server(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}{base}"
    try:
        with sync_playwright() as playwright:
            launch = {"headless": True, "args": ["--enable-unsafe-swiftshader"]}
            if executable:
                launch["executable_path"] = executable
            browser = playwright.chromium.launch(**launch)
            context = browser.new_context(accept_downloads=True)
            messages, failed_requests, errors = [], [], []

            def observe(page):
                page.on("console", lambda message: messages.append({"url": page.url, "type": message.type, "text": message.text}))
                page.on("requestfailed", lambda request: failed_requests.append({"url": request.url, "failure": request.failure}))
                page.on("pageerror", lambda error: messages.append({"url": page.url, "type": "pageerror", "text": str(error)}))

            context.on("page", observe)
            try:
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(origin + "/", wait_until="networkidle")
                assert page.title().startswith("JupyterLite")
                no_overflow(page)
                page.screenshot(path=str(diagnostics / "landing-desktop.png"), full_page=True)
                for href in ["book/", "lite/lab/index.html", "apps/leaflet/", "apps/deck/", "apps/scene/", "apps/d3/", "apps/d3plus/", "integrations/"]:
                    assert page.locator(f'a[href^="{href}"]').count() > 0, f"Missing launch link {href}"
                page.set_viewport_size({"width": 390, "height": 844})
                no_overflow(page)
                page.screenshot(path=str(diagnostics / "landing-mobile.png"), full_page=True)
                selected_ids = None
                for route in ["leaflet", "deck", "scene"]:
                    ids = check_app(page, origin, route, diagnostics)
                    assert selected_ids is None or ids == selected_ids, "Renderer exports disagree"
                    selected_ids = ids
                for lesson in CHART_LESSONS:
                    check_chart_app(page, origin, lesson, diagnostics)
                assert not errors, "JavaScript page errors: " + "; ".join(errors)
                for route, text in [("book/", "A little Python"), ("book/runtimes/", "Two browser environments"), ("integrations/", "Three GIS destinations")]:
                    response = page.goto(f"{origin}/{route}", wait_until="networkidle")
                    assert response.ok
                    assert text in page.locator("body").inner_text()
                    no_overflow(page)
                run_welcome_notebook(page, origin)
                for lesson in CHART_LESSONS:
                    run_chart_notebook(page, origin, lesson, diagnostics)
                check_failure_cases(context, origin)
            except Exception as error:
                capture_failure(context, diagnostics, messages, failed_requests, error)
                raise
            finally:
                browser.close()
        print(f"PASS: live Python in geospatial labs and four chart views, SVG/GPU clearing, tables/exports, keyboard/context recovery, five notebook executions and embedded apps, responsive layouts and required-asset failures at {base or '/'}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-executable", help="Optional installed Chrome/Chromium executable")
    args = parser.parse_args()
    main(args.browser_executable)
