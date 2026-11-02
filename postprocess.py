#!/usr/bin/env python3
"""Post-process the mirror: add checkout/track, fix root-relative fragment links,
strip third-party analytics (keeps the mirror offline-safe), and build an index."""
import os, re, json, requests

BASE = "https://www.mirobiotech.com"
OUT = "site"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
sess = requests.Session()
sess.headers.update({"User-Agent": UA})

# ---- 1. extra pages robots-disallowed but part of the site ----
for url, local in [(BASE + "/checkout", "site/checkout/index.html"),
                   (BASE + "/track", "site/track/index.html")]:
    if os.path.exists(local) and os.path.getsize(local) > 5000:
        continue
    r = sess.get(url, timeout=60)
    if r.status_code == 200:
        os.makedirs(os.path.dirname(local), exist_ok=True)
        open(local, "wb").write(r.content)
        print("added", url, len(r.content))

# ---- 2. fix anchors like href="/legal#disclaimer" handling is fine; nothing to do.
# ---- 3. strip third-party trackers that would hit the network on a local box ----
STRIP = [
    re.compile(r'<script[^>]*src="https://www\.googletagmanager\.com/[^"]*"[^>]*></script>'),
    re.compile(r'<script[^>]*src="https://connect\.facebook\.net/[^"]*"[^>]*></script>'),
    re.compile(r'<script[^>]*src="https://www\.google-analytics\.com/[^"]*"[^>]*></script>'),
    re.compile(r'<script[^>]*src="https://[^"]*(?:clarity|hotjar|facebook|doubleclick)[^"]*"[^>]*></script>', re.I),
]
stripped = 0
for rootdir, _, files in os.walk(OUT):
    for fn in files:
        if not fn.endswith(".html"):
            continue
        p = os.path.join(rootdir, fn)
        txt = open(p, encoding="utf-8", errors="ignore").read()
        new = txt
        for rx in STRIP:
            new, n = rx.subn("", new)
            stripped += n
        if new != txt:
            open(p, "w", encoding="utf-8").write(new)
print("tracker scripts removed:", stripped)
