#!/usr/bin/env python3
"""Retry failed pages sequentially with backoff (rate-limit safe)."""
import json, os, time, requests
from crawl import path_for, mkdirp, BASE, UA

sess = requests.Session()
sess.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})

rep = json.load(open("crawl-report.json"))
fails = [u for u, s in rep["pages_failed"]]
print(f"retrying {len(fails)}")

still = []
for i, u in enumerate(fails, 1):
    ok = False
    for attempt in range(4):
        try:
            r = sess.get(u, timeout=60)
            if r.status_code == 200 and len(r.content) > 5000:
                dest = path_for(u)
                mkdirp(dest)
                open(dest, "wb").write(r.content)
                ok = True
                print(f"  {i}/{len(fails)} ok  {u} ({len(r.content)}b)")
                break
            code = r.status_code
        except Exception as e:
            code = str(e)[:40]
        time.sleep(2 + attempt * 3)
    if not ok:
        still.append((u, code))
        print(f"  {i}/{len(fails)} FAIL {u} -> {code}")
    time.sleep(1.2)

print("STILL FAILING:", still)
rep["pages_failed"] = still
json.dump(rep, open("crawl-report.json", "w"), indent=2)
