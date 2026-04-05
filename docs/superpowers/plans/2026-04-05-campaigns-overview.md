# Campaigns Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a campaigns-facing overview endpoint and wire `Campagnes.tsx` to it so the page no longer derives its top performer locally.

**Architecture:** Keep `social-metrics` as an internal specialized source and expose a page-level contract under `campaigns`. The backend computes the overview bundle once, the frontend consumes a single overview payload for budget and top performer data.

**Tech Stack:** FastAPI, SQLite-backed campaign/social metrics services, React, TanStack Query, TypeScript, pytest, node:test.

---

### Task 1: Backend contract

**Files:**
- Create: `core/campaigns/overview_service.py`
- Modify: `api/schemas.py`
- Modify: `api/routers/campaigns.py`
- Test: `tests/test_api.py`

- [ ] Add a failing API test for `GET /api/campaigns/overview`
- [ ] Implement overview aggregation over campaigns + social metrics
- [ ] Expose the endpoint and response schema
- [ ] Run the focused pytest selection until green

### Task 2: Frontend contract and page wiring

**Files:**
- Modify: `frontend/shared/schema.ts`
- Modify: `frontend/client/src/lib/apiMappings.ts`
- Modify: `frontend/tests/apiMappings.test.ts`
- Modify: `frontend/client/src/pages/Campagnes.tsx`

- [ ] Add a failing frontend mapping test for the overview payload
- [ ] Add the shared/frontend types and mapper
- [ ] Replace the `campaigns/stats` fetch in `Campagnes.tsx` with `campaigns/overview`
- [ ] Render top performer metrics only when real values exist
- [ ] Run the focused frontend tests until green

### Task 3: Verification

**Files:**
- Modify only if verification reveals a defect

- [ ] Run `python -m pytest tests/ -q --tb=no`
- [ ] Run `node --test tests/stitchTextFidelity.test.mjs`
- [ ] Run `npm.cmd run check`
- [ ] Run `npm.cmd run build`
- [ ] Report actual results only after fresh verification
