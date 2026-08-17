const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "content-type",
  "x-ramy-client-id",
];

const FORWARDED_RESPONSE_HEADERS = [
  "cache-control",
  "content-disposition",
  "content-type",
];

function firstQueryValue(value) {
  return Array.isArray(value) ? value[0] : value;
}

function resolveRequestedPath(request) {
  const queryPath = firstQueryValue(request.query?.path);
  if (typeof queryPath === "string" && queryPath.trim()) {
    return queryPath.replace(/^\/+/, "");
  }

  return String(request.url || "")
    .split("?", 1)[0]
    .replace(/^\/api\//, "")
    .replace(/^\/+/, "");
}

function buildUpstreamUrl(request, backendUrl) {
  const requestedPath = resolveRequestedPath(request);
  const target = new URL(`/api/${requestedPath}`, backendUrl.replace(/\/+$/, ""));

  for (const [key, rawValue] of Object.entries(request.query || {})) {
    if (key === "path") continue;
    const values = Array.isArray(rawValue) ? rawValue : [rawValue];
    for (const value of values) {
      if (value != null) target.searchParams.append(key, String(value));
    }
  }

  return target;
}

function buildRequestBody(request) {
  if (request.method === "GET" || request.method === "HEAD" || request.body == null) {
    return undefined;
  }
  if (typeof request.body === "string" || Buffer.isBuffer(request.body)) {
    return request.body;
  }
  return JSON.stringify(request.body);
}

export default async function handler(request, response) {
  const backendUrl = process.env.RAMYPULSE_BACKEND_URL?.trim();
  const backendApiKey = process.env.RAMYPULSE_BACKEND_API_KEY?.trim();

  if (!backendUrl || !backendApiKey) {
    return response.status(503).json({
      detail: "Le service d'analyse n'est pas encore configuré.",
    });
  }

  const headers = new Headers();
  for (const headerName of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers?.[headerName];
    if (typeof value === "string" && value.trim()) {
      headers.set(headerName, value);
    }
  }
  headers.set("x-api-key", backendApiKey);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 55_000);

  try {
    const upstream = await fetch(buildUpstreamUrl(request, backendUrl), {
      method: request.method,
      headers,
      body: buildRequestBody(request),
      signal: controller.signal,
    });

    for (const headerName of FORWARDED_RESPONSE_HEADERS) {
      const value = upstream.headers.get(headerName);
      if (value) response.setHeader(headerName, value);
    }

    const payload = Buffer.from(await upstream.arrayBuffer());
    return response.status(upstream.status).send(payload);
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "AbortError";
    return response.status(timedOut ? 504 : 502).json({
      detail: timedOut
        ? "Le service d'analyse met trop de temps à répondre."
        : "Le service d'analyse est temporairement indisponible.",
    });
  } finally {
    clearTimeout(timeout);
  }
}

export const __testables = {
  buildUpstreamUrl,
  resolveRequestedPath,
};
