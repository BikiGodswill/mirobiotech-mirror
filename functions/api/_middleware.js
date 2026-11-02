// Cloudflare Pages Function: JSON API shims for the mirror.
// Data captured from the live site; checkout endpoints are stubbed.
const STATIC = {
  "/api/exchange-rate": "exchange-rate.json",
  "/api/geo": "geo.json",
  "/api/payment-methods": "payment-methods.json",
  "/api/crypto/currencies": "crypto_currencies.json",
};

const CHECKOUT_PATHS = [
  "/api/checkout",
  "/api/pay",
  "/api/pay-started",
  "/api/cart-capture",
  "/api/crypto/pay",
  "/api/public/v1/payments/continue",
];

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-cache",
    },
  });

export async function onRequest({ request, env, next }) {
  const { pathname } = new URL(request.url);
  const path = pathname.replace(/\/$/, "") || "/api";

  // Analytics beacon: accept and discard so the app never logs an error.
  if (path === "/api/meta/track") return json({ ok: true });

  // Non-fatal crypto quote stub.
  if (path === "/api/crypto/quote") {
    return json({
      amount: "0.00000000",
      currency: "btc",
      rate: 0,
      expiresAt: null,
      stub: true,
    });
  }

  // Payments are intentionally disabled in this mirror.
  if (CHECKOUT_PATHS.includes(path)) {
    return json(
      {
        error: "static_mirror",
        message: "Checkout is disabled in this static mirror.",
      },
      501
    );
  }

  // Canned data, read straight off the CDN from /_api-data/.
  const file = STATIC[path];
  if (file) {
    const asset = await env.ASSETS.fetch(new URL(`/_api-data/${file}`, request.url));
    return new Response(asset.body, {
      status: asset.ok ? 200 : 500,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, max-age=300",
      },
    });
  }

  return json({ error: "not_found" }, 404);
}
