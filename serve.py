#!/usr/bin/env python3
"""
Local server for the Miro Biotech mirror.
Serves the on-disk Next.js-style tree (/products/bpc-157 -> products/bpc-157/index.html)
with clean URLs, correct MIME types, 404 handling and a /_mirror health endpoint.
"""
import os, sys, json, mimetypes, posixpath, http.server, socketserver
from urllib.parse import unquote, urlparse, quote, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "site")
API_DIR = os.path.join(HERE, "api-cache")
PORT = int(os.environ.get("PORT", 8000))

EXTRA = {
    ".webp": "image/webp", ".avif": "image/avif", ".woff2": "font/woff2",
    ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".json": "application/json", ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml", ".ico": "image/x-icon",
}
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/webp", ".webp")


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def translate_path(self, path):
        p = urlparse(path).path
        p = unquote(p)
        p = posixpath.normpath(p)
        p = p.lstrip("/")
        full = os.path.join(ROOT, p) if p else ROOT
        return full

    def _resolve(self, path):
        """Return (filepath, is_dir_redirect)."""
        fs = self.translate_path(path)
        if os.path.isdir(fs):
            idx = os.path.join(fs, "index.html")
            if os.path.isfile(idx):
                return idx
            return None
        if os.path.isfile(fs):
            return fs
        # clean URL: /products/bpc-157 -> products/bpc-157/index.html
        cand = os.path.join(fs, "index.html")
        if os.path.isfile(cand):
            return cand
        # try with guessed extension for /icon /apple-icon style routes
        for ext in (".ico", ".png", ".webp", ".svg"):
            if os.path.isfile(fs + ext):
                return fs + ext
        return None

    def _send_file(self, fp, status=200):
        try:
            st = os.stat(fp)
        except OSError:
            return self._not_found()
        ext = os.path.splitext(fp)[1].lower()
        ctype = EXTRA.get(ext) or mimetypes.guess_type(fp)[0] or "application/octet-stream"
        if ext == ".html":
            ctype = "text/html; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(st.st_size))
        # long cache for hashed build assets
        if "/_next/static/" in fp or "/fonts/" in fp:
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(fp, "rb") as f:
            try:
                self.wfile.write(f.read())
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _not_found(self):
        nf = os.path.join(ROOT, "404.html")
        if os.path.isfile(nf):
            return self._send_file(nf, 404)
        self.send_error(404)

    # ---- /_next/image emulation: return the full-size original ----
    def _next_image(self):
        q = parse_qs(urlparse(self.path).query)
        url = (q.get("url") or [""])[0]
        fp = self._resolve(url) if url.startswith("/") else None
        if fp:
            return self._send_file(fp)
        return self._not_found()

    # ---- canned JSON API (captured from the live site, checkout stubbed) ----
    def _api(self, path):
        name = path[len("/api/"):].strip("/").replace("/", "_")
        fp = os.path.join(API_DIR, name + ".json")
        if path.rstrip("/") == "/api/meta/track":
            return self._json({"ok": True})
        if path.rstrip("/") == "/api/crypto/quote":
            # non-fatal quote stub so crypto payment UI renders without a network call
            return self._json({"amount": "0.00000000", "currency": "btc",
                               "rate": 0, "expiresAt": None, "stub": True})
        if path.rstrip("/").startswith("/api/checkout") or path.rstrip("/") in (
                "/api/pay", "/api/pay-started", "/api/cart-capture", "/api/crypto/pay",
                "/api/public/v1/payments/continue"):
            return self._json({"error": "static mirror", "message":
                               "Checkout is disabled in this offline mirror."}, 501)
        if os.path.isfile(fp):
            try:
                return self._json(json.load(open(fp)))
            except Exception:
                pass
        return self._json({"error": "not_found"}, 404)

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            self.rfile.read(n)
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self._api(path)
        self._json({"error": "not_found"}, 404)

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self._api(path)
        if path == "/_next/image":
            return self._next_image()
        if path == "/_mirror/health":
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        fp = self._resolve(path)
        if fp is None:
            return self._not_found()
        self._send_file(fp)

    def do_HEAD(self):
        self.do_GET()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    mimetypes.init()
    with Server(("0.0.0.0", PORT), Handler) as httpd:
        print(f"mirror serving {ROOT} on http://0.0.0.0:{PORT}", flush=True)
        httpd.serve_forever()
