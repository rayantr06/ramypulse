import assert from "node:assert/strict";
import test from "node:test";

import {
  buildTenantHeaders,
  getStoredTenantId,
  setStoredTenantId,
} from "../client/src/lib/tenantContext";

function installWindowWithLocalStorage(storage: Storage) {
  const originalWindow = globalThis.window;
  const fakeWindow = {
    localStorage: storage,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  } as unknown as Window;

  Object.defineProperty(globalThis, "window", {
    value: fakeWindow,
    configurable: true,
    writable: true,
  });

  return () => {
    if (originalWindow === undefined) {
      delete (globalThis as typeof globalThis & { window?: Window }).window;
      return;
    }

    Object.defineProperty(globalThis, "window", {
      value: originalWindow,
      configurable: true,
      writable: true,
    });
  };
}

function createMemoryStorage(initialValue: string | null = null): Storage {
  let value = initialValue;

  return {
    getItem: () => value,
    setItem: (_key: string, nextValue: string) => {
      value = nextValue;
    },
    removeItem: () => {
      value = null;
    },
    clear: () => {
      value = null;
    },
    key: () => null,
    get length() {
      return value == null ? 0 : 1;
    },
  } as Storage;
}

test("buildTenantHeaders attaches X-Ramy-Client-Id when tenant exists", () => {
  assert.deepEqual(buildTenantHeaders("ramy_client_001"), {
    "X-Ramy-Client-Id": "ramy_client_001",
  });
  assert.deepEqual(buildTenantHeaders(null), {});
});

test("getStoredTenantId reads from window.localStorage and falls back to null when empty", () => {
  const storage = createMemoryStorage();
  const restoreWindow = installWindowWithLocalStorage(storage);

  try {
    assert.equal(getStoredTenantId(), null);
    storage.setItem("ignored", "ramy_client_001");
    storage.removeItem("ignored");
    assert.equal(getStoredTenantId(), null);
  } finally {
    restoreWindow();
  }
});

test("setStoredTenantId(null) removes the stored tenant", () => {
  const storage = createMemoryStorage("ramy_client_001");
  const restoreWindow = installWindowWithLocalStorage(storage);

  try {
    assert.equal(getStoredTenantId(), "ramy_client_001");
    setStoredTenantId(null);
    assert.equal(getStoredTenantId(), null);
    assert.equal(storage.length, 0);
  } finally {
    restoreWindow();
  }
});
