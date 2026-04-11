import assert from "node:assert/strict";
import test from "node:test";

import {
  shouldGateProductRoute,
  shouldResetTenantCache,
} from "../client/src/lib/routeAccess";

test("product routes gate when no tenant is stored, while admin-sources stays outside the gate", () => {
  assert.equal(shouldGateProductRoute("/explorateur", null), true);
  assert.equal(shouldGateProductRoute("/campagnes", null), true);
  assert.equal(shouldGateProductRoute("/admin-sources", null), false);
  assert.equal(shouldGateProductRoute("/nouveau-client", null), false);
});

test("tenant cache resets only when the stored tenant changes", () => {
  assert.equal(shouldResetTenantCache(null, null), false);
  assert.equal(shouldResetTenantCache(null, "ramy_client_001"), true);
  assert.equal(shouldResetTenantCache("ramy_client_001", "ramy_client_001"), false);
  assert.equal(shouldResetTenantCache("ramy_client_001", "ramy_client_002"), true);
});
