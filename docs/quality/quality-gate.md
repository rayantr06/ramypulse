# Quality Gate

This gate exists to stop page-level spec drift before manual demo testing.

## A page is not releasable if
- a visible control has no real effect and is not explicitly tagged as shell-only or decorative;
- the frontend payload does not match the backend contract;
- no business scenario exists for the page;
- no automated page contract or golden-path coverage exists for the page family.

## Required documents
- `docs/quality/page-contracts.md`
- `docs/quality/golden-paths.md`

## Required commands
- `node --test frontend/tests/pageContracts.test.mjs`
- `npx.cmd tsx --test frontend/tests/pageSearchFilters.test.ts frontend/tests/uiPayloadContracts.test.ts frontend/tests/explorerAiView.test.ts`
- `node --test frontend/tests/interactiveSurfaceAudit.test.mjs`
- `node --test frontend/tests/stitchTextFidelity.test.mjs`
- `cd frontend && npm.cmd run test:golden`

## Current focus pages
- `Explorateur`
- `Watchlists`
- `Alertes`
- `Campagnes`
- `Recommandations`
- `Admin Sources`

## Expected outcome
- page contracts stay aligned with visible product surface;
- high-risk forms keep the backend payload shape;
- golden paths remain reproducible in Playwright;
- decorative controls are explicit instead of ambiguous.
