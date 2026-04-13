# Tenant Initialization Pipeline Design

Date: 2026-04-12
Status: Draft for user review
Scope: Frontend only (`frontend/client/src/**`)

## Goal

Replace the current ambiguous "empty dashboard" experience with a production-grade initialization pipeline that:

- shows the real onboarding/run stages to the user
- persists and resumes after refresh
- stops immediately when one stage fails
- explains clearly which stage failed and why
- only reveals the real dashboard when the tenant is actually ready

## Problem

The current product gating is based on `tenantId` presence only.

Current behavior:

- if `tenantId` exists, `/` renders `Dashboard`
- if no metrics/alerts/actions are available, the dashboard shows a generic empty state
- the onboarding run progress is only kept in React memory
- a refresh or navigation back to `/` loses the run context

This is not production-safe because the user cannot distinguish between:

- initialization still running
- a failed stage
- a completed run with no usable data
- a tenant that was never initialized correctly

## Existing Relevant Code

- `frontend/client/src/pages/ProductHome.tsx`
- `frontend/client/src/lib/routeAccess.ts`
- `frontend/client/src/pages/Dashboard.tsx`
- `frontend/client/src/pages/WatchOnboarding.tsx`
- `frontend/client/src/components/watch/WatchOnboardingWizard.tsx`
- `frontend/client/src/components/watch/RunProgressPanel.tsx`
- `frontend/client/src/lib/tenantContext.ts`

## Product Decision

Adopt a dedicated initialization pipeline screen as the canonical pre-dashboard experience.

Rules:

1. A selected tenant is not considered ready just because `tenantId` exists.
2. If an onboarding run is active or unresolved, product routes must show the pipeline screen instead of the dashboard.
3. If one stage fails, the pipeline stops, polling stops, and the UI highlights the failed stage with the backend error message.
4. The dashboard is shown only when the tenant is operationally ready.

## Intended User Experience

### State A: No tenant / no onboarding started

The user sees the onboarding wizard.

### State B: Onboarding or first watch run is in progress

The user sees a dedicated pipeline screen with:

- stage cards for `collecting`, `normalizing`, `indexing`, `finished`
- each stage marked as `pending`, `running`, `success`, `skipped`, or `error`
- live counters from backend step payloads
- current active stage clearly highlighted
- operator-friendly wording instead of vague marketing copy

### State C: A stage fails

The pipeline stops on the failed stage and shows:

- failed stage name
- backend error message for the failing step
- overall run status
- a clear operator action area

The screen must not continue to the next stage automatically.
The dashboard must remain blocked.

### State D: Run finishes but usable dashboard data is still missing

The user sees a completion-without-data state, not the generic dashboard placeholder.

This state explains:

- the run finished
- no exploitable signals are available yet
- the issue is not hidden

### State E: Tenant is ready

Only then does the app route to the real dashboard.

## Proposed Frontend Architecture

### 1. Persist onboarding run context

Add a dedicated local storage record for the active onboarding run.

Suggested shape:

```ts
type ActiveOnboardingRun = {
  clientId: string;
  runId: string;
  watchlistId: string;
  source: "smart" | "manual";
  lastKnownStatus?: string | null;
  lastKnownStage?: string | null;
};
```

This record is written when:

- manual onboarding creates the first run
- smart onboarding confirmation returns the first run

This record is cleared only when:

- the tenant becomes operationally ready
- the user explicitly restarts onboarding
- the run is no longer relevant to the active tenant

### 2. Introduce a tenant readiness resolver

Add a frontend resolver/hook that determines one of these states:

- `missing_tenant`
- `needs_onboarding`
- `run_in_progress`
- `run_failed`
- `run_completed_no_data`
- `ready`

Inputs:

- current stored tenant id
- persisted onboarding run context
- `/api/watch-runs/{run_id}` when a run exists
- existing dashboard summary query to determine whether usable data is present

### 3. Gate product routes on readiness, not on tenant existence

Change the routing rule so `/`, `/explorateur`, `/campagnes`, `/watchlists`, `/alertes`, `/recommandations` do not unlock just because a tenant is selected.

Desired behavior:

- no tenant: show onboarding wizard
- tenant + active run: show pipeline page
- tenant + failed run: show pipeline failure page
- tenant + successful run but no usable data: show explicit no-data completion state
- tenant ready: show dashboard and normal product routes

### 4. Replace the empty dashboard as the primary pre-ready screen

`Dashboard.tsx` should no longer be responsible for explaining initialization progress.

The pipeline page becomes the authoritative source of truth before readiness.

The existing empty tenant block may remain as a defensive fallback, but it should no longer be the normal path for an initializing tenant.

### 5. Upgrade the run progress panel into an operator pipeline

Extend the existing `RunProgressPanel` behavior so it:

- displays each pipeline stage with a stable state badge
- shows exact step errors from backend payload
- freezes in place on first failure
- stops polling on terminal states including failure
- exposes clear operator CTAs

Suggested CTA set on failure:

- `Reprendre le wizard`
- `Relancer l'initialisation`
- `Basculer vers un tenant de démonstration` (optional existing shortcut)

## Readiness Rules

Readiness must be explicit.

Recommended frontend rule set:

1. If there is no tenant id, state is `missing_tenant`.
2. If there is a tenant id but no onboarding run context yet, state is `needs_onboarding`.
3. If the run status or one backend step is `error`, state is `run_failed`.
4. If the run is still non-terminal, state is `run_in_progress`.
5. If the run finished successfully but dashboard summary still reports no usable signals, state is `run_completed_no_data`.
6. If the run finished successfully and dashboard summary contains usable data, state is `ready`.

Initial heuristic for "usable data":

- `summary.totalMentions > 0`

This is intentionally stricter than the current implementation because the requirement is to show the real dashboard only when real data exists.

## Failure Handling

Failure behavior is strict.

When any stage or step fails:

- mark the corresponding stage as `error`
- stop polling
- keep the pipeline visible
- show the exact backend-provided error message
- prevent navigation to the dashboard as the default route

This satisfies the approved requirement:

> the pipeline stops if a stage fails

## Refresh and Resume Behavior

After browser refresh:

- the app restores the persisted onboarding run for the active tenant
- the readiness resolver fetches `/api/watch-runs/{run_id}`
- the user returns to the exact pipeline state instead of the empty dashboard

This is the key correction for the current production gap.

## Constraints and Assumptions

- This design avoids backend changes because `api/` is out of scope for this worktree.
- Because there is currently no backend endpoint for "latest onboarding run for current tenant", resume depends on frontend persistence of the first run id.
- Cross-device or cross-browser resume remains limited by that backend constraint.

## Implementation Outline

1. Add onboarding run persistence helpers in frontend state utilities.
2. Add a readiness resolver hook for tenant operational state.
3. Update onboarding success flows to persist run context.
4. Upgrade the pipeline/progress screen for running, failed, and completed-no-data states.
5. Change product route gating to depend on readiness state.
6. Remove the current empty-dashboard path as the normal initializing-tenant experience.

## Test Plan

Required frontend coverage:

- route `/` shows onboarding when no tenant exists
- route `/` resumes pipeline when tenant exists and persisted run is active
- pipeline stops and displays failure when backend run status becomes `error`
- successful run with usable data unlocks dashboard
- successful run with zero usable data shows explicit completion-without-data state
- refresh during in-progress run preserves the pipeline state

## Risks

- Frontend-only persistence does not solve cross-device continuity.
- `summary.totalMentions > 0` is a pragmatic readiness heuristic, but not a perfect business truth.
- If backend step messages are low quality, the failure UI can only be as precise as the API payload.

## Recommendation

Proceed with this frontend implementation now, with one explicit limitation:

- production-grade within the current frontend-only boundary
- later backend enhancement recommended for tenant-scoped "latest onboarding run" recovery
