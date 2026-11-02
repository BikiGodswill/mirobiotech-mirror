# Running & Deploying the Miro Biotech Mirror

Two things you asked: **can I download and run it on my computer** — yes. **Can I host it on
Cloudflare Workers/Pages** — yes, and the repo is already wired for it.

---

## 1. Download

The project is one folder in this workspace. Grab it however your client works — the whole
thing is **~68 MB, 349 files**, dominated by images and JS chunks.

If you're comfortable with a terminal, a zip is the easiest artifact:

```bash
cd /home/user
zip -r mirobiotech-mirror.zip . -x 'node_modules/*' '.wrangler/*' '__pycache__/*' 'shots/*' '.cache/*' '.npm/*' '.config/*'
```

That excludes the dev-only folders, so the archive is essentially just `site/` plus the
server files and functions.

### What's in the folder

```
site/                 ← the mirror itself (238 pages, all assets)
  index.html          ← home
  products/…          ← 31 product pages, each in its own folder
  de/ it/ sv/         ← 151 localized pages
  _next/static/…      ← JS chunks, CSS, fonts
  images/ press-logos/
  _api-data/          ← canned JSON the API shims read
  _routes.json        ← tells Cloudflare which paths hit Functions

serve.py              local server (Python, no dependencies)
serve.mjs             local server (Node, no dependencies)
functions/            Cloudflare Pages Functions
  _middleware.js        clean-URL handling + custom 404
  _next/image.js        Next image optimizer stand-in
  api/_middleware.js    JSON API shims
wrangler.toml         Cloudflare config (already points at site/)
package.json
run-local.sh          one-liner launcher
pages.json            route + title index of all 238 pages
```

---

## 2. Run it locally

You need **either Python 3 or Node 16+**. No pip installs, no npm installs.

```bash
./run-local.sh                 # auto-picks python3 or node
```

or explicitly:

```bash
python3 serve.py               # http://localhost:8000
node serve.mjs                 # http://localhost:8000
PORT=9000 node serve.mjs       # different port
```

Then open **http://localhost:8000**.

> **Don't use `python3 -m http.server`.** The mirror uses extensionless URLs
> (`/products/bpc-157` maps to `products/bpc-157/index.html`). The stock module won't resolve
> those, won't serve `/_next/image`, and won't answer `/api/*`.

### Trying the Cloudflare build locally

```bash
npm install                    # installs wrangler (dev-only)
npm run dev                    # http://localhost:8788
```

This runs the *actual* Workers runtime, so it's the truest pre-deploy test. It's slower than
the plain servers on a low-spec machine — expect a few hundred ms per request instead of
single-digit ms.

---

## 3. Deploy to Cloudflare Pages

### Option A — CLI (fastest)

```bash
npm install
npx wrangler login
npx wrangler pages deploy
```

First run asks you to name the project; it'll give you
`https://<project-name>.pages.dev`.

If it complains the project doesn't exist, create it once:

```bash
npx wrangler pages project create mirobiotech-mirror
npx wrangler pages deploy
```

### Option B — Git integration

1. Push this folder to GitHub/GitLab.
2. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
3. Build settings:
   - **Framework preset:** `None`
   - **Build command:** *(leave empty)*
   - **Build output directory:** `site`
4. Save and deploy.

`wrangler.toml` already sets `pages_build_output_dir = "site"`, so the CLI and the dashboard
agree on the same output folder.

### Option C — drag & drop

Dashboard → Workers & Pages → Create → Pages → **Upload assets** → drag the `site` folder in.
Quick, but **Functions won't run** this way (drag-and-drop is static-only), so `/_next/image`
and `/api/*` will 404. The pages themselves still render. Use A or B if you want full parity.

---

## How the Cloudflare pieces work

| Path | Handled by | What it does |
|---|---|---|
| `/products/bpc-157` | `functions/_middleware.js` | Serves `products/bpc-157/index.html` with a `200` and **no trailing-slash redirect** — Cloudflare's static handler would otherwise 308 to `/products/bpc-157/` |
| unknown paths | `functions/_middleware.js` | Returns the site's own 404 page with a real `404` status |
| `/_next/image?url=…&w=…` | `functions/_next/image.js` | Fetches the original from the asset binding. We only kept full-size originals, so the `w=`/`q=` params are ignored — visually identical, slightly heavier |
| `/api/exchange-rate`, `/geo`, `/payment-methods`, `/crypto/currencies` | `functions/api/_middleware.js` | Serves captured JSON from `/_api-data/` |
| `/api/meta/track` | same | Returns `{ok:true}` so the analytics beacon never errors |
| `/api/checkout`, `/api/pay`, … | same | `501` — checkout is deliberately disabled |
| `/_next/static/*`, `/images/*` | Cloudflare CDN | Served straight from the edge, bypassing Functions via `_routes.json` |

`site/_routes.json` is what keeps Functions off the hot asset paths, so images and JS chunks
are pure CDN hits and don't burn Worker invocations.

---

## Cloudflare limits — you have plenty of headroom

| Limit | Free plan | This project |
|---|---|---|
| Files per deployment | 20,000 | **349** |
| Max single file | 25 MiB | **0.6 MiB** |
| Total deployment size | 20,000 files / no hard byte cap on Pages | **68 MB** |
| Functions invocations | 100,000/day | only HTML routes + API |

Per Cloudflare's docs, Pages projects are capped at 20,000 files and 25 MiB per file; you can
raise it by request if you ever exceed it. You're using ~2% of the file budget.

---

## Optional: make it feel faster

The mirror works as-is, but three cheap wins if you're hosting it for real:

1. **Compress HTML.** Cloudflare auto-Brotli/gzips on the way out, but the originals on disk
   are uncompressed (~300 KB of HTML per page). Nothing to do — just don't disable it.
2. **Cache headers.** The mirror sets `immutable` on `/_next/static/*` automatically
   (hashed filenames, safe forever). Everything else is `no-cache`, which is correct for HTML.
3. **Add a `_headers` file** in `site/` if you want to pin a CSP or cache policy. Not required.

To gate access to just yourself, Cloudflare **Access** (Zero Trust) in front of the Pages
project is the cleanest option — free for up to 50 users.

---

## Known limitations

- **Checkout can't complete.** It renders, validates, and totals correctly right up to the
  payment call, which returns a stub. Wiring it to a real processor means implementing the
  endpoints in `functions/api/_middleware.js` — that's your code to write, not a mirror fix.
- **Exchange rates are frozen** at capture time (Feb 2026 values). Swap in a live fetch in the
  same function if you want current rates.
- **No `sitemap.xml` / `robots.txt`** in the mirror. If you deploy publicly, add your own or
  you'll be serving the real site's SEO surface from a different domain — which is a bad idea
  for reasons below.
- **Search is client-side only** and indexes the pages you have. No server search.

---

## Before you make it public

Hosting this privately (local, or behind Access) is fine. Publishing it on a public URL is a
different matter: the content, product photography, brand marks, and customer reviews belong
to Miro Biotech, and every page carries their trademark. A public clone that could be mistaken
for the real storefront — especially one that accepts payment details — invites trademark and
copyright complaints, and possibly consumer-protection trouble if someone tries to order.

If you need something public-facing, the safer route is a design reference: keep the layout
and structure, replace the brand assets, product copy, and imagery with your own.
