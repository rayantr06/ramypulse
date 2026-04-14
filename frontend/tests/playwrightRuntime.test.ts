import assert from "node:assert/strict";
import test from "node:test";

import { buildPlaywrightRuntimeConfig } from "../playwright.runtime";

test("buildPlaywrightRuntimeConfig uses the default preview server when no base URL override is set", () => {
  const runtime = buildPlaywrightRuntimeConfig({});

  assert.equal(runtime.baseURL, "http://127.0.0.1:4173");
  assert.equal(runtime.webServer?.port, 4173);
  assert.match(runtime.webServer?.command ?? "", /npm run preview/);
});

test("buildPlaywrightRuntimeConfig disables the preview webServer when an external base URL is provided", () => {
  const runtime = buildPlaywrightRuntimeConfig({
    PLAYWRIGHT_BASE_URL: "http://127.0.0.1:4319",
  });

  assert.equal(runtime.baseURL, "http://127.0.0.1:4319");
  assert.equal(runtime.webServer, undefined);
});
