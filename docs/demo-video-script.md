# Demo Video Script

## Goal
Record a clean, honest product walkthrough that proves RamyPulse is a multi-source AI marketing intelligence platform without pretending every visible control in the product is finished.

## Recording Rules
- Use prepared demo data only.
- Follow the route order exactly.
- Click only the controls listed below.
- Do not click decorative shell icons or disabled demo controls.
- Keep the framing tight on the main product canvas when possible.

## Route Order
1. `#/`
2. `#/explorateur`
3. `#/alertes`
4. `#/recommandations`
5. `#/campagnes`
6. `#/admin-sources?view=sources`
7. `#/admin-sources?view=scheduler`

## Scene 1: Dashboard
- Open `#/`
- Show the global overview cards and top actions area.
- Narration:
  - RamyPulse centralizes fragmented marketing signals into one operating view.
  - The dashboard gives a fast summary of health, alerts, and action-oriented priorities.
- Do not click dashboard decorative controls.

## Scene 2: Explorer + RAG Insight
- Open `#/explorateur`
- Enter a prepared natural-language query in the search bar.
- Click `Explorer`.
- Wait for the result cards and the `RAG Insight` block.
- Narration:
  - Explorer combines semantic retrieval with enriched customer signals.
  - `RAG Insight` turns the current search results into a concise AI reading grounded in the underlying evidence.
- Do not click `Filtrer` or `Exporter`.

## Scene 3: Alerts
- Open `#/alertes`
- Show the alerts list, severity/status controls, and one alert detail panel.
- Narration:
  - RamyPulse detects anomalies, threshold breaches, and business-critical drifts.
  - Teams can triage and update alert state directly from the alert center.

## Scene 4: Recommendations
- Open `#/recommandations`
- Show the provider/model selection area, active recommendations, and one recommendation card.
- If generation is stable in the current dataset, trigger one generation path; otherwise present an existing result.
- Narration:
  - Recommendations transform observed signals into concrete action proposals.
  - The product keeps the operational context visible instead of generating generic text.
- Do not look for a contextual `more_vert` menu; it is intentionally removed from the demo path.

## Scene 5: Campaigns
- Open `#/campagnes`
- Show the overview metrics and the `Top Performeur` area.
- Click the main `CRÉER UNE CAMPAGNE` CTA only to focus the real creation form.
- Narration:
  - Campaign intelligence links spend, impact context, and engagement evidence.
  - The main CTA now routes to the actual composer instead of a dead visual action.
- Do not click `EXPORTER DATA`.

## Scene 6: Admin Sources
- Open `#/admin-sources?view=sources`
- Show the `Sources` subview, the source list, and the governance block in the edit panel.
- Narration:
  - This is the governed multi-source control plane.
  - Operators manage sources, priorities, coverage, and credentials without breaking the Stitch admin shell.
- Stay inside the subview tabs.
- Do not click `Pipelines`, `Logs`, `Connectors`, `Health`, `Validation`, `Archive`, `New Pipeline`, `Support`, or `Documentation`.

## Scene 7: Scheduler / Runtime
- Switch to `#/admin-sources?view=scheduler`
- Show the `Run due syncs` surface and the last tick result card.
- Narration:
  - The platform supports scheduler-driven ingestion operations and controlled runtime execution.
  - Multi-source priority and fallback logic stay visible at the operator level.
- Keep the shot on the scheduler cards and result panel.

## Mandatory Labels To Verify Before Recording
- `RAG Insight`
- `Actions recommandées`
- `Top Performeur`
- `Gouvernance source`
- `Run due syncs`

## Last Pre-Recording Check
- Frontend build passes.
- `stitchTextFidelity` passes.
- Admin visual smoke passes.
- Prepared data is loaded.
