# Page Contracts

Source of truth:
- Frontend routes: `frontend/client/src/App.tsx`
- Page implementations: `frontend/client/src/pages/*.tsx`
- Backend APIs: `api/routers/*.py`

Note:
- The SPA uses hash routing, so the browser URLs are `#/...` while the React route paths remain `/...`.

Scope:
- `Dashboard`
- `Explorer`
- `Watchlists`
- `Alertes`
- `Recommandations`
- `Campagnes`
- `Admin Sources`

## Dashboard
- Route: `/` (`#/`)
- Purpose: operational overview of brand health, critical alerts, and top AI actions.
- Visible actions: inspect critical alerts, inspect recommended actions, inspect regional/product performance.
- Required backend endpoints: `GET /api/dashboard/summary`, `GET /api/dashboard/alerts-critical`, `GET /api/dashboard/top-actions`, `GET /api/status`.
- Current status: implemented and read-only; all main data panels are wired to live API responses.
- Decorative or dead controls: `language`, `grid_view`, `notifications`, and `sensors` buttons in `AppShell` are shell-only; alert cards and action cards are presentational and have no click handler.

## Explorer
- Route: `/explorateur` (`#/explorateur`)
- Purpose: semantic search plus paginated verbatim exploration across channels.
- Visible actions: type a query, run search, toggle source chips, paginate verbatims, expand a row to inspect the full verbatim, open cited and ranked sources.
- Required backend endpoints: `GET /api/explorer/search?q=...&limit=...&channel=...`, `GET /api/explorer/verbatims?page=...&page_size=...&channel=...&aspect=...&sentiment=...&wilaya=...`.
- Current status: functional for search, source filtering, RAG evidence, and pagination against the API.
- Decorative or dead controls: the `Filtrer` and `Exporter` chips remain shell-only.

## Watchlists
- Route: `/watchlists` (`#/watchlists`)
- Purpose: create watchlists, inspect their current metrics, and deactivate active ones.
- Visible actions: switch between all/active/inactive, search visible watchlists, open the create form, create a watchlist, select a watchlist, deactivate an active watchlist, inspect metrics and quick insight.
- Required backend endpoints: `GET /api/watchlists?is_active=true`, `GET /api/watchlists?is_active=false`, `GET /api/watchlists/{watchlist_id}/metrics`, `POST /api/watchlists`, `DELETE /api/watchlists/{watchlist_id}`.
- Current status: functional CRUD plus latest-metric snapshot lookup.
- Decorative or dead controls: `Voir les détails analytiques` is still decorative; the app-shell search performs local filtering on name, description, scope, and owner initials.

## Alertes
- Route: `/alertes` (`#/alertes`)
- Purpose: triage alerts and move them through the status lifecycle.
- Visible actions: search alerts, filter by status, filter by severity, select an alert, acknowledge, dismiss, or resolve it.
- Required backend endpoints: `GET /api/alerts?status=...&severity=...&limit=...`, `PUT /api/alerts/{alert_id}/status`.
- Current status: functional triage console with live status updates.
- Decorative or dead controls: none in the page body; the app-shell search filters by title, description, location, impact label, and excerpt text.

## Recommandations
- Route: `/recommandations` (`#/recommandations`)
- Purpose: generate AI recommendations, review active recommendations, and manage their status.
- Visible actions: search recommendation runs, choose trigger/provider/model, generate recommendations, archive all active recommendations, archive or dismiss one recommendation, inspect run history, and jump to `Explorateur` via the AI shortcut.
- Required backend endpoints: `GET /api/recommendations/providers`, `GET /api/recommendations/context-preview?trigger_type=...&provider=...&model=...`, `GET /api/recommendations?limit=50`, `POST /api/recommendations/generate`, `PUT /api/recommendations/{recommendation_id}/status`.
- Current status: functional generation and lifecycle management.
- Decorative or dead controls: no decorative card menu remains; the app-shell search filters active cards and run history by title, rationale, provider, trigger, summary, model, and target.

## Campagnes
- Route: `/campagnes` (`#/campagnes`)
- Purpose: create campaigns, browse the campaign list, and inspect NSS impact by campaign.
- Visible actions: search campaigns, create a campaign, filter the list by status, select a campaign row, page through the list, inspect the impact panel for the selected campaign.
- Required backend endpoints: `GET /api/campaigns`, `GET /api/campaigns/overview`, `GET /api/campaigns/{campaign_id}/impact`, `POST /api/campaigns`.
- Current status: functional for campaign creation, list browsing, and impact inspection.
- Decorative or dead controls: `EXPORTER DATA` remains shell-only; the top-right `CRÉER UNE CAMPAGNE` button scrolls to and focuses the real creation form, and the app-shell search filters rows by campaign, influencer, platform, type, status, and keywords.

## Admin Sources
- Route: `/admin-sources` (`#/admin-sources`)
- Internal views: `#/admin-sources?view=sources`, `credentials`, `campaign-ops`, `scheduler`.
- Purpose: administer ingestion sources, credentials, campaign-ops evidence, and scheduler behavior.
- Visible actions: switch views, create and update sources, trigger source sync and health, create and deactivate credentials, attach or remove campaign posts, collect engagement metrics, upload manual metrics or screenshots, patch campaign revenue, and run the scheduler tick.
- Required backend endpoints: `GET /api/admin/sources`, `GET /api/admin/sources/{source_id}/runs`, `GET /api/admin/sources/{source_id}/snapshots`, `POST /api/admin/sources`, `PUT /api/admin/sources/{source_id}`, `POST /api/admin/sources/{source_id}/sync`, `POST /api/admin/sources/{source_id}/health`, `GET /api/social-metrics/credentials`, `POST /api/social-metrics/credentials`, `DELETE /api/social-metrics/credentials/{credential_id}`, `GET /api/campaigns`, `GET /api/social-metrics/campaigns/{campaign_id}`, `GET /api/social-metrics/campaigns/{campaign_id}/posts`, `POST /api/social-metrics/campaigns/{campaign_id}/posts`, `DELETE /api/social-metrics/posts/{post_id}`, `POST /api/social-metrics/campaigns/{campaign_id}/collect`, `POST /api/social-metrics/posts/{post_id}/metrics/manual`, `POST /api/social-metrics/posts/{post_id}/metrics/screenshot`, `PATCH /api/social-metrics/campaigns/{campaign_id}/revenue`, `POST /api/admin/scheduler/tick`.
- Current status: mostly functional admin ops console; the main source, credential, campaign-ops, and scheduler flows are wired.
- Decorative or dead controls: top-nav `Ingestion`, `Pipelines`, and `Logs` items are shell-only; `notifications`, `settings`, `New Pipeline`, `Support`, and `Documentation` remain shell-only.
