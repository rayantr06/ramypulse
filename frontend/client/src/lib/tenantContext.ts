import { useSyncExternalStore } from "react";

export const STORAGE_KEY = "ramypulse.activeTenantId";
const TENANT_CHANGE_EVENT = "ramypulse:tenant-change";

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

function emitTenantChange() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(TENANT_CHANGE_EVENT));
  }
}

export function getStoredTenantId(): string | null {
  const storage = getStorage();
  if (!storage) {
    return null;
  }

  const value = storage.getItem(STORAGE_KEY);
  return value && value.trim() ? value : null;
}

export function setStoredTenantId(clientId: string | null): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }

  const trimmedClientId = clientId?.trim() || null;
  if (trimmedClientId) {
    storage.setItem(STORAGE_KEY, trimmedClientId);
  } else {
    storage.removeItem(STORAGE_KEY);
  }

  emitTenantChange();
}

export function buildTenantHeaders(clientId: string | null | undefined): Record<string, string> {
  if (!clientId) {
    return {};
  }

  return {
    "X-Ramy-Client-Id": clientId,
  };
}

function subscribeTenantChanges(onStoreChange: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handler = () => onStoreChange();
  window.addEventListener(TENANT_CHANGE_EVENT, handler);
  window.addEventListener("storage", handler);

  return () => {
    window.removeEventListener(TENANT_CHANGE_EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}

export function useTenantId(): string | null {
  return useSyncExternalStore(subscribeTenantChanges, getStoredTenantId, () => null);
}
