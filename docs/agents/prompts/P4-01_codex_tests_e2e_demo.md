# PROMPT P4-01 — Codex : Tests E2E parcours démo
**Phase** : 4 — Tests E2E + Démo (Jours 9-10)
**Agent** : Codex CLI (worktree frontend)
**Tâche** : T34

---

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
Seed data chargé (tenant demo-expo-2026, score 72).
Playwright installé (@playwright/test dans devDependencies).

═══ TÂCHE : Créer frontend/tests/e2e/demo_flow.spec.ts ═══

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const TENANT_ID = 'demo-expo-2026';

test.beforeEach(async ({ page }) => {
  await page.goto(BASE_URL);
  await page.evaluate((tid) => {
    localStorage.setItem('ramypulse.activeTenantId', tid);
  }, TENANT_ID);
  await page.reload();
});

test('Acte 1 — Dashboard score santé visible', async ({ page }) => {
  await expect(page.getByText('72')).toBeVisible({ timeout: 10000 });
  await expect(page.getByText('Distribution')).toBeVisible();
});

test('Acte 2 — Navigation alertes + action', async ({ page }) => {
  await page.goto(BASE_URL + '#/alertes');
  await expect(page.getByText(/Console.*Alertes/i)).toBeVisible();
  const critiqueBtn = page.getByRole('button', { name: /critique/i }).first();
  if (await critiqueBtn.isVisible()) await critiqueBtn.click();
});

test('Acte 3 — Explorateur recherche sémantique', async ({ page }) => {
  await page.goto(BASE_URL + '#/explorateur');
  await page.fill('input[placeholder*="Explorer"]', 'goût yaghourt');
  await page.getByRole('button', { name: 'Explorer' }).click();
  await expect(page.locator('.verbatim-card, [data-verbatim]').first()).toBeVisible({ timeout: 15000 });
});

test('Acte 4 — Export CSV', async ({ page }) => {
  await page.goto(BASE_URL + '#/explorateur');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /export/i }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/verbatims.*\.csv/);
});

test('Acte 5 — Navigation complète sans erreur console', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  const routes = ['/', '#/alertes', '#/explorateur', '#/campagnes', '#/watchlists', '#/recommandations'];
  for (const route of routes) {
    await page.goto(BASE_URL + route);
    await page.waitForTimeout(1000);
  }
  const critical = errors.filter(e => !e.includes('favicon') && !e.includes('ResizeObserver'));
  expect(critical).toHaveLength(0);
});

CONTRAINTES :
- Ajouter data-testid dans les composants si nécessaire
- Timeouts raisonnables (10s max par assertion)
- Commit : "test(e2e): add demo flow E2E test suite"

CRITÈRES DE SUCCÈS :
✅ npx playwright test tests/e2e/demo_flow.spec.ts : 5/5 passent
✅ Aucun crash console lors du parcours
```
