// Cloudflare Pages Function: stands in for Next.js's /_next/image optimizer.
// We only have full-size originals, so serve the underlying file directly.
export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  const target = url.searchParams.get("url");

  if (!target || !target.startsWith("/")) {
    return new Response(JSON.stringify({ error: "missing url param" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }

  // Resolve against this deployment and let the asset binding fetch it.
  const assetUrl = new URL(target, url.origin).toString();
  const asset = await env.ASSETS.fetch(assetUrl);

  if (!asset.ok) return new Response("Not found", { status: 404 });

  const headers = new Headers(asset.headers);
  headers.set("Cache-Control", "public, max-age=31536000, immutable");
  headers.set("X-Mirror", "next-image-shim");
  return new Response(asset.body, { status: 200, headers });
}
