#!/usr/bin/env python3
"""Collect and download every asset path referenced by the mirrored HTML/CSS/JS."""
import os, re, sys, requests
from urllib.parse import unquote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://www.mirobiotech.com"
OUT = "site"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
sess = requests.Session()
sess.headers.update({"User-Agent": UA})

# matches /images/foo.webp  /press-logos/x.webp  /images/foo.webp?x  and escaped \\/
ASSET_RE = re.compile(r'(?:^|["\'(\s\\])(/(?:images|press-logos|fonts|_next/static|icons)/[A-Za-z0-9._~%/-]+\.(?:webp|png|jpg|jpeg|svg|avif|gif|ico|woff2?|ttf|otf|css|js))',
                      re.M)
NEXTIMG_RE = re.compile(r'/_next/image\?url=([^&"\'\\\s]+)')

found = set()
nextimg = set()

for rootdir, _, files in os.walk(OUT):
    for fn in files:
        p = os.path.join(rootdir, fn)
        if not fn.endswith((".html", ".css", ".js")):
            continue
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        # normalise escaped slashes from RSC payloads
        txt = txt.replace("\\\\/", "/").replace("\\/", "/")
        found |= set(ASSET_RE.findall(txt))
        nextimg |= {unquote(u) for u in NEXTIMG_RE.findall(txt)}

# /_next/image?url=%2Fimages%2Fx.webp  -> underlying real path
found |= {u for u in nextimg if u.startswith("/")}
print(f"unique asset refs: {len(found)}")

def dest_of(path):
    return os.path.join(OUT, unquote(path).lstrip("/"))

todo = [p for p in sorted(found) if not (os.path.exists(dest_of(p)) and os.path.getsize(dest_of(p)) > 0)]
print(f"need download: {len(todo)}")

def grab(path):
    url = BASE + path
    d = dest_of(path)
    try:
        r = sess.get(url, timeout=60)
        if r.status_code != 200 or len(r.content) == 0:
            return (path, f"http{r.status_code}")
        os.makedirs(os.path.dirname(d), exist_ok=True)
        open(d, "wb").write(r.content)
        return (path, "ok")
    except Exception as e:
        return (path, str(e)[:50])

fails = []
with ThreadPoolExecutor(max_workers=8) as ex:
    for f in as_completed([ex.submit(grab, p) for p in todo]):
        path, st = f.result()
        if st != "ok":
            fails.append((path, st))

print(f"downloaded {len(todo)-len(fails)}, failed {len(fails)}")
for p, s in fails[:40]:
    print("  FAIL", p, s)

total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT) for f in fs)
print(f"site size: {total/1e6:.1f} MB")
