import assert from "node:assert/strict";
import test from "node:test";

import { buildWatchlistCreatePayload } from "../client/src/lib/apiMappings";

test("buildWatchlistCreatePayload matches the backend watchlist contract", () => {
  const payload = buildWatchlistCreatePayload({
    name: "  NSS Oran  ",
    description: "  Surveille Oran  ",
    scope_type: "region",
    product: "ramy_citron",
    wilaya: "oran",
    channel: "google_maps",
    aspect: "disponibilite",
    sentiment: "",
    period_days: 7,
    min_volume: 10,
  });

  assert.deepEqual(payload, {
    name: "NSS Oran",
    description: "Surveille Oran",
    scope_type: "region",
    filters: {
      channel: "google_maps",
      aspect: "disponibilite",
      wilaya: "oran",
      product: "ramy_citron",
      sentiment: null,
      period_days: 7,
      min_volume: 10,
    },
  });
});
