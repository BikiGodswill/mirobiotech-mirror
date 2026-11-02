#!/usr/bin/env node
/**
 * Zero-dependency Node server for the Miro Biotech mirror.
 * Equivalent to serve.py — use whichever runtime you have.
 *
 *   node serve.mjs            # http://localhost:8000
 *   PORT=9000 node serve.mjs
 */
import { createServer } from "node:http";
import { stat, readFile } from "node:fs/promises";
import { join, extname, normalize, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "site");
const API = join(dirname(fileURLToPath(import.meta.url)), "api-cache");
const PORT = Number(process.env.PORT || 8000);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json",
  ".webp": "image/webp",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
};

const API_FILES = {
  "/api/exchange-rate": "exchange-rate.json",
  "/api/geo": "geo.json",
  "/api/payment-methods": "payment-methods.json",
  "/api/crypto/currencies": "crypto_currencies.json",
};

const send = (res, status, body, type) => {
  res.writeHead(status, {
    "Content-Type": type || "application/octet-stream",
    "Content-Length": Buffer.byteLength(body),
    "Cache-Control": "no-cache",
  });
  res.end(body);
};
const json = (res, obj, status = 200) =>
  send(res, status, JSON.stringify(obj), "application/json; charset=utf-8");

async function isFile(p) {
  try {
    return (await stat(p)).isFile();
  } catch {
    return false;
  }
}

/** Map a URL path to a file on disk, mirroring Next.js clean URLs. */
async function resolve(pathname) {
  const clean = normalize(decodeURIComponent(pathname)).replace(/^(\.\.[/\\])+/, "");
  const base = join(ROOT, clean);

  if (await isFile(base)) return base;
  if (await isFile(join(base, "index.html"))) return join(base, "index.html");
  for (const ext of [".ico", ".png", ".webp", ".svg"]) {
    if (await isFile(base + ext)) return base + ext;
  }
  if (pathname === "/") return join(ROOT, "index.html");
  return null;
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  let path = url.pathname;

  // drain request body for POSTs so the socket doesn't hang
  if (req.method === "POST") req.resume();

  // --- API shims ---
  if (path.startsWith("/api/")) {
    const p = path.replace(/\/$/, "");
    if (p === "/api/meta/track") return json(res, { ok: true });
    if (p === "/api/crypto/quote")
      return json(res, {
        amount: "0.00000000",
        currency: "btc",
        rate: 0,
        expiresAt: null,
        stub: true,
      });
    const disabled = [
      "/api/checkout",
      "/api/pay",
      "/api/pay-started",
      "/api/cart-capture",
      "/api/crypto/pay",
      "/api/public/v1/payments/continue",
    ];
    if (disabled.includes(p))
      return json(
        res,
        {
          error: "static_mirror",
          message: "Checkout is disabled in this static mirror.",
        },
        501
      );
    const file = API_FILES[p];
    if (file) {
      try {
        return send(res, 200, await readFile(join(API, file)), "application/json; charset=utf-8");
      } catch {
        return json(res, { error: "not_found" }, 404);
      }
    }
    return json(res, { error: "not_found" }, 404);
  }

  // --- /_next/image optimizer emulation: return the full-size original ---
  if (path === "/_next/image") {
    const target = url.searchParams.get("url");
    if (!target || !target.startsWith("/")) return json(res, { error: "missing url" }, 400);
    const file = await resolve(target);
    if (!file) return send(res, 404, "Not found", "text/plain");
    const body = await readFile(file);
    return send(res, 200, body, MIME[extname(file).toLowerCase()]);
  }

  if (path === "/_mirror/health") return json(res, { ok: true });

  // --- static + clean URLs ---
  const file = await resolve(path);
  if (file) {
    const body = await readFile(file);
    const type = MIME[extname(file).toLowerCase()] || "application/octet-stream";
    const cache = file.includes("/_next/static/") || file.includes("/fonts/")
      ? "public, max-age=31536000, immutable"
      : "no-cache";
    res.writeHead(200, {
      "Content-Type": type,
      "Content-Length": body.length,
      "Cache-Control": cache,
    });
    return res.end(req.method === "HEAD" ? undefined : body);
  }

  // --- 404: serve the site's own page ---
  if (await isFile(join(ROOT, "404.html"))) {
    const body = await readFile(join(ROOT, "404.html"));
    return send(res, 404, body, MIME[".html"]);
  }
  send(res, 404, "Not found", "text/plain");
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`mirror serving ${ROOT}`);
  console.log(`  http://localhost:${PORT}`);
});
