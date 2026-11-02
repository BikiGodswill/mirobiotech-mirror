#!/usr/bin/env python3
"""Download every _next/static/chunks/*.js referenced by any mirrored page."""
import os, re, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://www.mirobiotech.com"
OUT = "site"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
sess = requests.Session()
sess.headers.update({"User-Agent": UA})

CHUNK_RE = re.compile(r'/_next/static/chunks/[A-Za-z0-9._~-]+\.js')

wanted = set()
for root, _, files in os.walk(OUT):
    for f in files:
        if not f.endswith((".html", ".js")):
            continue
        t = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
        t = t.replace("\\/", "/")
        wanted |= set(CHUNK_RE.findall(t))

print("chunks referenced:", len(wanted))
have = set()
missing = []
for p in wanted:
    fp = os.path.join(OUT, p.lstrip("/"))
    if os.path.isfile(fp) and os.path.getsize(fp) > 0:
        have.add(p)
    else:
        missing.append(p)
print("present:", len(have), "missing:", len(missing))

def grab(p):
    r = sess.get(BASE + p, timeout=60)
    if r.status_code != 200:
        return (p, f"http{r.status_code}")
    fp = os.path.join(OUT, p.lstrip("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "wb").write(r.content)
    return (p, "ok")

fails = []
with ThreadPoolExecutor(max_workers=6) as ex:
    for f in as_completed([ex.submit(grab, p) for p in missing]):
        p, st = f.result()
        if st != "ok":
            fails.append((p, st))
print("downloaded:", len(missing) - len(fails), "failed:", len(fails))
for p, s in fails:
    print("  FAIL", p, s)
