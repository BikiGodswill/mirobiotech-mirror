import asyncio, collections
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 1000}, locale="en-US")
        pg = await ctx.new_page()
        errs = collections.Counter()
        four = []
        pg.on("console", lambda m: errs.update([m.text[:120]]) if m.type == "error" else None)
        pg.on("response", lambda r: four.append(f"{r.status} {r.url[:90]}") if r.status >= 400 else None)

        await pg.goto(BASE + "/", wait_until="networkidle")
        await pg.get_by_text("I am 21 or older").first.click()
        await pg.wait_for_timeout(900)

        # 1. client-side nav within locale
        await pg.locator('a[href="/products/bpc-157"]').first.click()
        await pg.wait_for_timeout(2200)
        print("nav1 url:", pg.url, "| lang:", await pg.get_attribute("html", "lang"),
              "| h1:", (await pg.locator("h1").first.inner_text()).strip()[:40])
        await pg.screenshot(path="shots/11-product-en.png", full_page=False)

        # 2. language switcher -> German
        try:
            await pg.locator("button:has-text('English')").first.click()
            await pg.wait_for_timeout(700)
            await pg.screenshot(path="shots/12-lang-menu.png")
            await pg.get_by_text("Deutsch").first.click()
            await pg.wait_for_timeout(2500)
            print("nav2 (lang switch) url:", pg.url, "| lang:",
                  await pg.get_attribute("html", "lang"))
            await pg.screenshot(path="shots/13-product-de.png")
        except Exception as e:
            print("lang switch issue:", str(e)[:120])

        # 3. header nav + search overlay
        await pg.goto(BASE + "/products", wait_until="networkidle")
        await pg.wait_for_timeout(700)
        print("products page cards:", await pg.locator('a[href^="/products/"]').count())
        await pg.screenshot(path="shots/14-products.png", full_page=True)

        # 4. cart interaction
        await pg.goto(BASE + "/products/ghk-cu", wait_until="networkidle")
        await pg.wait_for_timeout(1200)
        try:
            await pg.get_by_role("button", name=lambda n: n and "Add to cart" in n or "Aggiungi" in n or "In den" in n).first.click()
            await pg.wait_for_timeout(1200)
            await pg.screenshot(path="shots/15-cart-added.png")
            print("cart localStorage:", (await pg.evaluate("localStorage.getItem('miro-cart')"))[:120])
        except Exception as e:
            print("cart test:", str(e)[:120])

        # 5. mobile viewport
        m = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                has_touch=True, locale="en-US")
        mp = await m.new_page()
        await mp.goto(BASE + "/", wait_until="networkidle")
        await mp.wait_for_timeout(800)
        await mp.screenshot(path="shots/16-mobile-home.png", full_page=False)
        await mp.goto(BASE + "/products/bpc-157", wait_until="networkidle")
        await mp.wait_for_timeout(1000)
        await mp.screenshot(path="shots/17-mobile-product.png", full_page=False)

        print("\nunique console errors:", len(errs))
        for k, v in errs.most_common(8):
            print(f"  x{v} {k}")
        print("\n4xx/5xx responses:", len(four))
        for f in collections.Counter(four).most_common(8):
            print("  x%d %s" % (f[1], f[0]))
        await b.close()

asyncio.run(main())
