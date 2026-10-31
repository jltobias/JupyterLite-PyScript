"""Serve _site at its recorded base URL (including repository subpath builds)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def make_server(port=8000):
    site = ROOT / "_site"
    base = json.loads((site / "build-info.json").read_text())["base_url"]

    class MountedHandler(SimpleHTTPRequestHandler):
        def valid_mount(self):
            parsed = urlsplit(self.path)
            if base and parsed.path == base:
                self.send_response(302)
                self.send_header("Location", base + "/")
                self.end_headers()
                return False
            if base and not parsed.path.startswith(base + "/"):
                self.send_error(404, "Use the configured repository subpath")
                return False
            return True

        def translate_path(self, path):
            # Keep self.path public so inherited directory redirects preserve
            # the repository prefix; only filesystem translation removes it.
            if base and path.startswith(base + "/"):
                path = path[len(base):]
            return super().translate_path(path)

        def do_GET(self):
            if self.valid_mount():
                super().do_GET()

        def do_HEAD(self):
            if self.valid_mount():
                super().do_HEAD()

    server = ThreadingHTTPServer(("127.0.0.1", port), partial(MountedHandler, directory=str(site)))
    return server, base


if __name__ == "__main__":
    server, base = make_server()
    print(f"Preview: http://127.0.0.1:8000{base}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
