import assert from "node:assert/strict";
import test from "node:test";

import handler, { __testables } from "../api/[...path].js";

function createResponse() {
  return {
    body: null,
    headers: new Map(),
    statusCode: 200,
    json(payload) {
      this.body = payload;
      return this;
    },
    send(payload) {
      this.body = payload;
      return this;
    },
    setHeader(name, value) {
      this.headers.set(name.toLowerCase(), value);
    },
    status(statusCode) {
      this.statusCode = statusCode;
      return this;
    },
  };
}

test("the API proxy preserves path and query parameters", () => {
  const target = __testables.buildUpstreamUrl(
    {
      query: { path: ["watchlists"], is_active: "true" },
      url: "/api/watchlists?is_active=true",
    },
    "https://backend.example/",
  );

  assert.equal(target.toString(), "https://backend.example/api/watchlists?is_active=true");
});

test("the API proxy injects its server-side key", async () => {
  const previousBackendUrl = process.env.RAMYPULSE_BACKEND_URL;
  const previousBackendKey = process.env.RAMYPULSE_BACKEND_API_KEY;
  const previousFetch = globalThis.fetch;
  process.env.RAMYPULSE_BACKEND_URL = "https://backend.example";
  process.env.RAMYPULSE_BACKEND_API_KEY = "server-only-key";

  globalThis.fetch = async (url, init) => {
    assert.equal(String(url), "https://backend.example/api/watchlists?is_active=true");
    assert.equal(init.headers.get("x-api-key"), "server-only-key");
    assert.equal(init.headers.get("x-ramy-client-id"), "ramy_client_001");
    return new Response(JSON.stringify([{ watchlist_id: "watch-1" }]), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const response = createResponse();
    await handler(
      {
        body: null,
        headers: { "x-ramy-client-id": "ramy_client_001" },
        method: "GET",
        query: { path: ["watchlists"], is_active: "true" },
        url: "/api/watchlists?is_active=true",
      },
      response,
    );

    assert.equal(response.statusCode, 200);
    assert.equal(response.headers.get("content-type"), "application/json");
    assert.deepEqual(JSON.parse(response.body.toString("utf8")), [
      { watchlist_id: "watch-1" },
    ]);
  } finally {
    globalThis.fetch = previousFetch;
    process.env.RAMYPULSE_BACKEND_URL = previousBackendUrl;
    process.env.RAMYPULSE_BACKEND_API_KEY = previousBackendKey;
  }
});

test("the API proxy fails safely when deployment secrets are missing", async () => {
  const previousBackendUrl = process.env.RAMYPULSE_BACKEND_URL;
  const previousBackendKey = process.env.RAMYPULSE_BACKEND_API_KEY;
  delete process.env.RAMYPULSE_BACKEND_URL;
  delete process.env.RAMYPULSE_BACKEND_API_KEY;

  try {
    const response = createResponse();
    await handler(
      { headers: {}, method: "GET", query: { path: ["health"] }, url: "/api/health" },
      response,
    );

    assert.equal(response.statusCode, 503);
    assert.match(response.body.detail, /pas encore configuré/);
  } finally {
    process.env.RAMYPULSE_BACKEND_URL = previousBackendUrl;
    process.env.RAMYPULSE_BACKEND_API_KEY = previousBackendKey;
  }
});
