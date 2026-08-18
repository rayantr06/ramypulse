import assert from "node:assert/strict";
import test from "node:test";

import {
  shouldGateProductRoute,
  shouldResetTenantCache,
} from "../client/src/lib/routeAccess";

test("product routes gate until readiness is ready, while admin-sources stays outside the gate", () => {
  assert.equal(shouldGateProductRoute("/explorateur", "run_in_progress"), true);
  assert.equal(shouldGateProductRoute("/campagnes", "run_failed"), true);
  assert.equal(shouldGateProductRoute("/recommandations", "run_completed_no_data"), true);
  assert.equal(shouldGateProductRoute("/watchlists/new", "needs_onboarding"), true);
  assert.equal(shouldGateProductRoute("/explorateur", "checking"), false);
  assert.equal(shouldGateProductRoute("/admin-sources", "run_in_progress"), false);
  assert.equal(shouldGateProductRoute("/nouveau-client", "run_in_progress"), false);
  assert.equal(shouldGateProductRoute("/explorateur", "ready"), false);
});

test("tenant cache resets only when the stored tenant changes", () => {
  assert.equal(shouldResetTenantCache(null, null), false);
  assert.equal(shouldResetTenantCache(null, "ramy_client_001"), true);
  assert.equal(shouldResetTenantCache("ramy_client_001", "ramy_client_001"), false);
  assert.equal(shouldResetTenantCache("ramy_client_001", "ramy_client_002"), true);
});
