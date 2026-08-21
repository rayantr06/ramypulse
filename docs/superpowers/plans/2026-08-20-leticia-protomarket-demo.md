# Leticia ProtoMarket Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a deterministic, frontend-only LIDAL Pulse demo that Leticia can install, launch, reset and record on Windows without private data, API keys, a backend, or a phone QR scan.

**Architecture:** The existing React/Vite V3 UI remains the product shell. A focused local demo repository supplies sanitized multilingual fixtures and QR submissions through `localStorage`; a same-origin public-feedback route opens in a second browser tab. PowerShell scripts install and launch only the frontend, while versioned French guides provide the exact recording path and narration.

**Tech Stack:** React 18, TypeScript 5.6 strict, Vite 7, TanStack Query 5, Wouter, Tailwind/Shadcn, `qrcode.react`, Playwright, Node test runner, PowerShell 5.1+.

**Spec:** `docs/superpowers/specs/2026-08-20-leticia-protomarket-demo-design.md`

## Global Constraints

- Work only in `G:\ramypulse-leticia-demo` on branch `codex/lidal-pulse-leticia-demo`.
- Do not modify `api/` or `frontend/shared/schema.ts`.
- Do not commit `.env`, SQLite databases, the full training corpus, credentials, real personal data, or external provider tokens.
- The recording path must run without Python, FastAPI, Supabase, Gemini, OpenAI, Apify, or an internet connection after `npm ci`.
- Use only sanitized fixtures and `https://example.invalid/...` source URLs.
- Demo channels are `facebook`, `google_maps`, `audio`, and `youtube`.
- The central business story is availability in Oran; every alert, source excerpt and recommended action must support that same story.
- The UI must say that SLM outputs are prepared demonstration examples and that the trained model is still being validated.
- The QR path opens in a second tab on the same computer; do not add a public tunnel or phone-network dependency.
- Preserve TanStack Query tenant isolation with query keys shaped as `['/api/endpoint', { clientId, ...params }]`.
- Every mutation must include an `onError` destructive toast.
- Use only existing CSS design tokens; do not hardcode new colors.
- Final verification requires `npm run check`, `npm run build`, `npm run test:quality`, the dedicated demo E2E test, and a manual 1920 × 1080 pass.

---

## File Map

### Create

- `frontend/client/src/lib/leticiaDemoScenario.ts` — coherent multilingual demo fixtures and cross-record validation helpers.
- `frontend/client/src/lib/leticiaDemoState.ts` — namespaced storage access and reset function.
- `frontend/client/src/lib/listeningPoints.ts` — QR point and submission domain repository.
- `frontend/client/src/hooks/useListeningPoints.ts` — tenant-scoped TanStack Query adapters.
- `frontend/client/src/components/listening/ListeningPointComposer.tsx` — three-step QR creation form.
- `frontend/client/src/components/demo/DemoSourceFlow.tsx` — compact source → SLM → proof → decision explanation.
- `frontend/client/src/pages/ListeningPoints.tsx` — QR management surface.
- `frontend/client/src/pages/PublicFeedback.tsx` — same-origin public feedback form.
- `frontend/client/src/pages/DemoReset.tsx` — deterministic reset and redirect route.
- `frontend/tests/leticiaDemoScenario.test.ts` — fixture integrity and truthfulness tests.
- `frontend/tests/listeningPoints.test.ts` — repository behavior tests.
- `frontend/tests/e2e/leticiaDemo.spec.ts` — complete recording golden path.
- `scripts/leticia/INSTALLER_DEMO_LETICIA.ps1` — prerequisite check and reproducible install.
- `scripts/leticia/LANCER_DEMO_LETICIA.ps1` — safe local launcher.
- `scripts/leticia/REINITIALISER_DEMO.ps1` — opens the local reset route.
- `docs/protomarket_ii_2026/demo_leticia/00_LIRE_EN_PREMIER.md`
- `docs/protomarket_ii_2026/demo_leticia/01_INSTALLATION_WINDOWS.md`
- `docs/protomarket_ii_2026/demo_leticia/02_SCRIPT_VIDEO_PROTOTYPE.md`
- `docs/protomarket_ii_2026/demo_leticia/03_SCRIPT_PITCH_3_MINUTES.md`
- `docs/protomarket_ii_2026/demo_leticia/04_CHECKLIST_AVANT_TOURNAGE.md`
- `docs/protomarket_ii_2026/demo_leticia/05_DEPANNAGE_RAPIDE.md`
- `docs/protomarket_ii_2026/demo_leticia/06_MESSAGE_A_ENVOYER_A_LETICIA.md`

### Modify

- `frontend/package.json` and `frontend/package-lock.json` — add `qrcode.react` and the dedicated demo test command.
- `frontend/client/src/App.tsx` — register points, public feedback and reset routes.
- `frontend/client/src/lib/productNavigation.ts` — add the points-of-listening navigation item.
- `frontend/client/src/lib/routeAccess.ts` — keep public feedback and reset outside the tenant gate.
- `frontend/client/src/lib/v3DemoData.ts` — export the coherent Oran scenario through existing V3 constants.
- `frontend/client/src/pages/Dashboard.tsx` — add the source flow and recording-safe links.
- `frontend/client/src/pages/Explorateur.tsx` — show prepared SLM justification and honest demo label.
- `frontend/client/src/components/explorer/SignalAnalysisPanel.tsx` — expose evidence, structured output and demo provenance.
- `frontend/tests/pageContracts.test.mjs` — enforce new route/page copy contracts.
- `frontend/tests/e2e/productGoldenPaths.spec.ts` — retain existing golden paths and add QR route coverage if shared setup is required.
- `frontend/client/src/components/BrandMark.tsx` and `frontend/client/index.html` — use official LIDAL assets.
- `frontend/client/public/brand/*` — add normalized official logo filenames.

---

### Task 1: Deterministic Scenario and Namespaced Demo State

**Files:**
- Create: `frontend/client/src/lib/leticiaDemoScenario.ts`
- Create: `frontend/client/src/lib/leticiaDemoState.ts`
- Create: `frontend/tests/leticiaDemoScenario.test.ts`
- Modify: `frontend/client/src/lib/v3DemoData.ts`
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `LETICIA_DEMO_STORAGE_PREFIX: 'lidal.demo.leticia.'`
- Produces: `resetLeticiaDemoState(storage: Pick<Storage, 'key' | 'length' | 'removeItem'>): void`
- Produces: `LETICIA_DEMO_SCENARIO` with `mentions`, `monitors`, `observations`, `signals`, `cases`, `actions`, `overview`, `reports`, and `notifications` matching `frontend/shared/v3.ts`.
- Produces: `validateLeticiaDemoScenario(): string[]`, returning an empty array for valid fixtures.
- Consumes: existing V3 domain types from `frontend/shared/v3.ts`.

- [ ] **Step 1: Write the failing scenario integrity tests**

```ts
import assert from "node:assert/strict";
import test from "node:test";
import { LETICIA_DEMO_SCENARIO, validateLeticiaDemoScenario } from "../client/src/lib/leticiaDemoScenario";
import { LETICIA_DEMO_STORAGE_PREFIX, resetLeticiaDemoState } from "../client/src/lib/leticiaDemoState";

test("Leticia scenario is internally coherent and auditable", () => {
  assert.deepEqual(validateLeticiaDemoScenario(), []);
  assert.ok(LETICIA_DEMO_SCENARIO.mentions.some((item) => item.language === "darija_arabizi"));
  assert.ok(LETICIA_DEMO_SCENARIO.mentions.some((item) => item.language === "darija_arabe"));
  assert.ok(LETICIA_DEMO_SCENARIO.mentions.every((item) => item.sourceUrl.startsWith("https://example.invalid/")));
  assert.ok(LETICIA_DEMO_SCENARIO.signals.every((signal) => signal.evidenceIds.length > 0));
  assert.match(LETICIA_DEMO_SCENARIO.signals[0]!.title, /disponibilit/i);
  assert.match(LETICIA_DEMO_SCENARIO.signals[0]!.territory ?? "", /Oran/i);
});

test("reset removes only Leticia demo keys", () => {
  const values = new Map([[`${LETICIA_DEMO_STORAGE_PREFIX}points`, "[]"], ["unrelated", "keep"]]);
  const storage = {
    get length() { return values.size; },
    key(index: number) { return [...values.keys()][index] ?? null; },
    removeItem(key: string) { values.delete(key); },
  };
  resetLeticiaDemoState(storage);
  assert.equal(values.has(`${LETICIA_DEMO_STORAGE_PREFIX}points`), false);
  assert.equal(values.get("unrelated"), "keep");
});
```

- [ ] **Step 2: Run the tests and confirm the missing modules fail**

Run: `cd frontend; npx tsx --test tests/leticiaDemoScenario.test.ts`

Expected: FAIL with module-not-found errors for `leticiaDemoScenario` and `leticiaDemoState`.

- [ ] **Step 3: Implement storage reset and the minimum coherent fixtures**

Use this storage contract:

```ts
export const LETICIA_DEMO_STORAGE_PREFIX = "lidal.demo.leticia." as const;

export function resetLeticiaDemoState(
  storage: Pick<Storage, "key" | "length" | "removeItem">,
): void {
  const keys = Array.from({ length: storage.length }, (_, index) => storage.key(index))
    .filter((key): key is string => Boolean(key?.startsWith(LETICIA_DEMO_STORAGE_PREFIX)));
  keys.forEach((key) => storage.removeItem(key));
}
```

Create 8–12 sanitized mentions. The central evidence set must include these prepared comments and exact substrings:

```ts
const availabilityEvidence = [
  {
    id: "m_oran_arabizi_01",
    text: "Ma l9itch le produit fi Oran depuis trois jours.",
    evidence: "Ma l9itch le produit fi Oran",
    language: "darija_arabizi",
    source: "facebook",
  },
  {
    id: "m_oran_arabe_02",
    text: "المنتج ماكانش متوفر في المحل بوهران هذا الأسبوع",
    evidence: "ماكانش متوفر في المحل بوهران",
    language: "darija_arabe",
    source: "google_maps",
  },
  {
    id: "m_oran_fr_03",
    text: "Produit indisponible dans deux points de vente à Oran.",
    evidence: "Produit indisponible",
    language: "francais",
    source: "youtube",
  },
] as const;
```

The signal must reference those mention IDs, use aspect `disponibilite`, territory `Oran`, and recommend verifying stock before a targeted replenishment. `validateLeticiaDemoScenario()` must verify all evidence IDs exist, all evidence substrings occur in the source text, every source URL is non-real, and every action belongs to an existing case.

- [ ] **Step 4: Wire existing `V3_DEMO_*` exports to the new scenario**

Keep existing import names stable in `useV3Data.ts`. In `v3DemoData.ts`, re-export or assign each existing constant from `LETICIA_DEMO_SCENARIO`; do not change API/live-mode behavior.

- [ ] **Step 5: Add the test to the quality command and run it**

Modify `test:quality` to include `tests/leticiaDemoScenario.test.ts` in the `tsx --test` group.

Run: `cd frontend; npx tsx --test tests/leticiaDemoScenario.test.ts`

Expected: 2 tests PASS.

- [ ] **Step 6: Commit the deterministic scenario**

```powershell
git add frontend/client/src/lib/leticiaDemoScenario.ts frontend/client/src/lib/leticiaDemoState.ts frontend/client/src/lib/v3DemoData.ts frontend/tests/leticiaDemoScenario.test.ts frontend/package.json
git commit -m "feat(demo): add coherent Leticia recording scenario"
```

---

### Task 2: Listening-Point Repository and Tenant-Scoped Hooks

**Files:**
- Create: `frontend/client/src/lib/listeningPoints.ts`
- Create: `frontend/client/src/hooks/useListeningPoints.ts`
- Create: `frontend/tests/listeningPoints.test.ts`

**Interfaces:**
- Consumes: `LETICIA_DEMO_STORAGE_PREFIX` from Task 1.
- Produces: `ListeningPoint`, `ListeningPointSubmission`, `ListeningPointCreateInput`, and `ListeningPointStatus` types.
- Produces: `createListeningPointsRepository(storage, clock, makeId): ListeningPointsRepository`.
- Produces: `useListeningPoints()`, `useListeningPointSubmissions(pointId)`, `useCreateListeningPoint()`, `useSubmitListeningPointFeedback()`, and `useSetListeningPointStatus()`.

- [ ] **Step 1: Write repository tests before implementation**

```ts
test("repository records a same-origin QR submission as pending", () => {
  const repository = createListeningPointsRepository(memoryStorage(), () => "2026-08-20T12:00:00Z", () => "fixed-id");
  const point = repository.findByToken("produit-pilote-demo");
  assert.ok(point);
  const submission = repository.submit({
    organizationId: point.organizationId,
    listeningPointId: point.id,
    rating: 2,
    text: "Ma l9itch le produit fi Oran.",
    channels: ["text"],
    imageName: null,
    audioDurationSeconds: null,
    consent: true,
  });
  assert.equal(submission.validationStatus, "pending");
  assert.equal(repository.listSubmissions(point.id).length, 1);
});

test("repository isolates points by organization", () => {
  const repository = createListeningPointsRepository(memoryStorage(), () => "2026-08-20T12:00:00Z", () => "fixed-id");
  assert.ok(repository.list("demo-expo-2026").length > 0);
  assert.deepEqual(repository.list("another-tenant"), []);
});
```

- [ ] **Step 2: Run the repository tests and confirm failure**

Run: `cd frontend; npx tsx --test tests/listeningPoints.test.ts`

Expected: FAIL because `listeningPoints.ts` does not exist.

- [ ] **Step 3: Implement an injectable local repository**

Define the repository interface exactly:

```ts
export interface ListeningPointsRepository {
  list(organizationId: string): ListeningPoint[];
  findByToken(token: string): ListeningPoint | null;
  create(input: ListeningPointCreateInput): ListeningPoint;
  setStatus(id: string, status: ListeningPointStatus): ListeningPoint;
  recordScan(token: string): void;
  submit(input: ListeningPointSubmissionInput): ListeningPointSubmission;
  listSubmissions(listeningPointId: string): ListeningPointSubmission[];
}
```

Seed three deterministic points, including the active `Produit pilote 1 L` token `produit-pilote-demo`. Store points and submissions under `${LETICIA_DEMO_STORAGE_PREFIX}listening-points` and `${LETICIA_DEMO_STORAGE_PREFIX}listening-point-submissions`. Never clear unrelated browser keys.

- [ ] **Step 4: Implement TanStack Query hooks with tenant isolation**

Use these query keys:

```ts
["/api/v3/listening-points", { clientId: organizationId }]
["/api/v3/listening-point-submissions", { clientId: organizationId, pointId }]
```

Each mutation must update or invalidate both affected keys and include:

```ts
onError: (error: Error) => toast({
  variant: "destructive",
  title: "Opération impossible",
  description: error.message,
})
```

- [ ] **Step 5: Run repository and TypeScript tests**

Run: `cd frontend; npx tsx --test tests/listeningPoints.test.ts; npm run check`

Expected: repository tests PASS and TypeScript exits 0.

- [ ] **Step 6: Commit the repository layer**

```powershell
git add frontend/client/src/lib/listeningPoints.ts frontend/client/src/hooks/useListeningPoints.ts frontend/tests/listeningPoints.test.ts
git commit -m "feat(demo): add local QR listening repository"
```

---

### Task 3: QR Management, Public Feedback and Reset Routes

**Files:**
- Create: `frontend/client/src/components/listening/ListeningPointComposer.tsx`
- Create: `frontend/client/src/pages/ListeningPoints.tsx`
- Create: `frontend/client/src/pages/PublicFeedback.tsx`
- Create: `frontend/client/src/pages/DemoReset.tsx`
- Modify: `frontend/client/src/App.tsx`
- Modify: `frontend/client/src/lib/productNavigation.ts`
- Modify: `frontend/client/src/lib/routeAccess.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/tests/pageContracts.test.mjs`
- Modify: `frontend/tests/e2e/productGoldenPaths.spec.ts`

**Interfaces:**
- Consumes: repository and hooks from Task 2.
- Consumes: `resetLeticiaDemoState(window.localStorage)` from Task 1.
- Produces routes `/listening-points`, `/listening-points/new`, `/feedback/:token`, and `/demo/reset`.
- Produces test IDs `listening-points-page`, `listening-point-qr`, `public-feedback-form`, and `pending-submission`.

- [ ] **Step 1: Add failing page-contract assertions**

```js
test("QR listening pages expose the reliable recording path", () => {
  const points = readPage("ListeningPoints.tsx");
  const feedback = readPage("PublicFeedback.tsx");
  const reset = readPage("DemoReset.tsx");
  assert.ok(points.includes('data-testid="listening-point-qr"'));
  assert.ok(points.includes("Tester le formulaire"));
  assert.ok(feedback.includes('data-testid="public-feedback-form"'));
  assert.ok(feedback.includes("En attente d’analyse"));
  assert.ok(reset.includes("resetLeticiaDemoState"));
});
```

- [ ] **Step 2: Run the page contract and confirm failure**

Run: `cd frontend; node --test tests/pageContracts.test.mjs`

Expected: FAIL because the pages are absent.

- [ ] **Step 3: Add the QR dependency and implement the composer**

Run: `cd frontend; npm install qrcode.react@^4.2.0`

The composer must use React Hook Form and Zod and collect only: target type/name, internal name, responsible person, enabled channels, low-rating alert and threshold. Submit through `useCreateListeningPoint`; cancel through Wouter navigation.

- [ ] **Step 4: Implement the management and public pages**

`ListeningPoints.tsx` must show deterministic metrics, a real `QRCodeSVG`, download/copy buttons, `Tester le formulaire` with `target="_blank"`, and the latest local submissions. `PublicFeedback.tsx` must accept rating plus at least one enabled channel, require consent, submit locally, and display a success page that explicitly says the result is pending analysis.

Do not claim that audio bytes or photos are uploaded. Keep only local duration and filename metadata.

- [ ] **Step 5: Implement the reset route and route access**

`DemoReset.tsx` must call `resetLeticiaDemoState`, clear the TanStack Query cache, show « Démonstration réinitialisée », and redirect to `/` after 800 ms. Keep `/feedback/:token` and `/demo/reset` outside `TenantProtectedRoute`.

- [ ] **Step 6: Add the first QR E2E golden path**

```ts
test("public QR feedback returns to the point as pending", async ({ context, page }) => {
  await page.goto("/#/listening-points");
  const popupPromise = context.waitForEvent("page");
  await page.getByRole("link", { name: "Tester le formulaire" }).click();
  const feedback = await popupPromise;
  await feedback.getByRole("radio", { name: "2 étoiles" }).click();
  await feedback.getByLabel("Votre message").fill("Ma l9itch le produit fi Oran.");
  await feedback.getByRole("checkbox").check();
  await feedback.getByRole("button", { name: "Envoyer mon retour" }).click();
  await expect(feedback.getByText("En attente d’analyse")).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("pending-submission")).toContainText("Ma l9itch le produit fi Oran.");
});
```

- [ ] **Step 7: Run focused tests and build**

Run: `cd frontend; node --test tests/pageContracts.test.mjs; npm run check; npm run build; npx playwright test tests/e2e/productGoldenPaths.spec.ts`

Expected: all commands exit 0.

- [ ] **Step 8: Commit the QR surfaces**

```powershell
git add frontend/package.json frontend/package-lock.json frontend/client/src/App.tsx frontend/client/src/lib/productNavigation.ts frontend/client/src/lib/routeAccess.ts frontend/client/src/components/listening frontend/client/src/pages/ListeningPoints.tsx frontend/client/src/pages/PublicFeedback.tsx frontend/client/src/pages/DemoReset.tsx frontend/tests/pageContracts.test.mjs frontend/tests/e2e/productGoldenPaths.spec.ts
git commit -m "feat(demo): add reliable QR feedback recording path"
```

---

### Task 4: Source Flow and Honest SLM Justification

**Files:**
- Create: `frontend/client/src/components/demo/DemoSourceFlow.tsx`
- Modify: `frontend/client/src/pages/Dashboard.tsx`
- Modify: `frontend/client/src/pages/Explorateur.tsx`
- Modify: `frontend/client/src/components/explorer/SignalAnalysisPanel.tsx`
- Modify: `frontend/tests/pageContracts.test.mjs`
- Create: `frontend/tests/e2e/leticiaDemo.spec.ts`

**Interfaces:**
- Consumes: `LETICIA_DEMO_SCENARIO` and existing `parseSlmAnalysis` helpers.
- Produces: `DemoSourceFlow` with four sources, SLM transformation, evidence/alert and human-decision steps.
- Produces test IDs `demo-source-flow`, `demo-slm-provenance`, and `demo-structured-output`.

- [ ] **Step 1: Write failing copy and E2E expectations**

```ts
test("recording path explains source to decision without overclaiming", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByTestId("demo-source-flow")).toContainText("Facebook");
  await expect(page.getByTestId("demo-source-flow")).toContainText("Google Maps");
  await expect(page.getByTestId("demo-source-flow")).toContainText("YouTube");
  await expect(page.getByTestId("demo-source-flow")).toContainText("Audio autorisé");
  await page.goto("/#/explorateur");
  await expect(page.getByTestId("demo-slm-provenance")).toContainText("exemple de démonstration");
  await expect(page.getByTestId("demo-structured-output")).toContainText("Disponibilité");
  await expect(page.getByTestId("signal-analysis-panel")).toContainText("Ma l9itch le produit fi Oran");
});
```

- [ ] **Step 2: Run the E2E test and confirm missing UI failure**

Run: `cd frontend; npx playwright test tests/e2e/leticiaDemo.spec.ts`

Expected: FAIL on missing `demo-source-flow`.

- [ ] **Step 3: Implement the compact source flow**

Render this exact conceptual sequence in `DemoSourceFlow`:

```text
Facebook · Google Maps · YouTube · Audio autorisé · QR
→ LIDAL AI comprend la langue et le contexte
→ preuve exacte + aspect + alerte
→ décision validée par l’équipe
```

Use existing cards/tokens and keep the component under 160 lines. Place it below the Dashboard header and above KPI cards so it is fully visible without scrolling at 1920 × 1080.

- [ ] **Step 4: Add honest SLM provenance and structured output**

The Explorer/analysis panel must show:

```text
Analyse du SLM — exemple de démonstration
Le modèle spécialisé est en cours de validation. Cette sortie préparée montre le contrat produit visé.
```

Render input, exact evidence, sentiment, aspect, intent, alert and confidence. Do not render free-form hidden reasoning or claim live inference latency.

- [ ] **Step 5: Run focused and regression tests**

Run: `cd frontend; npx playwright test tests/e2e/leticiaDemo.spec.ts; npm run check; npm run build`

Expected: E2E PASS, TypeScript PASS, build PASS.

- [ ] **Step 6: Commit the explanatory flow**

```powershell
git add frontend/client/src/components/demo/DemoSourceFlow.tsx frontend/client/src/pages/Dashboard.tsx frontend/client/src/pages/Explorateur.tsx frontend/client/src/components/explorer/SignalAnalysisPanel.tsx frontend/tests/pageContracts.test.mjs frontend/tests/e2e/leticiaDemo.spec.ts
git commit -m "feat(demo): explain sources SLM evidence and decision flow"
```

---

### Task 5: Windows Installer, Launcher and Reset Scripts

**Files:**
- Create: `scripts/leticia/INSTALLER_DEMO_LETICIA.ps1`
- Create: `scripts/leticia/LANCER_DEMO_LETICIA.ps1`
- Create: `scripts/leticia/REINITIALISER_DEMO.ps1`
- Create: `tests/test_leticia_demo_scripts.py`

**Interfaces:**
- Produces: scripts callable from any current directory.
- Produces: local URL `http://127.0.0.1:5173/#/` and reset URL `http://127.0.0.1:5173/#/demo/reset`.

- [ ] **Step 1: Write static safety tests for the scripts**

```python
def test_leticia_scripts_are_path_safe_and_frontend_only():
    installer = INSTALLER.read_text(encoding="utf-8")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    reset = RESET.read_text(encoding="utf-8")
    assert "$PSScriptRoot" in installer
    assert "npm ci" in installer
    assert "uvicorn" not in installer + launcher
    assert "Start-Process" in launcher
    assert "-WindowStyle Hidden" in launcher
    assert "#/demo/reset" in reset
    assert "Stop-Process" in launcher
```

- [ ] **Step 2: Run the test and confirm missing scripts failure**

Run: `python -m pytest tests/test_leticia_demo_scripts.py -q`

Expected: FAIL because the script files do not exist.

- [ ] **Step 3: Implement the installer**

Resolve repository and frontend roots relative to `$PSScriptRoot`. Require Node 20 or 22 and `npm.cmd`. Run `npm ci` in `frontend`. Create `frontend/.env.local` only when absent with:

```text
VITE_RAMYPULSE_DEMO_MODE=true
VITE_RAMYPULSE_DEFAULT_TENANT_ID=demo-expo-2026
VITE_LIDAL_V3_API_ENABLED=false
```

Do not overwrite an existing environment file.

- [ ] **Step 4: Implement safe launcher and reset scripts**

The launcher must detect port 5173 before spawning Node, start `node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173` hidden, poll the URL for up to 30 seconds, open the browser, and stop only the process object it created after the user presses Enter. The reset script only opens the reset URL and never edits arbitrary browser files.

- [ ] **Step 5: Run script safety tests and a local smoke**

Run: `python -m pytest tests/test_leticia_demo_scripts.py -q`

Then run manually:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\INSTALLER_DEMO_LETICIA.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\LANCER_DEMO_LETICIA.ps1
```

Expected: browser opens on `/#/`, no backend process starts, and Enter stops only Vite.

- [ ] **Step 6: Commit the Windows package**

```powershell
git add scripts/leticia tests/test_leticia_demo_scripts.py
git commit -m "chore(demo): add one-click Leticia Windows launcher"
```

---

### Task 6: Official Branding and Recording Guides

**Files:**
- Modify: `frontend/client/src/components/BrandMark.tsx`
- Modify: `frontend/client/index.html`
- Create/Modify: `frontend/client/public/brand/lidal-mark-dark.png`
- Create/Modify: `frontend/client/public/brand/lidal-mark-transparent.png`
- Create: all seven files under `docs/protomarket_ii_2026/demo_leticia/`
- Modify: `frontend/tests/e2e/brandIdentity.spec.ts`

**Interfaces:**
- Consumes official source logos from `C:\Users\AZ\Downloads\Logo LIDAL.png`, `Logo_fond_black.png`, and `Logo_retirerbackground.png`.
- Produces stable public asset paths `/brand/lidal-mark-dark.png` and `/brand/lidal-mark-transparent.png`.
- Produces exact installation, narration, checklist, troubleshooting and handoff copy.

- [ ] **Step 1: Extend the brand test before copying assets**

```ts
test("Leticia demo uses the official local LIDAL mark", async ({ page }) => {
  await page.goto("/#/");
  const logo = page.getByRole("img", { name: "LIDAL Pulse" }).first();
  await expect(logo).toHaveAttribute("src", /\/brand\/lidal-mark-dark\.png$/);
  const response = await page.request.get("/brand/lidal-mark-dark.png");
  expect(response.ok()).toBeTruthy();
});
```

- [ ] **Step 2: Run the brand test and confirm expected failure**

Run: `cd frontend; npx playwright test tests/e2e/brandIdentity.spec.ts`

Expected: FAIL until official stable paths are present.

- [ ] **Step 3: Inspect and normalize the official assets**

Visually inspect all three source images. Copy the dark-background and transparent variants to the stable names without modifying pixels. Record their SHA-256 hashes in `00_LIRE_EN_PREMIER.md`. Do not copy unrelated Downloads files.

- [ ] **Step 4: Wire brand assets and favicon**

Use the dark-background asset in `BrandMark` for the Obsidian shell and the transparent variant for favicon/end-card references. Preserve accessible alt text `LIDAL Pulse`.

- [ ] **Step 5: Write the seven French handoff documents**

The prototype script must follow the eight timed scenes in the spec and include exact route/click/narration/do-not-click columns. The 3-minute pitch must clearly separate LIDAL AI (engine in validation), LIDAL Pulse (first product), RamyPulse/Alerte IA (founding experiences), business model and ProtoMarket funding.

`06_MESSAGE_A_ENVOYER_A_LETICIA.md` must contain this command sequence:

```powershell
git clone https://github.com/rayantr06/ramypulse.git
cd ramypulse
git switch codex/lidal-pulse-leticia-demo
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\INSTALLER_DEMO_LETICIA.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\LANCER_DEMO_LETICIA.ps1
```

It must also tell her to record at 1920 × 1080, zoom 100 %, hide notifications, use the prepared second-tab QR flow, and never show terminals, secrets or personal tabs.

- [ ] **Step 6: Run brand and documentation checks**

Run: `cd frontend; npx playwright test tests/e2e/brandIdentity.spec.ts`

Run: `git diff --check`

Expected: brand test PASS and no whitespace errors.

- [ ] **Step 7: Commit branding and guides**

```powershell
git add frontend/client/src/components/BrandMark.tsx frontend/client/index.html frontend/client/public/brand frontend/tests/e2e/brandIdentity.spec.ts docs/protomarket_ii_2026/demo_leticia
git commit -m "docs(demo): package Leticia recording guides and branding"
```

---

### Task 7: Full Verification, Recording Rehearsal and Publication

**Files:**
- Modify if needed after failures: only files already listed in Tasks 1–6.
- Verify: entire branch diff from `codex/lidal-pulse-v3`.

**Interfaces:**
- Consumes all prior tasks.
- Produces a pushed branch, verified commit hash, and a ready-to-send Leticia message.

- [ ] **Step 1: Verify repository scope and secret hygiene**

Run:

```powershell
git status --short
git diff --check codex/lidal-pulse-v3...HEAD
git diff --name-only codex/lidal-pulse-v3...HEAD
git grep -n -I -E "(api[_-]?key|service_role|BEGIN (RSA|OPENSSH) PRIVATE KEY|Pwd@@)" -- . ":(exclude)package-lock.json"
```

Expected: only planned files appear; the secret scan returns no credential values. Documentation may mention generic variable names but never a real value.

- [ ] **Step 2: Run the complete automated verification**

```powershell
cd frontend
npm ci
npm run check
npm run build
npm run test:quality
npx playwright test tests/e2e/leticiaDemo.spec.ts tests/e2e/brandIdentity.spec.ts
cd ..
python -m pytest tests/test_leticia_demo_scripts.py -q
```

Expected: every command exits 0 with no warning treated as a test failure.

- [ ] **Step 3: Rehearse the exact Windows handoff from a fresh clone**

Clone the repository into a new temporary directory, switch to `codex/lidal-pulse-leticia-demo`, run the installer, run the launcher, then follow `02_SCRIPT_VIDEO_PROTOTYPE.md` from start to finish. Verify the application makes no request to non-local hosts during the recording path.

- [ ] **Step 4: Perform the visual recording check**

At 1920 × 1080 and browser zoom 100 %, verify:

- source flow, KPI cards and page title are visible without accidental cropping;
- Arabic text renders right-to-left correctly;
- the SLM evidence excerpt is readable;
- the QR is fully visible and opens the second tab;
- the pending submission is visible after returning;
- alert and action both refer to availability in Oran;
- no debug controls, terminals or private tabs appear.

- [ ] **Step 5: Commit any verification-only corrections**

If the checks required changes, stage only the exact corrected files and commit:

```powershell
git commit -m "fix(demo): complete Leticia recording rehearsal"
```

If no files changed, do not create an empty commit.

- [ ] **Step 6: Push the verified branch**

```powershell
git push -u origin codex/lidal-pulse-leticia-demo
git rev-parse HEAD
git status --short --branch
```

Expected: upstream is `origin/codex/lidal-pulse-leticia-demo`, the worktree is clean, and the final hash is recorded in `06_MESSAGE_A_ENVOYER_A_LETICIA.md` or supplied in the handoff message.

- [ ] **Step 7: Send the final handoff**

Provide the user with:

- the Git branch and final commit hash;
- clickable paths to `00_LIRE_EN_PREMIER.md`, both video scripts and the Leticia message;
- the complete test results;
- confirmation that the full training corpus and credentials were not published;
- the exact two commands Leticia runs after switching branches.
