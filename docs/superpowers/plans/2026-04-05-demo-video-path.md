# Demo Video Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the exact competition demo path reliable, honest, and stable without trying to finish the entire product.

**Architecture:** Keep the existing product pages and backend contracts, then harden only the filmed path. Add a visible AI/RAG surface inside Explorer, neutralize decorative controls on filmed pages, and preserve the real Stitch-driven product structure.

**Tech Stack:** React, TypeScript, Wouter, TanStack Query, FastAPI, pytest, Node test runner, Playwright

---

## File Structure

### Existing files to modify
- `frontend/client/src/components/AppShell.tsx`
  - shared header controls for product pages
- `frontend/client/src/pages/Explorateur.tsx`
  - search page that already talks to `/api/explorer/search`
- `frontend/client/src/pages/Recommandations.tsx`
  - recommendation generation and active cards
- `frontend/client/src/pages/Campagnes.tsx`
  - campaign overview and create form
- `frontend/client/src/pages/AdminSources.tsx`
  - dedicated admin shell
- `frontend/client/src/components/admin/AdminSourcesOps.tsx`
  - real admin internal subviews
- `frontend/tests/stitchTextFidelity.test.mjs`
  - copy/fidelity guardrails
- `frontend/tests/visual/adminSources.visual.spec.ts`
  - targeted admin visual smoke

### New files to create
- `frontend/client/src/lib/demoMode.ts`
  - one tiny source of truth for demo-specific UI guards
- `frontend/client/src/lib/explorerAiView.ts`
  - pure mapper for turning search payload into an Explorer AI insight block
- `frontend/tests/explorerAiView.test.ts`
  - pure unit coverage for the new AI insight mapper
- `docs/demo-video-script.md`
  - exact click path and narration for recording

---

### Task 1: Add a tiny demo-mode UI guard

**Files:**
- Create: `frontend/client/src/lib/demoMode.ts`
- Modify: `frontend/client/src/components/AppShell.tsx`
- Test: `frontend/tests/stitchTextFidelity.test.mjs`

- [ ] **Step 1: Write the failing copy test for demo-safe controls**

```js
test("Shared shell keeps Stitch branding while avoiding fake interactive labels in demo mode", async () => {
  const source = await fs.readFile(
    path.join(repoRoot, "frontend/client/src/components/AppShell.tsx"),
    "utf8",
  );
  assert.match(source, /data-demo-disabled/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/stitchTextFidelity.test.mjs`
Expected: FAIL because `data-demo-disabled` is not present yet.

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/client/src/lib/demoMode.ts
export const DEMO_MODE = true;

export function demoDisabledProps(label: string) {
  return DEMO_MODE
    ? {
        "aria-disabled": true,
        "data-demo-disabled": label,
        tabIndex: -1,
      }
    : {};
}
```

```tsx
// frontend/client/src/components/AppShell.tsx
import { demoDisabledProps } from "@/lib/demoMode";

<button
  className="material-symbols-outlined hover:text-white transition-colors"
  {...demoDisabledProps("language")}
>
  language
</button>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/stitchTextFidelity.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/client/src/lib/demoMode.ts frontend/client/src/components/AppShell.tsx frontend/tests/stitchTextFidelity.test.mjs
git commit -m "feat(demo): add demo-safe shell controls"
```

### Task 2: Make Explorer visibly demonstrate AI/RAG in-page

**Files:**
- Create: `frontend/client/src/lib/explorerAiView.ts`
- Modify: `frontend/client/src/pages/Explorateur.tsx`
- Test: `frontend/tests/explorerAiView.test.ts`
- Test: `frontend/tests/stitchTextFidelity.test.mjs`

- [ ] **Step 1: Write the failing unit test for AI insight mapping**

```ts
import test from "node:test";
import assert from "node:assert/strict";
import { buildExplorerAiView } from "../client/src/lib/explorerAiView";

test("buildExplorerAiView summarizes the strongest search results", () => {
  const view = buildExplorerAiView([
    { source: "facebook", sentiment: "positif", aspect: "goût", content: "Très bon goût", relevance_score: 92 },
    { source: "facebook", sentiment: "négatif", aspect: "prix", content: "Prix trop élevé", relevance_score: 81 },
  ]);

  assert.equal(view.title, "AI Insight");
  assert.match(view.summary, /goût|prix/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx.cmd tsx --test frontend/tests/explorerAiView.test.ts`
Expected: FAIL because `buildExplorerAiView` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```ts
export interface ExplorerAiView {
  title: string;
  summary: string;
  bullets: string[];
}

export function buildExplorerAiView(results: Array<{
  source: string;
  sentiment: string;
  aspect: string;
  content: string;
  relevance_score: number;
}>): ExplorerAiView | null {
  if (!results.length) return null;
  const top = results.slice(0, 3);
  return {
    title: "AI Insight",
    summary: `Top signals mention ${top.map((item) => item.aspect).filter(Boolean).join(", ")}.`,
    bullets: top.map((item) => `${item.sentiment} • ${item.aspect} • ${item.source}`),
  };
}
```

```tsx
const aiInsight = useMemo(() => buildExplorerAiView(searchResults), [searchResults]);

{aiInsight ? (
  <section data-testid="explorer-ai-insight" className="bg-surface-container rounded-xl p-6">
    <p className="text-[10px] font-bold uppercase tracking-widest text-tertiary">{aiInsight.title}</p>
    <p className="text-sm mt-2 text-on-surface">{aiInsight.summary}</p>
  </section>
) : null}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
- `npx.cmd tsx --test frontend/tests/explorerAiView.test.ts`
- `node --test frontend/tests/stitchTextFidelity.test.mjs`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/client/src/lib/explorerAiView.ts frontend/client/src/pages/Explorateur.tsx frontend/tests/explorerAiView.test.ts frontend/tests/stitchTextFidelity.test.mjs
git commit -m "feat(demo): add in-page explorer ai insight"
```

### Task 3: Remove decorative traps from Recommendations and Campaigns

**Files:**
- Modify: `frontend/client/src/pages/Recommandations.tsx`
- Modify: `frontend/client/src/pages/Campagnes.tsx`
- Test: `frontend/tests/stitchTextFidelity.test.mjs`

- [ ] **Step 1: Write failing fidelity checks for known dead controls**

```js
test("Recommendations no longer exposes decorative more_vert control on active cards", async () => {
  const source = await fs.readFile(
    path.join(repoRoot, "frontend/client/src/pages/Recommandations.tsx"),
    "utf8",
  );
  assert.doesNotMatch(source, /more_vert/);
});

test("Campagnes no longer exposes decorative EXPORTER DATA CTA", async () => {
  const source = await fs.readFile(
    path.join(repoRoot, "frontend/client/src/pages/Campagnes.tsx"),
    "utf8",
  );
  assert.doesNotMatch(source, /EXPORTER DATA/);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test frontend/tests/stitchTextFidelity.test.mjs`
Expected: FAIL because both strings exist today.

- [ ] **Step 3: Write minimal implementation**

```tsx
// Recommandations.tsx
<div className="flex justify-between items-start mb-4">
  <PriorityBadge priority={recommendation.priority} />
</div>
```

```tsx
// Campagnes.tsx
<div className="flex gap-3">
  <div className="px-4 py-2 bg-surface-container-high text-on-surface-variant text-xs font-bold rounded-sm opacity-60">
    DONNÉES CAMPAGNES
  </div>
</div>
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
- `node --test frontend/tests/stitchTextFidelity.test.mjs`
- `npx.cmd tsc`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/client/src/pages/Recommandations.tsx frontend/client/src/pages/Campagnes.tsx frontend/tests/stitchTextFidelity.test.mjs
git commit -m "fix(demo): remove decorative recommendation and campaign traps"
```

### Task 4: Make Admin safe for filming

**Files:**
- Modify: `frontend/client/src/pages/AdminSources.tsx`
- Modify: `frontend/client/src/components/admin/AdminSourcesOps.tsx`
- Test: `frontend/tests/stitchTextFidelity.test.mjs`
- Test: `frontend/tests/visual/adminSources.visual.spec.ts`

- [ ] **Step 1: Write failing test for subdued non-functional admin shell items**

```js
test("Admin shell marks non-functional outer controls as demo-disabled", async () => {
  const source = await fs.readFile(
    path.join(repoRoot, "frontend/client/src/pages/AdminSources.tsx"),
    "utf8",
  );
  assert.match(source, /data-demo-disabled/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/stitchTextFidelity.test.mjs`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```tsx
<a
  className="text-gray-500 pointer-events-none opacity-50"
  data-demo-disabled="admin-shell-item"
>
  Pipelines
</a>
```

```ts
test("admin scheduler view still renders inside dedicated shell", async ({ page }) => {
  await page.goto("/#/admin-sources?view=scheduler");
  await expect(page.getByTestId("admin-shell-canvas")).toBeVisible();
  await expect(page.getByText("Run due syncs")).toBeVisible();
});
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
- `node --test frontend/tests/stitchTextFidelity.test.mjs`
- `npx.cmd playwright test frontend/tests/visual/adminSources.visual.spec.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/client/src/pages/AdminSources.tsx frontend/client/src/components/admin/AdminSourcesOps.tsx frontend/tests/stitchTextFidelity.test.mjs frontend/tests/visual/adminSources.visual.spec.ts
git commit -m "fix(demo): make admin shell safe for recording"
```

### Task 5: Document and verify the exact video path

**Files:**
- Create: `docs/demo-video-script.md`
- Modify: `frontend/tests/stitchTextFidelity.test.mjs`

- [ ] **Step 1: Write the demo path document**

```md
# Demo Video Script

1. Open `#/`
2. Open `#/explorateur`
3. Search for the prepared query
4. Show AI Insight block
5. Open `#/alertes`
6. Open `#/recommandations`
7. Open `#/campagnes`
8. Open `#/admin-sources?view=scheduler`
```

- [ ] **Step 2: Add a fidelity guard that demo scenes still exist**

```js
test("Demo path labels remain present", async () => {
  const explorer = await fs.readFile(path.join(repoRoot, "frontend/client/src/pages/Explorateur.tsx"), "utf8");
  assert.match(explorer, /AI Insight/);
  const admin = await fs.readFile(path.join(repoRoot, "frontend/client/src/components/admin/AdminSourcesOps.tsx"), "utf8");
  assert.match(admin, /Run due syncs/);
});
```

- [ ] **Step 3: Run the verification commands**

Run:
- `python -m pytest tests/test_auth.py tests/test_api.py -q --tb=no`
- `npx.cmd tsc`
- `node --test frontend/tests/stitchTextFidelity.test.mjs`

Expected:
- backend tests PASS
- TypeScript PASS
- fidelity tests PASS

- [ ] **Step 4: Commit**

```bash
git add docs/demo-video-script.md frontend/tests/stitchTextFidelity.test.mjs
git commit -m "docs(demo): add final video path script"
```

---

## P0
- Task 1
- Task 2
- Task 3
- Task 4

## P1
- Task 5

## Self-Review
- Spec coverage: every mandatory filmed scene is represented by a task.
- Placeholder scan: no `TBD`, `TODO`, or vague "handle later" steps remain.
- Type consistency: new demo helpers are isolated and do not require backend contract changes.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-05-demo-video-path.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
