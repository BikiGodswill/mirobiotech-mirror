#!/usr/bin/env python3
"""Verify every mirrored page's <html lang> matches its URL locale prefix,
and re-fetch mismatches sequentially with a fresh session until correct."""
import os, re, time, requests

BASE = "https://www.mirobiotech.com"
OUT = "site"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

LANG_RE = re.compile(r'<html[^>]*lang="([A-Za-z-]+)"')


def expected(route):
    for loc in ("de", "it", "sv"):
        if route == f"/{loc}" or route.startswith(f"/{loc}/"):
            return loc
    return "en"


def routes():
    out = []
    for root, _, files in os.walk(OUT):
        if "index.html" not in files:
            continue
        rel = os.path.relpath(root, OUT)
        route = "/" if rel == "." else "/" + rel.replace(os.sep, "/")
        out.append((route, os.path.join(root, "index.html")))
    return sorted(out)


def lang_of(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        head = f.read(6000)
    m = LANG_RE.search(head)
    return m.group(1) if m else "?"


bad = [(r, p, lang_of(p), expected(r)) for r, p in routes()]
bad = [b for b in bad if b[2] != b[3]]
print(f"locale mismatches: {len(bad)} of {len(routes())} pages")

if bad:
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                         "Cookie": "NEXT_LOCALE=en"})
    fixed, failed = 0, []
    for route, path, got, want in bad:
        ok = False
        for attempt in range(6):
            r = sess.get(BASE + route, timeout=60)
            if r.status_code == 200 and r.content:
                m = LANG_RE.search(r.content[:6000].decode("utf-8", "ignore"))
                got2 = m.group(1) if m else "?"
                if got2 == want:
                    open(path, "wb").write(r.content)
                    fixed += 1
                    ok = True
                    break
            time.sleep(1.5 + attempt)
        if not ok:
            failed.append((route, got2 if 'got2' in dir() else got))
            print("  FAIL", route, "wanted", want)
        time.sleep(0.6)
    print(f"fixed: {fixed}, failed: {len(failed)}")
