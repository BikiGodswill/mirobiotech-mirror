import asyncio, json
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 1000})
        page = await ctx.new_page()
        errs, failed = [], []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("requestfailed", lambda r: failed.append(r.url[:110]))
        page.on("response", lambda r: failed.append(f"{r.status} {r.url[:100]}") if r.status >= 400 else None)

        await page.goto(BASE + "/", wait_until="networkidle")
        await page.screenshot(path="shots/01-home-full.png", full_page=True)
        await page.screenshot(path="shots/02-home-top.png")

        # age gate present?
        gate = await page.locator("text=Are you 21 or older?").count()
        print("age gate nodes:", gate)
        if gate:
            await page.get_by_text("I am 21 or older").first.click()
            await page.wait_for_timeout(800)
            await page.screenshot(path="shots/03-home-after-gate.png")

        # client-side nav test: click first product card link
        link = page.locator('a[href="/products/bpc-157"]').first
        print("product links:", await page.locator('a[href^="/products/"]').count())
        await link.click()
        await page.wait_for_timeout(2500)
        print("url after click:", page.url)
        print("h1:", (await page.locator("h1").first.inner_text())[:80] if await page.locator("h1").count() else "NONE")
        await page.screenshot(path="shots/04-after-client-nav.png")

        for path, name in [("/products", "05-products"), ("/categories", "06-categories"),
                           ("/reviews", "07-reviews"), ("/about", "08-about"),
                           ("/de", "09-de-home"), ("/legal", "10-legal")]:
            await page.goto(BASE + path, wait_until="networkidle")
            await page.wait_for_timeout(900)
            await page.screenshot(path=f"shots/{name}.png", full_page=True)

        print("console errors:", len(errs))
        for e in errs[:12]:
            print("  E:", e[:160])
        print("failed/4xx:", len(failed))
        for f in failed[:15]:
            print("  F:", f)
        await b.close()

asyncio.run(main())
