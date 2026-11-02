#!/usr/bin/env python3
"""Mirror https://www.mirobiotech.com (all locales, all pages)."""
import os, re, sys, time, json, hashlib
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin, unquote, quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE = "https://www.mirobiotech.com"
OUT = "site"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

sess = requests.Session()
sess.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})

SKIP_DIRS = {"/api/", "/checkout", "/admin", "/track", "/_next/static/chunks/"}


def path_for(url):
    """Map a site URL to a local file path (Next.js style, no .html suffix)."""
    p = urlparse(url).path
    p = unquote(p)
    if p == "" or p == "/":
        return os.path.join(OUT, "index.html")
    p = p.rstrip("/")
    if os.path.splitext(p)[1]:
        return os.path.join(OUT, p.lstrip("/"))
    return os.path.join(OUT, p.lstrip("/"), "index.html")


def mkdirp(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def get(url, tries=3):
    for i in range(tries):
        try:
            r = sess.get(url, timeout=45)
            if r.status_code == 200:
                return r
            if r.status_code in (404, 410):
                return r
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return r if 'r' in dir() else None


def fetch_page(url):
    """Fetch HTML page and save."""
    r = get(url)
    if r is None:
        return (url, "error", 0)
    if r.status_code != 200:
        return (url, f"http{r.status_code}", 0)
    dest = path_for(url)
    mkdirp(dest)
    with open(dest, "wb") as f:
        f.write(r.content)
    return (url, "ok", len(r.content))


def fetch_asset(url):
    """Fetch a static asset (js/css/font/image/ico) and save under site/."""
    u = urlparse(url)
    if u.netloc and u.netloc not in ("www.mirobiotech.com", "mirobiotech.com"):
        return (url, "ext", 0)
    if u.path.startswith("/_next/image"):
        return (url, "nextimg", 0)
    dest = os.path.join(OUT, u.path.lstrip("/"))
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return (url, "cached", 0)
    r = get(url)
    if r is None or r.status_code != 200:
        return (url, f"http{r.status_code if r is not None else 'err'}", 0)
    mkdirp(dest)
    with open(dest, "wb") as f:
        f.write(r.content)
    return (url, "ok", len(r.content))


def main():
    # ---------- 1. sitemap ----------
    sm = sess.get(BASE + "/sitemap.xml", timeout=45).text
    root = ET.fromstring(sm.encode())
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text.strip() for loc in root.findall(".//s:loc", ns)]
    urls = [u for u in urls if "/api/" not in u]
    print(f"sitemap: {len(urls)} urls")

    # also grab robots-referenced extras
    urls += [BASE + "/site.webmanifest", BASE + "/favicon.ico",
             BASE + "/apple-icon", BASE + "/icon"]

    seen, todo = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            todo.append(u)

    # ---------- 2. pages ----------
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_page, u): u for u in todo}
        done = 0
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            done += 1
            if done % 25 == 0:
                print(f"  pages {done}/{len(todo)}")
    bad = [(u, s) for u, s, n in results if s not in ("ok", "nextimg")]
    print(f"pages done: {sum(1 for r in results if r[1]=='ok')} ok, {len(bad)} failed")

    # ---------- 3. discover same-origin assets from saved HTML ----------
    assets = set()
    pat = re.compile(r'(?:src|href)="(/[^"]+?)"')
    for rootdir, _, files in os.walk(OUT):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            raw = open(os.path.join(rootdir, fn), "r", encoding="utf-8", errors="ignore").read()
            for m in pat.findall(raw):
                if m.startswith(("/_next/static", "/images/", "/press-logos/",
                                 "/favicon", "/icon", "/apple-icon")):
                    assets.add(BASE + m.replace("&amp;", "&"))
            # css url() refs handled later
    # webp/jpg referenced raw in JSON payloads
    for m in set(re.findall(r'"\\?u?r?l?\\?"?:?\\?"(/images/[^"\\]+)"', "")):
        pass
    print(f"assets discovered from html: {len(assets)}")

    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(fetch_asset, a) for a in assets]
        res = [f.result() for f in as_completed(futs)]
    print(f"assets: {sum(1 for r in res if r[1] in ('ok','cached'))} saved, "
          f"{sum(1 for r in res if r[1] not in ('ok','cached'))} failed")

    # ---------- 4. css url() deps ----------
    css_deps = set()
    for rootdir, _, files in os.walk(OUT):
        for fn in files:
            if fn.endswith(".css"):
                p = os.path.join(rootdir, fn)
                txt = open(p, encoding="utf-8", errors="ignore").read()
                for m in re.findall(r'url\(([^)]+)\)', txt):
                    m = m.strip('\'" ')
                    if m.startswith("/"):
                        css_deps.add(BASE + m)
                    elif m.startswith("data:"):
                        continue
    with ThreadPoolExecutor(max_workers=10) as ex:
        res2 = [f.result() for f in as_completed(
            [ex.submit(fetch_asset, a) for a in css_deps])]
    print(f"css deps: {len(css_deps)} refs, {sum(1 for r in res2 if r[1] in ('ok','cached'))} saved")

    with open("crawl-report.json", "w") as f:
        json.dump({"pages_total": len(todo), "pages_failed": bad,
                   "assets_requested": len(assets | css_deps)}, f, indent=2)
    print("FAILED PAGES:", bad)


if __name__ == "__main__":
    main()
