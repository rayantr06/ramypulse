import assert from "node:assert/strict";
import test from "node:test";

import type { ActiveOnboardingRun } from "../client/src/lib/onboardingRunState";
import { resolveTenantReadiness } from "../client/src/lib/tenantReadiness";

function buildRun(status: string, stage: string) {
  return {
    run_id: "run-001",
    client_id: "ifri",
    stage,
    status,
    records_collected: 4,
    steps: {},
  };
}

const activeRun: ActiveOnboardingRun = {
  clientId: "ifri",
  runId: "run-001",
  watchlistId: "watch-001",
  source: "smart",
  lastKnownStatus: null,
  lastKnownStage: null,
};

test("resolveTenantReadiness returns missing_tenant when there is no tenant", () => {
  assert.equal(
    resolveTenantReadiness({
      tenantId: null,
      activeRun: null,
      run: null,
      summary: null,
    }),
    "missing_tenant",
  );
});

test("resolveTenantReadiness returns needs_onboarding for a tenant without data and without run context", () => {
  assert.equal(
    resolveTenantReadiness({
      tenantId: "ifri",
      activeRun: null,
      run: null,
      summary: { total_mentions: 0 },
    }),
    "needs_onboarding",
  );
});

test("resolveTenantReadiness returns ready for an existing tenant that already has usable data", () => {
  assert.equal(
    resolveTenantReadiness({
      tenantId: "ramy-demo",
      activeRun: null,
      run: null,
      summary: { total_mentions: 12 },
    }),
    "ready",
  );
});

test("resolveTenantReadiness returns run_in_progress while the first run is active", () => {
  assert.equal(
    resolveTenantReadiness({
      tenantId: "ifri",
      activeRun,
      run: buildRun("running", "normalizing"),
      summary: { total_mentions: 0 },
    }),
    "run_in_progress",
  );
});

test("resolveTenantReadiness returns run_failed when the run errors", () => {
  assert.equal(
    resolveTenantReadiness({
      tenantId: "ifri",
      activeRun,
      run: buildRun("error", "indexing"),
      summary: { total_mentions: 0 },
    }),
    "run_failed",
  );
});

test("resolveTenantReadiness returns run_completed_no_data when the run ends without usable signals", () => {
  assert.equal(
    resolveTenantReadiness({
      tenantId: "ifri",
      activeRun,
      run: buildRun("ready", "finished"),
      summary: { total_mentions: 0 },
    }),
    "run_completed_no_data",
  );
});

test("resolveTenantReadiness returns ready when the run ends and dashboard data exists", () => {
  assert.equal(
    resolveTenantReadiness({
      tenantId: "ifri",
      activeRun,
      run: buildRun("ready", "finished"),
      summary: { total_mentions: 18 },
    }),
    "ready",
  );
});
