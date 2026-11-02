# Miro Biotech — Full Site Mirror

A complete, working local clone of **https://www.mirobiotech.com** — every page, all four
languages, all assets, with the interactive front-end (cart, currency, search, language
switching, age gate) live and working.

Captured: **2026-10-25**

---

## Quick start

```bash
./run-local.sh              # or: python3 serve.py  /  node serve.mjs
```

Then open **http://localhost:8000**

Deploying to Cloudflare Pages (CLI, Git, or drag-and-drop) is covered in **DEPLOY.md**.

> Use `serve.py` / `serve.mjs`, not `python3 -m http.server`. The mirror uses Next.js-style clean URLs
> (`/products/bpc-157` → `products/bpc-157/index.html`), and the plain module won't resolve
> those, or the `/_next/image` optimizer or `/api/*` endpoints.

Optional: `PORT=9000 python3 serve.py`

---

## What's included

| | Count |
|---|---|
| Pages mirrored | **238** |
| Languages | **4** — English, German (`/de`), Italian (`/it`), Swedish (`/sv`) |
| Product pages | 31 × 4 locales |
| Category pages | 6 × 4 locales |
| JS chunks + CSS + fonts | 45 files |
| Images / press logos / icons | 55 files |
| Total size | **68 MB** |

### Page coverage
- **Home** — hero, stats, featured products, blends, categories, "why Miro", reviews carousel, FAQ
- **Catalog** — `/products`, `/categories` + 6 category pages, 31 product detail pages
- **Trust/policy** — `/about`, `/reviews` (706 reviews), `/partners`, `/careers`,
  `/shipping`, `/refund-policy`, `/legal` (terms / privacy / disclaimer), `/how-to-order`
- **Commerce** — `/checkout` (full multi-step form), `/track`, `/buy-peptides-with-upi`,
  `/buy-peptides-with-cryptocurrency`, `/buy-peptides-in-india` + 31 country/product pages
- **Localized commerce** — `/de/kasse`, `/it/cassa`, `/sv/kassa`, plus translated
  tracking routes (`/de/sendungsverfolgung`, `/it/traccia-ordine`, `/sv/sparning`)
- **404** — the site's own not-found page (`site/404.html`)

See `pages.json` for the full route → title index.

---

## What works

Everything that runs client-side, because the original JavaScript is intact and hydrated:

- ✅ Age gate (21+) with persistence
- ✅ Language switcher — actually navigates to the correct translated route
- ✅ Currency switcher with live rates (served from `api-cache/exchange-rate.json`)
- ✅ Cart add / remove / quantity / volume-discount progress (persists in `localStorage`)
- ✅ Cart drawer, checkout page rendering with your cart contents
- ✅ Search overlay (⌘K), product variant selection, related products, mobile menu
- ✅ Internal navigation via Next.js client router — no full page reloads
- ✅ Fully responsive (desktop / tablet / mobile verified)

## What's intentionally limited

- **Order submission is disabled.** `/api/checkout`, `/api/pay`, `/api/crypto/pay` etc.
  return a `501 "Checkout is disabled in this offline mirror."` stub instead of charging a
  card. Every step up to that point works. Edit `_api()` in `serve.py` if you want them to
  behave differently.
- **The 12 `/de|/it|/sv` variants of `buy-peptides-with-upi` / `-cryptocurrency` don't exist
  upstream** (they 404 on the live site too) — omitted rather than invented.
- **Analytics is neutralised** — Google Tag Manager and Meta Pixel were repointed to a local
  no-op script, so the mirror doesn't phone home or skew the real site's data.
- **Third-party links still point outward** (PubMed, Wikipedia, press articles, WhatsApp,
  Telegram) — those are outbound references, not site pages.

---

## Layout

```
serve.py              local web server, Python (clean URLs, /_next/image, /api shims)
serve.mjs             local web server, Node (same behaviour, zero deps)
run-local.sh          auto-detects python3 or node
DEPLOY.md             running locally + Cloudflare Pages deployment guide
wrangler.toml         Cloudflare config (output dir: site/)
functions/            Cloudflare Pages Functions (clean URLs, image shim, API shims)
crawl.py              sitemap crawl of all 230 URLs
retry.py              sequential retry for rate-limited pages
fix_locales.py        verifies each page's <html lang> matches its URL locale
assets.py             downloads every referenced image/font/icon
chunks.py             downloads statically referenced JS/CSS chunks
harvest_chunks.py     browser-driven discovery of lazy-loaded route chunks
link_audit.py         finds internal links with no page on disk
postprocess.py        adds robots-excluded routes, strips trackers
pages.json            route + title index of all 238 pages
shots/                verification screenshots
site/                 ← the mirror itself
```

To re-capture from scratch: `python3 crawl.py && python3 retry.py && python3 assets.py &&
python3 chunks.py && python3 fix_locales.py && python3 link_audit.py`

---

## Note on content

This is an offline snapshot of a commercial vendor site, reproduced for reference/development
purposes, not as a live storefront. Product page images carry the original vendor's labels
and claims, and every page carries its own "for laboratory research use only" notice — those
are the site's statements, not endorsements.

**MiroBiotech** is a trademark of its owner; this mirror is not affiliated with or endorsed by
them.
