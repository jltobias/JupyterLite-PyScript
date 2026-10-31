"""Build one Pages artifact: landing page, PyScript labs, JupyterLite and JB2.

Requires the pinned requirements and Node.js 22+. No Python server is deployed.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def clean_generated(path):
    """Only recursively remove a resolved generated directory inside this repo."""
    lexical = Path(os.path.abspath(path))
    resolved = path.resolve()
    if lexical != resolved:
        raise ValueError(f"Refusing to clean a symlink or junction: {lexical}")
    if resolved == ROOT or not resolved.is_relative_to(ROOT):
        raise ValueError(f"Refusing to clean outside the repository: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def run(command, cwd=ROOT, env=None):
    print("Running:", " ".join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True)


def validate_base_url(base_url):
    if base_url and (not base_url.startswith("/") or base_url.startswith("//")
                     or ".." in base_url or any(c in base_url for c in ":?#\\")
                     or any(c.isspace() for c in base_url)):
        raise ValueError("--base-url must be an absolute URL path, e.g. /JupyterLite-PyScript")
    return base_url.rstrip("/")


def build(base_url=""):
    base_url = validate_base_url(base_url)
    output, staging = ROOT / "_site", ROOT / "tmp/build"
    clean_generated(output)
    clean_generated(staging)
    staging.mkdir(parents=True)
    shutil.copytree(ROOT / "site", output)
    shutil.copytree(ROOT / "content/data", output / "data")
    shutil.copy2(ROOT / "content/selection.py", output / "apps/shared/selection.py")
    shutil.copy2(ROOT / "content/chart_data.py", output / "apps/shared/chart_data.py")
    lite_content = staging / "lite-content"
    shutil.copytree(ROOT / "content", lite_content)
    (lite_content / "hub-config.json").write_text(
        json.dumps({"base_url": base_url}, indent=2) + "\n", encoding="utf-8")
    # Root-relative launches bypass JupyterLab's notebook-files URL resolver.
    # Substitute the actual deployment prefix without hardcoding a public host.
    for path in lite_content.glob("*.ipynb"):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "markdown":
                cell["source"] = [line.replace("{{HUB_BASE}}", base_url) for line in cell["source"]]
        path.write_text(json.dumps(notebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Learners can inspect actual deployed app source inside their notebook FS.
    shutil.copytree(output / "apps/shared", lite_content / "source")
    shutil.copytree(output / "apps", lite_content / "source/apps")
    run([sys.executable, "-m", "jupyter", "lite", "build", "--contents", lite_content,
         "--output-dir", output / "lite"], cwd=staging)
    book_stage = staging / "book"
    shutil.copytree(ROOT / "book", book_stage, ignore=shutil.ignore_patterns("_build"))
    for path in book_stage.rglob("*"):
        if path.suffix in {".md", ".yml", ".css"}:
            # MyST prepends BASE_URL to Markdown root links. /.. exits the book
            # mount after that prefix is added, preserving the repository path.
            replacement = "/.." if path.suffix == ".md" else base_url
            path.write_text(path.read_text(encoding="utf-8").replace("{{HUB_BASE}}", replacement), encoding="utf-8")
    executable = Path(sys.executable).parent / ("jupyter-book.exe" if os.name == "nt" else "jupyter-book")
    if not executable.exists():
        raise RuntimeError("Install requirements.txt into the Python environment used to run this script.")
    env = os.environ.copy()
    env["BASE_URL"] = f"{base_url}/book"
    run([executable, "build", "--html"], cwd=book_stage, env=env)
    generated_book = book_stage / "_build/html"
    if not (generated_book / "index.html").exists():
        raise RuntimeError("Jupyter Book did not produce _build/html/index.html")
    shutil.copytree(generated_book, output / "book")
    (output / ".nojekyll").touch()
    (output / "build-info.json").write_text(json.dumps({"base_url": base_url,
        "book_base_url": env["BASE_URL"], "dataset_count": 24}, indent=2), encoding="utf-8")
    print(f"Built combined site at {output} (base URL: {base_url or '/'})", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="", help="Repository URL prefix; empty for local root preview")
    args = parser.parse_args()
    build(args.base_url)
