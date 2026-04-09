import assert from "node:assert/strict";
import test from "node:test";

import { getTenantQueryClient } from "../client/src/lib/queryClient";

test("getTenantQueryClient returns a stable QueryClient per tenant id", () => {
  const first = getTenantQueryClient("ramy_client_001");
  const second = getTenantQueryClient("ramy_client_001");
  const third = getTenantQueryClient("ramy_client_002");
  const anonymousFirst = getTenantQueryClient(null);
  const anonymousSecond = getTenantQueryClient(null);

  assert.equal(first, second);
  assert.notEqual(first, third);
  assert.equal(anonymousFirst, anonymousSecond);
  assert.notEqual(first, anonymousFirst);
});

test("getTenantQueryClient isolates cached query data between tenants", () => {
  const firstTenantClient = getTenantQueryClient("ramy_client_001");
  const secondTenantClient = getTenantQueryClient("ramy_client_002");
  const anonymousClient = getTenantQueryClient(null);
  const queryKey = ["/api/dashboard"];

  firstTenantClient.setQueryData(queryKey, { tenant: "ramy_client_001" });
  secondTenantClient.setQueryData(queryKey, { tenant: "ramy_client_002" });
  anonymousClient.setQueryData(queryKey, { tenant: null });

  assert.deepEqual(firstTenantClient.getQueryData(queryKey), { tenant: "ramy_client_001" });
  assert.deepEqual(secondTenantClient.getQueryData(queryKey), { tenant: "ramy_client_002" });
  assert.deepEqual(anonymousClient.getQueryData(queryKey), { tenant: null });
});
