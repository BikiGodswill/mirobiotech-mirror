// Cloudflare Pages Function (runs for HTML routes only — see public/_routes.json).
// Purpose: Cloudflare's static handler 308-redirects extensionless paths to a
// trailing slash. The original site uses clean URLs with no trailing slash, so we
// resolve them directly from the asset binding and serve with a 200 — no redirect.
const HTML_HEADERS = {
  "content-type": "text/html; charset=utf-8",
  "cache-control": "no-cache",
};

export async function onRequest({ request, env, next }) {
  const url = new URL(request.url);
  const path = url.pathname;

  // Clean URL, no extension, no trailing slash -> try <path>/index.html
  if (path !== "/" && !path.endsWith("/") && !/\.[a-z0-9]+$/i.test(path)) {
    const asset = await env.ASSETS.fetch(
      new URL(`${path}/index.html`, url.origin).toString()
    );
    if (asset.ok) {
      return new Response(asset.body, { status: 200, headers: HTML_HEADERS });
    }
    // fall through to next() so genuinely missing paths still 404
  }

  // Trailing-slash variant: let the static handler serve it.
  const res = await next();

  // Make the site's own 404 page the fallback for unknown routes.
  if (res.status === 404) {
    const custom = await env.ASSETS.fetch(
      new URL("/404.html", url.origin).toString()
    );
    if (custom.ok) {
      return new Response(custom.body, { status: 404, headers: HTML_HEADERS });
    }
  }
  return res;
}
