"""Verify the assembled artifact, source notebooks and shared data contract."""
import ast
from contextlib import redirect_stdout
from html.parser import HTMLParser
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.links.append(value)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_file(path):
    assert path.is_file(), f"Missing artifact: {path.relative_to(SITE)}"


def check_links(base):
    # Check all owned pages plus generated book routes; JupyterLite's vendor
    # application links are checked by launch/browser tests rather than crawled.
    pages = [SITE / "index.html", *list((SITE / "apps").rglob("*.html")),
             *list((SITE / "integrations").rglob("*.html")),
             *list((SITE / "book").rglob("*.html"))]
    count = 0
    for page in pages:
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for link in parser.links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            path = unquote(parts.path)
            if path.startswith("/"):
                if base:
                    assert path == base or path.startswith(base + "/"), f"Escapes repository subpath: {page}: {link}"
                    path = path[len(base):]
                destination = SITE / path.lstrip("/")
            else:
                destination = page.parent / path
            destination = destination.resolve()
            assert destination.is_relative_to(SITE.resolve()), f"Link escapes artifact: {page}: {link}"
            if destination.is_dir():
                destination /= "index.html"
            assert destination.is_file(), f"Broken local link in {page.relative_to(SITE)}: {link}"
            count += 1
    return count


def check_data_and_python():
    selection = load_module("selection", ROOT / "content/selection.py")
    generator = load_module("generate_data", ROOT / "scripts/generate_data.py")
    dataset = json.loads((ROOT / "content/data/nyc-observations.geojson").read_text())
    assert dataset == generator.make_dataset(), "Dataset differs from deterministic generator"
    assert len(dataset["features"]) == 24
    assert len({f["id"] for f in dataset["features"]}) == 24
    assert dataset["metadata"]["simulated"] is True
    original = json.dumps(dataset, sort_keys=True)
    for hour, count in [("all", 24), (8, 6), (12, 6), (18, 6), (21, 6), (0, 0), (23, 0)]:
        collection = selection.feature_collection(dataset, hour)
        exported = json.loads(selection.export_geojson(dataset, hour))
        assert collection == exported
        assert len(collection["features"]) == count == collection["metadata"]["feature_count"]
        assert "crs" not in collection
        for f in collection["features"]:
            assert f["type"] == "Feature" and f["geometry"]["type"] == "Point"
            lon, lat = f["geometry"]["coordinates"]
            assert -74.1 < lon < -73.8 and 40.6 < lat < 40.9
            assert f["properties"]["simulated"] is True
            assert hour == "all" or f["properties"]["hour"] == hour
    assert original == json.dumps(dataset, sort_keys=True), "Selection mutated input"
    copied = selection.select_features(dataset, 8)
    copied[0]["properties"]["value"] = -1
    assert dataset["features"][0]["properties"]["value"] != -1
    check_hour_selectors(selection, dataset)
    for path in [*list((ROOT / "scripts").glob("*.py")), ROOT / "content/selection.py", ROOT / "site/apps/shared/lab.py"]:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert json.loads((SITE / "data/nyc-observations.geojson").read_text()) == dataset
    assert (SITE / "apps/shared/selection.py").read_bytes() == (ROOT / "content/selection.py").read_bytes()


def check_hour_selectors(selection, dataset):
    for valid in [8, "8", "08"]:
        assert len(selection.feature_collection(dataset, valid)["features"]) == 6
    for bad in [-1, 24, "invalid", "8.9", 8.9, 8.0, True, False]:
        try:
            selection.feature_collection(dataset, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Accepted invalid hour {bad}")


def check_notebooks(base):
    import nbformat
    names = ["01-welcome.ipynb", "02-explore-data.ipynb", "03-author-an-app.ipynb"]
    for name in names:
        notebook = nbformat.read(ROOT / "content" / name, as_version=4)
        nbformat.validate(notebook)
        assert notebook.metadata.kernelspec.language == "python"
        for cell in notebook.cells:
            if cell.cell_type == "code":
                ast.parse(cell.source)
        packaged = SITE / "lite/files" / name
        assert_file(packaged)
        expected = json.loads((ROOT / "content" / name).read_text(encoding="utf-8"))
        for cell in expected["cells"]:
            if cell["cell_type"] == "markdown":
                cell["source"] = [line.replace("{{HUB_BASE}}", base) for line in cell["source"]]
        actual = json.loads(packaged.read_text(encoding="utf-8"))
        assert actual == expected, f"Packaged notebook differs from source/prefix substitution: {name}"
        for cell in actual["cells"]:
            if cell["cell_type"] == "markdown":
                markdown = "".join(cell["source"])
                assert "{{HUB_BASE}}" not in markdown and "../../apps/" not in markdown
    for path in ["data/nyc-observations.geojson", "selection.py", "source/lab.py", "source/lab.js", "source/apps/leaflet/index.html"]:
        assert_file(SITE / "lite/files" / path)
    # Execute every lesson's real Python cells with an isolated copy of its
    # packaged files. This catches wrong lesson paths and missing modules.
    original_cwd = Path.cwd()
    work = ROOT / "tmp" / f"notebook-check-{uuid4().hex}"
    work.mkdir(parents=True)
    try:
        shutil.copytree(SITE / "lite/files", work, dirs_exist_ok=True)
        sys.path.insert(0, str(work))
        try:
            os.chdir(work)
            for name in names:
                notebook = nbformat.read(work / name, as_version=4)
                namespace = {"__name__": "__main__"}
                with redirect_stdout(io.StringIO()):
                    for index, cell in enumerate(notebook.cells):
                        if cell.cell_type == "code":
                            exec(compile(cell.source, f"{name}:cell{index}", "exec"), namespace)
        finally:
            os.chdir(original_cwd)
            sys.path.pop(0)
    finally:
        resolved = work.resolve()
        assert resolved.is_relative_to((ROOT / "tmp").resolve()), "Unsafe notebook-check cleanup target"
        shutil.rmtree(resolved)


def main():
    assert_file(SITE / "build-info.json")
    base = json.loads((SITE / "build-info.json").read_text())["base_url"]
    for route in ["index.html", "lite/lab/index.html", "book/index.html", "integrations/index.html",
                  "apps/leaflet/index.html", "apps/deck/index.html", "apps/scene/index.html"]:
        assert_file(SITE / route)
    for chapter in ["runtimes", "data", "maps-and-scenes", "authoring", "nyc-taxi", "interoperability", "deployment"]:
        assert_file(SITE / "book" / chapter / "index.html")
    check_data_and_python()
    check_notebooks(base)
    checked = check_links(base)
    print(f"PASS: {checked} local links/assets, primary routes, 3 notebook schemas/execution and packaging, deterministic data, Python filter/export and empty selections (base={base or '/'}).")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
