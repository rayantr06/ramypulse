# Golden Paths

These scenarios are grounded in the current frontend routes and backend APIs.

## Dashboard
1. Open `#/`.
   - Expected result: the dashboard loads the brand-health score, the three critical-alert cards, the AI action cards, the product bars, and the regional distribution section.
2. Open `#/` when the database has no current snapshot data.
   - Expected result: the page still renders, but the KPI and panel areas fall back to empty or default messaging instead of crashing.

## Explorer
1. Open `#/explorateur`, type a natural-language query, and click `Explorer`.
   - Expected result: search results appear from `GET /api/explorer/search`, ranked by relevance, with sentiment labels and source metadata.
2. Stay on `#/explorateur` and move through verbatim pages with the next/previous buttons.
   - Expected result: `GET /api/explorer/verbatims` reloads the current page and the table updates with the new page number and rows.

## Watchlists
1. Open `#/watchlists`, click `Créer une watchlist`, fill the form, and submit.
   - Expected result: `POST /api/watchlists` creates the watchlist, the form closes, and the new watchlist becomes the selected one with its metrics loaded from `/api/watchlists/{watchlist_id}/metrics`.
2. Open `#/watchlists`, select an active watchlist, and click `Désactiver`.
   - Expected result: `DELETE /api/watchlists/{watchlist_id}` marks it inactive, the list refreshes, and the watchlist no longer appears in the active set.
3. Open `#/watchlists`, type a search term such as `oran` in the header search.
   - Expected result: only the watchlists matching name, description, scope, or owner initials remain visible.

## Alertes
1. Open `#/alertes`, filter to `CRITIQUE`, select an alert, then click `Reconnaître`.
   - Expected result: `GET /api/alerts` returns the filtered list and `PUT /api/alerts/{alert_id}/status` moves the selected alert to `acknowledged`.
2. On `#/alertes`, click `Résoudre` for a selected alert.
   - Expected result: the alert status changes to `resolved`, the alert remains visible only if the current filters still match it, and the summary counters update.
3. Open `#/alertes`, type a term such as `oran` in the header search.
   - Expected result: the alert list narrows by title, description, location, impact label, or excerpt text while keeping triage actions available.

## Recommandations
1. Open `#/recommandations`, leave the trigger on `Manuel`, click `Générer`.
   - Expected result: `POST /api/recommendations/generate` creates a new recommendation run, and the active recommendation cards refresh.
2. On `#/recommandations`, open an active recommendation and click `Archiver`.
   - Expected result: `PUT /api/recommendations/{recommendation_id}/status` sets the status to `archived`, and the item disappears from the active section after refresh.
3. Open `#/recommandations`, type a term such as `promo` in the header search.
   - Expected result: the active cards and run history narrow to matching title, rationale, provider, trigger, model, or summary text.

## Campagnes
1. Open `#/campagnes`, fill the create-campaign form, and submit `Lancer la Campagne`.
   - Expected result: `POST /api/campaigns` creates a campaign, the list refreshes, and the new campaign can be selected in the table.
2. Open `#/campagnes`, select a campaign row, and inspect its impact block.
   - Expected result: `GET /api/campaigns/{campaign_id}/impact` populates the NSS pre/during/post metrics and the impact summary for that campaign.
3. Open `#/campagnes`, type a term such as `amine` in the header search.
   - Expected result: the visible campaign rows narrow by campaign name, influencer, platform, type, status, or keywords, and the selected campaign stays aligned with the visible table.

## Admin Sources
1. Open `#/admin-sources?view=sources`, create a source, then trigger `Lancer sync`.
   - Expected result: `POST /api/admin/sources` creates the source, `POST /api/admin/sources/{source_id}/sync` launches a sync run, and the runs/snapshots panels refresh.
2. Open `#/admin-sources?view=campaign-ops`, select a campaign, add a post, and collect metrics.
   - Expected result: `POST /api/social-metrics/campaigns/{campaign_id}/posts` links the post, `POST /api/social-metrics/campaigns/{campaign_id}/collect` gathers engagement, and the campaign-ops tables update.
