# Backend Missing Fields For Stitch Fidelity

This file tracks Stitch-driven frontend fields that should not be invented in React.
If the backend does not expose them yet, the frontend must not render fake values.

## Campagnes

### Top performer ROI
- Page: `frontend/client/src/pages/Campagnes.tsx`
- Stitch example previously shown: `ROI 4.2x`
- Expected API field: `top_performer.roi`
- Suggested backend entrypoint: `GET /api/campaigns/stats`
- Suggested modules:
  - `api/routers/campaigns.py`
  - `core/campaigns/impact_calculator.py`
  - optional service to aggregate campaign business outcomes
- Notes:
  - current platform data exposes budget and NSS impact, but no revenue or conversion base
  - until ROI is computed from real business data, the frontend should not display an ROI number

### Top performer engagement rate
- Page: `frontend/client/src/pages/Campagnes.tsx`
- Stitch example previously shown: `+18% Engagement`
- Expected API field: `top_performer.engagement_rate`
- Suggested backend entrypoint: `GET /api/campaigns/stats` or `GET /api/campaigns/{id}/impact`
- Suggested modules:
  - `api/routers/campaigns.py`
  - `core/campaigns/impact_calculator.py`
- Notes:
  - current campaign impact exposes NSS uplift and volume uplift, but not a true engagement rate metric
  - the frontend now shows only real campaign metadata instead of an invented engagement percentage

## Recommandations

### Estimated LLM cost
- Page: `frontend/client/src/pages/Recommandations.tsx`
- Previous frontend-only estimate: token formula in React
- Expected API field: `estimated_cost_usd`
- Suggested backend entrypoint: `GET /api/recommendations/context-preview`
- Suggested modules:
  - `api/routers/recommendations.py`
  - `core/recommendation/context_builder.py`
  - pricing registry/provider metadata for each supported model
- Notes:
  - current backend exposes `estimated_tokens`, but not authoritative provider pricing
  - the frontend now displays `Non disponible` instead of a fabricated cost
