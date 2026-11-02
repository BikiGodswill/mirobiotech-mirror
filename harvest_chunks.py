#!/usr/bin/env python3
"""Load pages in a real browser, capture every _next static asset requested,
download the missing ones, and repeat until a full pass finds nothing new."""
import asyncio, os, requests
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"
OUT = "site"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
sess = requests.Session()
sess.headers.update({"User-Agent": UA})

PAGES = ["/", "/products", "/products/bpc-157", "/products/glp-3-rt", "/products/glp-2-tz",
         "/categories", "/categories/blends", "/reviews", "/about", "/contact", "/checkout",
         "/track", "/legal", "/partners", "/careers", "/shipping", "/refund-policy",
         "/how-to-order", "/buy-peptides-with-upi", "/buy-peptides-in-india",
         "/buy-peptides-in-india/glp-3-rt", "/de", "/it", "/sv", "/de/produkte",
         "/de/produkte/glp-3-rt", "/de/rechtliches"]


async def harvest(round_no):
    missing = set()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1400, "height": 900})
        page = await ctx.new_page()
        seen = set()

        def on_resp(r):
            u = r.url.split("?")[0]
            if u.startswith(BASE + "/_next/static/") and r.status >= 400:
                seen.add(u[len(BASE):])

        page.on("response", on_resp)
        for path in PAGES:
            try:
                await page.goto(BASE + path, wait_until="networkidle", timeout=45000)
            except Exception:
                pass
            await page.wait_for_timeout(1200)
            # scroll to trigger lazy chunks
            await page.mouse.wheel(0, 3000)
            await page.wait_for_timeout(500)
        await b.close()
    return seen


def download(paths):
    ok = 0
    for p in sorted(paths):
        r = sess.get("https://www.mirobiotech.com" + p, timeout=60)
        if r.status_code == 200:
            fp = os.path.join(OUT, p.lstrip("/"))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, "wb").write(r.content)
            ok += 1
        else:
            print("  cannot fetch", p, r.status_code)
    return ok


async def main():
    for rnd in range(1, 8):
        missing = await harvest(rnd)
        print(f"round {rnd}: {len(missing)} missing static files")
        if not missing:
            print("all static assets satisfied")
            break
        print("  downloading", download(missing))

asyncio.run(main())
