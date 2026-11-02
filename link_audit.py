#!/usr/bin/env python3
"""Full internal-link audit: collect every internal href from the mirror + RSC
payloads, diff against what is on disk, and fetch anything missing from live."""
import os, re, json, requests
from urllib.parse import urlparse, unquote, urljoin

BASE = "https://www.mirobiotech.com"
OUT = "site"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
sess = requests.Session()
sess.headers.update({"User-Agent": UA})

HREF = re.compile(r'href="(/[^"#?]*)"')
# routes embedded in RSC/JSON payloads e.g. \"/de/warenkorb\" or "href":"/it/carrello"
RSC = re.compile(r'\\?"(?:href|url)\\?":\\?"(/[A-Za-z0-9\-_/%]+)\\?"')

links = set()
for root, _, files in os.walk(OUT):
    for f in files:
        if not f.endswith((".html", ".js")):
            continue
        t = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
        t2 = t.replace("\\/", "/")
        links |= set(HREF.findall(t))
        links |= set(RSC.findall(t2))

# keep only plausible page routes (no file extensions, not internal dirs)
ROUTE = re.compile(r'^/(de|it|sv)?/?[A-Za-z0-9\-_/]*$')
cands = {l.rstrip("/") or "/" for l in links
         if ROUTE.match(l) and not l.startswith(("/_next", "/images", "/press-logos",
                                                 "/api", "/_mirror", "/fonts"))}
print("internal page routes discovered:", len(cands))

def local_file(route):
    if route == "/":
        return os.path.join(OUT, "index.html")
    return os.path.join(OUT, route.lstrip("/"), "index.html")

missing = sorted(r for r in cands if not os.path.isfile(local_file(r)))
print("routes not on disk:", len(missing))

added, failed = [], []
for r in missing:
    try:
        resp = sess.get(BASE + r, timeout=60, allow_redirects=False)
        if resp.status_code == 200 and len(resp.content) > 3000:
            fp = local_file(r)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, "wb").write(resp.content)
            added.append(r)
        else:
            failed.append((r, resp.status_code,
                           resp.headers.get("location")))
    except Exception as e:
        failed.append((r, "err", str(e)[:40]))

print(f"added {len(added)} routes")
for a in added:
    print("  +", a)
print(f"unavailable {len(failed)}:")
for r, c, loc in failed:
    print("  -", r, c, loc or "")
json.dump({"added": added, "unavailable": failed}, open("link-audit.json", "w"), indent=2)
