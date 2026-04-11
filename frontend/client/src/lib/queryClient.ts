import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { buildTenantHeaders, getStoredTenantId } from "./tenantContext";

const ANONYMOUS_TENANT_CACHE_KEY = "__anonymous__";
const tenantQueryClients = new Map<string, QueryClient>();

function getConfiguredApiKey(): string {
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
  const rawValue = env?.VITE_RAMYPULSE_API_KEY;
  return typeof rawValue === "string" ? rawValue.trim() : "";
}

function buildAuthHeaders(): Record<string, string> {
  const apiKey = getConfiguredApiKey();
  return apiKey ? { "X-API-Key": apiKey } : {};
}

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown> | null;
};

function mergeHeaders(...headersInit: Array<HeadersInit | undefined>): Headers {
  const merged = new Headers();
  headersInit.forEach((headers) => {
    if (!headers) return;
    new Headers(headers).forEach((value, key) => {
      merged.set(key, value);
    });
  });
  return merged;
}

function bodyNeedsJsonEncoding(body: unknown): body is Record<string, unknown> {
  if (body == null) return false;
  if (typeof body === "string") return false;
  if (body instanceof FormData) return false;
  if (body instanceof URLSearchParams) return false;
  if (body instanceof Blob) return false;
  if (body instanceof ArrayBuffer) return false;
  if (ArrayBuffer.isView(body)) return false;
  return typeof body === "object";
}

function shouldApplyJsonContentType(body: unknown, headers: Headers): boolean {
  if (headers.has("Content-Type") || body == null) return false;
  if (typeof body === "string") {
    const trimmed = body.trim();
    return trimmed.startsWith("{") || trimmed.startsWith("[");
  }
  return bodyNeedsJsonEncoding(body);
}

function normalizeRequestBody(body: unknown, headers: Headers): BodyInit | undefined {
  if (body == null) return undefined;
  if (shouldApplyJsonContentType(body, headers)) {
    headers.set("Content-Type", "application/json");
  }
  if (bodyNeedsJsonEncoding(body)) {
    return JSON.stringify(body);
  }
  if (
    typeof body === "string" ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    body instanceof Blob ||
    body instanceof ArrayBuffer ||
    ArrayBuffer.isView(body)
  ) {
    return body;
  }
  return undefined;
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response>;
export async function apiRequest(
  url: string,
  init?: ApiRequestOptions,
): Promise<Response>;
export async function apiRequest(
  methodOrUrl: string,
  urlOrInit?: string | ApiRequestOptions,
  data?: unknown,
): Promise<Response> {
  const tenantHeaders = buildTenantHeaders(getStoredTenantId());
  const isLegacyCall = typeof urlOrInit === "string";
  const method = isLegacyCall ? methodOrUrl : urlOrInit?.method ?? "GET";
  const requestUrl = isLegacyCall ? urlOrInit : methodOrUrl;
  const requestInit = (isLegacyCall ? {} : (urlOrInit ?? {})) as ApiRequestOptions;
  const rawBody = isLegacyCall ? data : requestInit.body;
  const headers = mergeHeaders(buildAuthHeaders(), tenantHeaders, requestInit.headers);
  const body = normalizeRequestBody(rawBody, headers);
  const res = await fetch(requestUrl, {
    ...requestInit,
    method,
    headers,
    body,
  });

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const res = await fetch(queryKey.join("/"), {
      headers: {
        ...buildAuthHeaders(),
        ...buildTenantHeaders(getStoredTenantId()),
      },
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    await throwIfResNotOk(res);
    return await res.json();
  };

function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        queryFn: getQueryFn({ on401: "throw" }),
        refetchInterval: false,
        refetchOnWindowFocus: false,
        staleTime: 30_000,
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function getTenantCacheKey(tenantId: string | null): string {
  return tenantId ?? ANONYMOUS_TENANT_CACHE_KEY;
}

export function getTenantQueryClient(tenantId: string | null): QueryClient {
  const cacheKey = getTenantCacheKey(tenantId);
  const existingClient = tenantQueryClients.get(cacheKey);

  if (existingClient) {
    return existingClient;
  }

  const nextClient = createQueryClient();
  tenantQueryClients.set(cacheKey, nextClient);
  return nextClient;
}
