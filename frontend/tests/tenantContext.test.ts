import assert from "node:assert/strict";
import test from "node:test";

import {
  buildTenantHeaders,
  getStoredTenantId,
} from "../client/src/lib/tenantContext";

test("buildTenantHeaders attaches X-Ramy-Client-Id when tenant exists", () => {
  assert.deepEqual(buildTenantHeaders("ramy_client_001"), {
    "X-Ramy-Client-Id": "ramy_client_001",
  });
  assert.deepEqual(buildTenantHeaders(null), {});
});

test("getStoredTenantId falls back to null when nothing is stored", () => {
  const originalLocalStorage = globalThis.localStorage;
  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {
      throw new Error("unexpected setItem");
    },
    removeItem: () => {
      throw new Error("unexpected removeItem");
    },
    clear: () => {
      throw new Error("unexpected clear");
    },
    key: () => null,
    length: 0,
  } as Storage;

  try {
    assert.equal(getStoredTenantId(), null);
  } finally {
    globalThis.localStorage = originalLocalStorage;
  }
});
