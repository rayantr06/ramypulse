# Backend Missing Fields For Stitch Fidelity

This file tracks fields that are still missing for active frontend pages.
If a field is already exposed somewhere in the backend, it should not stay listed here as
"missing" just because the frontend is not wired to it yet.

## Still Open

## Campagnes

### Campaign overview top performer bundle
- Page: `frontend/client/src/pages/Campagnes.tsx`
- Current frontend behavior:
  - reads `GET /api/campaigns`
  - reads `GET /api/campaigns/stats`
  - reads `GET /api/campaigns/{id}/impact`
  - derives `topPerformer` locally from the first active campaign
- Missing backend contract for this page:
  - `GET /api/campaigns/stats` should expose a real `top_performer` object, or
  - `GET /api/campaigns` should expose enough fields to build that card honestly
- Expected fields for the page-level card:
  - `top_performer.influencer_handle`
  - optional `top_performer.roi_pct`
  - optional `top_performer.engagement_rate`
  - optional `top_performer.signal_count`
  - optional `top_performer.sentiment_breakdown`
  - optional `top_performer.negative_aspects`
- Notes:
  - the backend already exposes campaign-level engagement and sentiment via
    `GET /api/social-metrics/campaigns/{campaign_id}`
  - the `Campagnes` page does not consume that endpoint today
  - until this bundle exists on a campaigns-facing endpoint, the page should keep showing
    only real campaign metadata and must not invent ROI or engagement values

### Top performer ROI for the campaigns overview
- Page: `frontend/client/src/pages/Campagnes.tsx`
- Stitch example previously shown: `ROI 4.2x`
- Current state:
  - `roi_pct` exists only in `GET /api/social-metrics/campaigns/{campaign_id}`
  - it depends on real `revenue_dza` plus linked campaign posts
  - no campaigns overview endpoint exposes `top_performer.roi_pct` today
- Suggested backend entrypoint:
  - enrich `GET /api/campaigns/stats` with `top_performer.roi_pct`
- Notes:
  - do not derive ROI from NSS uplift
  - if no `revenue_dza` is available for the winning campaign, this field must stay absent/null

### Top performer engagement rate for the campaigns overview
- Page: `frontend/client/src/pages/Campagnes.tsx`
- Stitch example previously shown: `+18% Engagement`
- Current state:
  - `engagement_rate` exists only in `GET /api/social-metrics/campaigns/{campaign_id}`
  - it depends on real collected reach and interactions
  - no campaigns overview endpoint exposes `top_performer.engagement_rate` today
- Suggested backend entrypoint:
  - enrich `GET /api/campaigns/stats` with `top_performer.engagement_rate`
- Notes:
  - do not fabricate this from campaign impact or NSS uplift
  - if no linked post metrics exist for the winning campaign, this field must stay absent/null

## Resolved

## Dashboard

### API status and latency
- Page: `frontend/client/src/pages/Dashboard.tsx`
- Status: resolved
- Backend:
  - `GET /api/status`
- Notes:
  - the frontend now reads real `api_status` and `latency_ms`
  - hardcoded `API Status: Normal` and `Latency: 42ms` are gone

## Campagnes

### Quarterly budget allocation
- Page: `frontend/client/src/pages/Campagnes.tsx`
- Status: resolved
- Backend:
  - `GET /api/campaigns/stats`
- Fields:
  - `quarterly_budget_committed`
  - `quarterly_budget_allocation`
  - `quarter_label`

## Recommandations

### Estimated LLM cost
- Page: `frontend/client/src/pages/Recommandations.tsx`
- Status: resolved
- Backend:
  - `GET /api/recommendations/context-preview`
- Field:
  - `estimated_cost_usd`
- Notes:
  - pricing now comes from the backend pricing registry
  - the old frontend-only token formula is gone

## Social Metrics

### Campaign engagement and sentiment summary
- Surface:
  - `frontend/client/src/components/admin/AdminSourcesOps.tsx`
- Status: resolved
- Backend:
  - `GET /api/social-metrics/campaigns/{campaign_id}`
- Fields:
  - `engagement_rate`
  - `roi_pct`
  - `revenue_dza`
  - `signal_count`
  - `sentiment_breakdown`
  - `negative_aspects`
  - `top_performer`
- Notes:
  - this is implemented in the backend
  - the remaining gap is that `Campagnes.tsx` does not consume an equivalent campaigns-facing summary yet
