# Demo Video Path Design

## Goal
Create a short-lived product branch that makes the demo video path credible, stable, and honest without pretending the whole product is finished.

## Problem
The competition submission requires a YouTube demo video and a write-up. The current product already has real backend depth, but several visible UI controls are still decorative. A free-form live demo would expose dead buttons and unfinished surfaces, which would make the product look weaker than it is.

The right response is not to "finish everything." The right response is to make the exact scenes shown in the video reliable and coherent.

## Demo Narrative
The video must prove these product claims:

1. RamyPulse is a multi-source AI marketing intelligence platform.
2. It can explore enriched signals, not just display static dashboards.
3. It can detect issues and surface alerts.
4. It can turn analysis into recommendations.
5. It can connect campaign performance with business context.
6. It has operator-facing source governance and runtime control.

## Mandatory Demo Scenes

### 1. Dashboard
Purpose:
- establish the global product surface
- show health, alerts, and AI-driven actions

Allowed interactions:
- page load only

### 2. Explorer
Purpose:
- show search across enriched content
- show an explicit AI/RAG insight inside the Explorer page

Allowed interactions:
- type a query
- submit search
- optionally change one source filter

### 3. Alerts
Purpose:
- show detected alerts and drill into one alert

Allowed interactions:
- select an alert
- optionally change one filter

### 4. Recommendations
Purpose:
- show recommendation generation and/or active recommendations list

Allowed interactions:
- choose provider/model
- generate recommendations
- optionally archive one recommendation

### 5. Campaigns
Purpose:
- show campaign creation or campaign overview
- show business-facing metrics such as budget, impact, top performer

Allowed interactions:
- create one campaign through the real form on the left
- select one campaign row

### 6. Admin Sources
Purpose:
- prove the product has real operational controls, not only user-facing pages

Allowed interactions:
- switch between `Sources`, `Credentials`, `Campaign Ops`, and `Scheduler`
- run `scheduler/tick` or `runtime/cycle`

## Non-Negotiable Invariants

### Product integrity
- No fake business metrics.
- No fake backend workflows.
- No new page whose only purpose is to look good in the video.
- No separate React chat page just for demo purposes.

### Architecture safety
- Do not break multi-source orchestration.
- Do not change `coverage_key`, `source_priority`, scheduler fallback behavior, or `content_items` identity rules in this sprint.
- Do not refactor ingestion or connectors in this sprint.
- Do not change auth/runtime behavior unless required for a filmed flow.

### UX safety
- Every control that is visibly clicked in the video must work.
- Every control that is visibly prominent in filmed scenes and does not work must be hidden, downgraded, or rendered non-interactive in a deliberate way.
- Preserve Stitch visual language.

## Scope

### In scope
- Explorer RAG/AI surface inside the existing page
- removing or neutralizing dead controls on filmed surfaces
- making Recommendations and Campaigns scenes safer for a guided demo
- making Admin demo-safe while preserving the real internal subviews
- preparing deterministic demo data and a reset path
- adding smoke verification for the exact demo path

### Out of scope
- finishing all pages
- implementing all decorative shell items
- official platform ingestion connector work
- audio pipeline
- broad refactors
- new product modules

## Demo Data Strategy
- Use deterministic local demo data, not live fragile dependencies.
- Prefer seeded DB state and existing sample records over last-minute mocks.
- If the demo needs a reset, use a small script or documented reset command.
- The video should not depend on a live third-party API during recording.

## UX Decisions

### Explorer
- Keep the current search/results/verbatims layout.
- Add a clear AI/RAG answer block in-page, above or beside results.
- Do not add a separate chat route.
- Remove or neutralize the floating `chat` button if it still does nothing.

### Recommendations
- Keep the current generation form and active recommendations cards.
- Remove or neutralize `more_vert` if it is still decorative.

### Campaigns
- Keep the real left-side create form.
- Either wire the top CTA to the same real flow or downgrade it visually so it is not a trap.
- Remove or neutralize `EXPORTER DATA` and `expand_less` if they remain decorative in the filmed scene.

### Admin
- Keep the internal admin subviews because they are real.
- Do not film or expose decorative outer shell items as if they were functional.
- If necessary, make clearly non-functional shell items visually subdued in demo mode.

## Acceptance Criteria
- The exact video path can be executed end-to-end without dead clicks.
- Explorer visibly demonstrates AI/RAG value in-page.
- Recommendations, Campaigns, and Admin scenes are coherent for filming.
- Decorative controls in filmed scenes no longer undermine credibility.
- Backend data shown in the video remains real.
- Target verification passes for the demo branch.

## Demo-Focused Verification
- `python -m pytest tests/test_auth.py tests/test_api.py -q --tb=no`
- `npx.cmd tsc`
- `node --test frontend/tests/stitchTextFidelity.test.mjs`
- targeted visual or smoke checks for the demo path

## Branching
- Branch name: `feat/demo-video-path`
- Worktree path: `g:\ramypulse\.worktrees\feat-demo-video-path`

## Success Definition
Success is not "the whole site is complete."

Success is:
- the video tells a coherent product story
- every shown interaction works
- no important filmed area looks fake or broken
- the changes do not compromise the existing architecture
