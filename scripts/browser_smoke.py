"""Live runtime, renderer, notebook and failure checks against the built site.

Run after build/check_site; needs Playwright Chromium (or --browser-executable).
The preview mount uses build-info.json, so CI exercises a repository subpath.
"""
import argparse
import json
from pathlib import Path
import re
import threading

from playwright.sync_api import sync_playwright
from preview import make_server

ROOT = Path(__file__).resolve().parents[1]


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


def run_welcome_notebook(page, origin):
    page.set_viewport_size({"width": 1280, "height": 900})
    response = page.goto(origin + "/lite/lab/index.html?path=01-welcome.ipynb", wait_until="domcontentloaded")
    assert response.ok
    page.wait_for_selector(".jp-NotebookPanel", timeout=90000)
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
                for href in ["book/", "lite/lab/index.html", "apps/leaflet/", "apps/deck/", "apps/scene/", "integrations/"]:
                    assert page.locator(f'a[href^="{href}"]').count() > 0, f"Missing launch link {href}"
                page.set_viewport_size({"width": 390, "height": 844})
                no_overflow(page)
                page.screenshot(path=str(diagnostics / "landing-mobile.png"), full_page=True)
                selected_ids = None
                for route in ["leaflet", "deck", "scene"]:
                    ids = check_app(page, origin, route, diagnostics)
                    assert selected_ids is None or ids == selected_ids, "Renderer exports disagree"
                    selected_ids = ids
                assert not errors, "JavaScript page errors: " + "; ".join(errors)
                for route, text in [("book/", "A little Python"), ("book/runtimes/", "Two browser environments"), ("integrations/", "Three GIS destinations")]:
                    response = page.goto(f"{origin}/{route}", wait_until="networkidle")
                    assert response.ok
                    assert text in page.locator("body").inner_text()
                    no_overflow(page)
                run_welcome_notebook(page, origin)
                check_failure_cases(context, origin)
            except Exception as error:
                capture_failure(context, diagnostics, messages, failed_requests, error)
                raise
            finally:
                browser.close()
        print(f"PASS: live Python/renderers and GPU clearing, tables, keyboard/context recovery, notebook execution/launch, responsive layouts and required-asset failures at {base or '/'}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-executable", help="Optional installed Chrome/Chromium executable")
    args = parser.parse_args()
    main(args.browser_executable)
