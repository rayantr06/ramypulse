import { useSyncExternalStore } from "react";

export interface ActiveOnboardingRun {
  clientId: string;
  runId: string;
  watchlistId: string;
  source: "smart" | "manual";
  lastKnownStatus?: string | null;
  lastKnownStage?: string | null;
}

const STORAGE_KEY = "ramypulse.activeOnboardingRun";
const ONBOARDING_RUN_CHANGE_EVENT = "ramypulse:onboarding-run-change";
let pendingOnboardingRun: ActiveOnboardingRun | null | undefined;
let cachedSerializedOnboardingRun: string | null | undefined;
let cachedOnboardingRun: ActiveOnboardingRun | null = null;

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function emitOnboardingRunChange() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(ONBOARDING_RUN_CHANGE_EVENT));
  }
}

function normalizeActiveOnboardingRun(value: unknown): ActiveOnboardingRun | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const clientId = typeof record.clientId === "string" ? record.clientId.trim() : "";
  const runId = typeof record.runId === "string" ? record.runId.trim() : "";
  const watchlistId = typeof record.watchlistId === "string" ? record.watchlistId.trim() : "";
  const source = record.source === "manual" ? "manual" : record.source === "smart" ? "smart" : null;

  if (!clientId || !runId || !watchlistId || !source) {
    return null;
  }

  return {
    clientId,
    runId,
    watchlistId,
    source,
    lastKnownStatus: typeof record.lastKnownStatus === "string" ? record.lastKnownStatus : null,
    lastKnownStage: typeof record.lastKnownStage === "string" ? record.lastKnownStage : null,
  };
}

export function getStoredOnboardingRun(): ActiveOnboardingRun | null {
  if (pendingOnboardingRun !== undefined) {
    return pendingOnboardingRun;
  }

  const storage = getStorage();
  if (!storage) {
    return null;
  }

  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) {
      cachedSerializedOnboardingRun = null;
      cachedOnboardingRun = null;
      return null;
    }

    if (raw === cachedSerializedOnboardingRun) {
      return cachedOnboardingRun;
    }

    cachedSerializedOnboardingRun = raw;
    cachedOnboardingRun = normalizeActiveOnboardingRun(JSON.parse(raw));
    return cachedOnboardingRun;
  } catch {
    cachedSerializedOnboardingRun = null;
    cachedOnboardingRun = null;
    return null;
  }
}

export function setStoredOnboardingRun(run: ActiveOnboardingRun | null): void {
  pendingOnboardingRun = run ? normalizeActiveOnboardingRun(run) : null;
  const storage = getStorage();
  if (!storage) {
    emitOnboardingRunChange();
    return;
  }

  try {
    if (pendingOnboardingRun) {
      cachedSerializedOnboardingRun = JSON.stringify(pendingOnboardingRun);
      cachedOnboardingRun = pendingOnboardingRun;
      storage.setItem(STORAGE_KEY, cachedSerializedOnboardingRun);
    } else {
      cachedSerializedOnboardingRun = null;
      cachedOnboardingRun = null;
      storage.removeItem(STORAGE_KEY);
    }
    pendingOnboardingRun = undefined;
  } catch {
    // Best-effort persistence. Keep the in-memory value to preserve UI continuity.
  }

  emitOnboardingRunChange();
}

export function patchStoredOnboardingRun(patch: Partial<ActiveOnboardingRun>): void {
  const current = getStoredOnboardingRun();
  if (!current) {
    return;
  }

  setStoredOnboardingRun({
    ...current,
    ...patch,
  });
}

function subscribeOnboardingRunChanges(onStoreChange: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handler = () => onStoreChange();
  window.addEventListener(ONBOARDING_RUN_CHANGE_EVENT, handler);
  window.addEventListener("storage", handler);

  return () => {
    window.removeEventListener(ONBOARDING_RUN_CHANGE_EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}

export function useStoredOnboardingRun(): ActiveOnboardingRun | null {
  return useSyncExternalStore(subscribeOnboardingRunChanges, getStoredOnboardingRun, () => null);
}
