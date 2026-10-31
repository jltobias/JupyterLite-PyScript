---
title: Build once, publish one static site
---

The repository combines four pieces in a single `_site` artifact: landing page, PyScript labs, JupyterLite notebooks and this **Jupyter Book 2 / MyST** book. No Python backend is deployed. Public links become available only after the GitHub Pages deployment succeeds.

## Local build

Use Python 3.11 or newer and Node.js 22 or newer, with npm on PATH. In an isolated environment:

```sh
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install -r requirements.txt
python scripts/build.py
python scripts/check_site.py
python scripts/preview.py
```

Open `http://localhost:8000`. First loads need network access for browser runtimes and graphics assets. Build time also needs network access for JupyterLite assets and the MyST web theme.

## Repository subpaths

GitHub Pages serves this project at `/JupyterLite-PyScript/`. The pipeline runs:

```sh
python scripts/build.py --base-url /JupyterLite-PyScript
python scripts/check_site.py
```

The helper passes `/JupyterLite-PyScript/book` as MyST's `BASE_URL` and substitutes the hub path in staged book links. Source book files stay reusable. Landing/app assets use relative URLs. JupyterLite builds at `_site/lite`; the notebooks, sample data and actual app source are packaged into that build.

For a local repository-path preview use `scripts/preview.py`; it mounts `_site` under the path recorded by the build. Then run the browser checks described in the README.

## GitHub Pages workflow

The workflow builds and checks on pull requests and pushes to `main`. On a push to `main`, it uploads **one** combined Pages artifact and deploys it through Actions. A maintainer selects **Settings → Pages → Source: GitHub Actions** once, then commits and pushes the source to `main`.

The base path is derived from the repository name in CI. Forks using a custom domain or a user-site repository should adjust it to the actual public URL path.

## What checks cover

Artifact checks validate primary destinations, local HTML asset/link paths, notebook schema basics, packaged notebook data, deterministic synthetic provenance, Python filter/export behavior including no matches, and MyST routes. Browser smoke checks load each app, verify the live Python selection and downloaded file, inspect desktop/mobile overflow, and test visible blocked-CDN/WebGL failures. They require a browser and internet access; a static link check alone cannot establish runtime success.

Sources: [MyST static export and BASE_URL](https://mystmd.org/guide/deployment), [JupyterLite CLI](https://jupyterlite.readthedocs.io/en/stable/reference/cli.html), [GitHub Pages custom Actions workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
