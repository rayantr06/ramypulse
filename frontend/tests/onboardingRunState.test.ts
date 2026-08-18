import assert from "node:assert/strict";
import test from "node:test";

import {
  getStoredOnboardingRun,
  patchStoredOnboardingRun,
  setStoredOnboardingRun,
} from "../client/src/lib/onboardingRunState";

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

test("setStoredOnboardingRun persists the active run payload", () => {
  const storage = createMemoryStorage();
  const restoreWindow = installWindowWithLocalStorage(storage);

  try {
    setStoredOnboardingRun({
      clientId: "ifri",
      runId: "run-001",
      watchlistId: "watch-001",
      source: "smart",
    });

    assert.deepEqual(getStoredOnboardingRun(), {
      clientId: "ifri",
      runId: "run-001",
      watchlistId: "watch-001",
      source: "smart",
      lastKnownStatus: null,
      lastKnownStage: null,
    });
  } finally {
    restoreWindow();
    setStoredOnboardingRun(null);
  }
});

test("patchStoredOnboardingRun updates the run status without losing identity", () => {
  const storage = createMemoryStorage();
  const restoreWindow = installWindowWithLocalStorage(storage);

  try {
    setStoredOnboardingRun({
      clientId: "ifri",
      runId: "run-001",
      watchlistId: "watch-001",
      source: "manual",
    });

    patchStoredOnboardingRun({
      lastKnownStatus: "error",
      lastKnownStage: "normalizing",
    });

    assert.deepEqual(getStoredOnboardingRun(), {
      clientId: "ifri",
      runId: "run-001",
      watchlistId: "watch-001",
      source: "manual",
      lastKnownStatus: "error",
      lastKnownStage: "normalizing",
    });
  } finally {
    restoreWindow();
    setStoredOnboardingRun(null);
  }
});

test("getStoredOnboardingRun keeps a stable snapshot reference while storage is unchanged", () => {
  const storage = createMemoryStorage();
  const restoreWindow = installWindowWithLocalStorage(storage);

  try {
    setStoredOnboardingRun({
      clientId: "ifri",
      runId: "run-001",
      watchlistId: "watch-001",
      source: "smart",
    });

    const firstSnapshot = getStoredOnboardingRun();
    const secondSnapshot = getStoredOnboardingRun();

    assert.equal(firstSnapshot, secondSnapshot);
  } finally {
    restoreWindow();
    setStoredOnboardingRun(null);
  }
});

test("setStoredOnboardingRun(null) clears the persisted run", () => {
  const storage = createMemoryStorage();
  const restoreWindow = installWindowWithLocalStorage(storage);

  try {
    setStoredOnboardingRun({
      clientId: "ifri",
      runId: "run-001",
      watchlistId: "watch-001",
      source: "smart",
    });
    setStoredOnboardingRun(null);

    assert.equal(getStoredOnboardingRun(), null);
    assert.equal(storage.length, 0);
  } finally {
    restoreWindow();
    setStoredOnboardingRun(null);
  }
});
