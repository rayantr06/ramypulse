# Feuille de Route Expo — RamyPulse
**Version** : 1.0 — Générée le 2026-04-11  
**Chef de projet** : Subagent RamyPulse  
**Branche de travail** : `feat/watch-first-expo-ready`

---

## 1. Vue d'ensemble

### Résumé exécutif

RamyPulse est une SPA React (Vite + Wouter + TanStack Query + Shadcn/ui + Tailwind) couplée à un backend FastAPI + SQLite de 51 endpoints, tous fonctionnels et 100% mappés au frontend. La base technique est saine : architecture propre, gestion multi-tenant, design system Obsidian cohérent. Les obstacles avant l'expo sont ciblés : 20 boutons morts, 5 bugs critiques, un `.env` vide bloquant les collecteurs watch-first, et un composant monolithe de 1441 lignes. La feuille de route couvre 10 jours : stabilisation, fix bugs, complétion des features, polish Stitch, puis démo.

### Métriques clés du projet

| Métrique | Valeur |
|----------|--------|
| Pages / écrans | 10 (9 fonctionnelles + 1 page 404) |
| Endpoints backend | 51 (tous fonctionnels) |
| Appels API frontend | 47 (100% mappés à des endpoints réels) |
| Boutons morts | 20 |
| Bugs haute sévérité | 5 |
| Bugs moyenne sévérité | 12 |
| Bugs basse sévérité | 17 |
| Branches non-mergées | 1 (`feat/discovery-brain-v1`, 1 commit, 0 conflit) |
| Collecteurs watch-first | 4 (Google Maps, YouTube, Web Keywords, Public URL Seed) |
| Variables `.env` manquantes | Toutes (fichier vide) |
| Composant le plus long | `AdminSourcesOps.tsx` (1441 lignes) |

### Date expo et marge

| Élément | Valeur |
|---------|--------|
| Durée de développement | 10 jours |
| Marge de sécurité | 2 jours (J11-J12) |
| Expo estimée | J12 au plus tôt après démarrage |
| Risque principal | Clés API collecteurs — si indisponibles, remplacer par seed data demo |

---

## 2. Phases de développement

### Phase 0 : Stabilisation & Merge (Jour 1)

**Objectif** : Codebase propre, backend qui démarre, environnement configuré.

#### 0.1 Merger les branches

```bash
# Sur feat/watch-first-expo-ready (HEAD actuel)
git merge feat/discovery-brain-v1 --no-ff -m "merge(discovery): integrate discovery brain v1"
# Aucun conflit attendu (merge test déjà validé)
git push origin feat/watch-first-expo-ready
```

Puis créer une PR `feat/watch-first-expo-ready → main` et merger (55 + 1 commits, fast-forward possible).

#### 0.2 Configurer `.env`

Le fichier `.env` est vide. Variables à renseigner pour activer les collecteurs watch-first :

| Variable | Collecteur | Source |
|----------|-----------|--------|
| `GOOGLE_MAPS_API_KEY` | Google Maps Reviews collector | Google Cloud Console |
| `YOUTUBE_API_KEY` | YouTube Search collector | Google Cloud Console |
| `PERPLEXITY_API_KEY` | Perplexity Discovery Brain | perplexity.ai |
| `SERPAPI_KEY` ou équivalent | Web Keyword collector | SerpAPI / SearXNG |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Moteur recommandations IA | OpenAI / Anthropic |

> **Si les clés ne sont pas disponibles avant J2** : le backend reste fonctionnel en mode dégradé. Les collecteurs retourneront des erreurs gérées. Préparer un jeu de données seed réaliste pour contourner (voir Phase 4).

#### 0.3 Vérifier que le backend démarre

```bash
cd ramypulse
pip install -r requirements.txt  # ou uv sync
uvicorn api.main:app --reload --port 8000
curl http://localhost:8000/api/health
curl http://localhost:8000/api/status
```

Résultat attendu : `{"status": "ok", "db_status": "ok"}`.

#### 0.4 Lancer les tests existants

```bash
# Backend Python
pytest tests/ -v --tb=short
# Si découverte brain inclus :
pytest tests/test_perplexity_discovery.py -v

# Frontend
cd frontend
npm install
npm run test   # Vitest
npx playwright test  # E2E Playwright
```

Documenter les tests qui échouent → les prioriser dans Phase 1.

---

### Phase 1 : Fix Bugs Critiques (Jours 2-3)

**Objectif** : Éliminer tous les crashs visibles et comportements trompeurs avant toute démonstration.

#### 1.1 Les 5 bugs haute sévérité

| # | Bug | Fichier | Fix |
|---|-----|---------|-----|
| B1 | Bouton "VOIR DETAILS" sans onClick sur cartes action IA | `Dashboard.tsx` L~190 | Naviguer vers `/recommandations` ou ouvrir un modal détail. Option rapide : `onClick={() => navigate('/recommandations')}` |
| B2 | Upload screenshot sans headers d'auth | `AdminSourcesOps.tsx` | Remplacer `fetch()` brut par `apiRequest()` de `queryClient.ts` qui injecte `X-API-Key` et `X-Ramy-Client-Id` |
| B3 | `formatSentimentLabel()` ne gère pas `"tres_negatif"` | `Explorateur.tsx` | Ajouter le case : `case 'tres_negatif': return 'Très Négatif'` (avec couleur rouge foncé) |
| B4 | Mutation création campagne sans `onError` | `Campagnes.tsx` | Ajouter `onError: (error) => toast({ title: "Erreur", description: error.message, variant: "destructive" })` |
| B5 | "Tout Archiver" — race condition forEach+mutate | `Recommandations.tsx` | Remplacer par une mutation batch : `Promise.all(ids.map(id => mutateAsync(id)))` puis invalider le cache une seule fois avec `queryClient.invalidateQueries` |

#### 1.2 Décision sur les 20 boutons morts

| # | Bouton | Page | Décision | Action |
|---|--------|------|----------|--------|
| 1 | "VOIR DETAILS" (action IA) | Dashboard | **Connecter** | `navigate('/recommandations')` |
| 2 | Carte alerte (cursor-pointer) | Dashboard | **Connecter** | `navigate('/alertes')` |
| 3 | Carte action (cursor-pointer) | Dashboard | **Connecter** | `navigate('/recommandations')` |
| 4 | "Filtrer" (icône tune) | Explorateur | **Connecter** | Ouvrir un panneau filtre avancé (sidebar ou popover) avec filtres date/sentiment |
| 5 | "Exporter" (icône download) | Explorateur | **Connecter** | Implémenter export CSV des verbatims (voir Phase 2) |
| 6 | "EXPORTER DATA" | Campagnes | **Connecter** | Implémenter export CSV des campagnes (voir Phase 2) |
| 7 | "Voir les détails analytiques" | Watchlists | **Connecter** | `navigate('/explorateur')` avec le slug de la watchlist en query param |
| 8 | "Pipelines" (nav link) | AdminSources | **Tooltip** | `href="#"` + `title="Bientôt disponible"` + curseur `not-allowed` |
| 9 | "Logs" (nav link) | AdminSources | **Tooltip** | Idem |
| 10 | "notifications" (icône header) | AdminSources | **Supprimer** | Retirer l'élément — redondant avec AppShell |
| 11 | "settings" (icône header) | AdminSources | **Supprimer** | Retirer l'élément |
| 12 | "New Pipeline" | AdminSources | **Tooltip** | `disabled` + `title="Bientôt disponible"` |
| 13 | "Support" (sidebar) | AdminSources | **Supprimer** | Retirer — hors scope expo |
| 14 | "Documentation" (sidebar) | AdminSources | **Supprimer** | Retirer — hors scope expo |
| 15 | Nav items (Connectors, Health, Validation, Archive) | AdminSources | **Tooltip** | Badge "Bientôt" sur chaque item |
| 16 | "Voir tout l'historique" | AdminSources | **Supprimer** | Retirer — la liste est déjà visible |
| 17 | "language" (icône header) | AppShell | **Supprimer** | Retirer — pas de i18n à l'expo |
| 18 | "grid_view" (icône header) | AppShell | **Supprimer** | Retirer — pas de vue grille implémentée |
| 19 | "notifications" (icône header) | AppShell | **Tooltip** | `onClick` → toast "Aucune notification" |
| 20 | "sensors" (icône header) | AppShell | **Connecter** | `navigate('/admin-sources')` (accès direct à l'admin) |

#### 1.3 Fix des erreurs de mutation silencieuses

Toutes les mutations sans `onError` dans le projet :

```bash
# Trouver toutes les mutations sans onError
grep -rn "useMutation\|mutate(" frontend/client/src --include="*.tsx" | grep -v onError
```

Pattern à appliquer systématiquement :

```typescript
onError: (error: Error) => {
  toast({
    title: "Erreur",
    description: error.message || "Une erreur est survenue",
    variant: "destructive",
  });
},
onSuccess: () => {
  toast({ title: "Succès", description: "Opération effectuée" });
  queryClient.invalidateQueries({ queryKey: [...] });
},
```

Concerne : `Campagnes.tsx` (création), `AdminSourcesOps.tsx` (sync, health, scheduler), `Recommandations.tsx` (archivage).

---

### Phase 2 : Compléter les fonctionnalités (Jours 4-6)

**Objectif** : Toutes les features visibles dans la démo sont fonctionnelles.

#### 2.1 Implémenter les exports CSV/PDF

**Export CSV verbatims** (`Explorateur.tsx`) :
```typescript
// Utiliser l'endpoint existant : GET /api/explorer/verbatims (sans pagination)
const exportCSV = async () => {
  const data = await apiRequest('/api/explorer/verbatims?page_size=1000');
  const csv = convertToCSV(data.items); // colonnes : source, sentiment, contenu, wilaya, date
  downloadBlob(csv, 'verbatims.csv', 'text/csv');
};
```

**Export CSV campagnes** (`Campagnes.tsx`) :
```typescript
// Utiliser l'endpoint existant : GET /api/campaigns
const exportCSV = async () => {
  const data = await apiRequest('/api/campaigns');
  const csv = convertToCSV(data); // colonnes : nom, type, plateforme, budget, statut, ROI
  downloadBlob(csv, 'campagnes.csv', 'text/csv');
};
```

**Helper partagé** à créer dans `lib/utils.ts` :
```typescript
export function convertToCSV(items: Record<string, unknown>[]): string { ... }
export function downloadBlob(content: string, filename: string, mimeType: string): void { ... }
```

#### 2.2 Connecter les boutons CTA restants

**"VOIR DETAILS" Dashboard → Recommandations** :
- Passer l'`actionId` en query param : `navigate('/recommandations?highlight=' + action.id)`
- Dans `Recommandations.tsx` : lire le param et scroller vers la carte

**"Voir les détails analytiques" Watchlists → Explorateur** :
- `navigate('/explorateur?watchlist=' + watchlist.id)`
- Dans `Explorateur.tsx` : pré-remplir le filtre source avec les canaux de la watchlist

#### 2.3 Corriger les 12 bugs moyens

| # | Bug | Fichier | Fix |
|---|-----|---------|-----|
| M1 | Titre "VENTES PAR PRODUIT" (données = sentiment) | `Dashboard.tsx` | Renommer en "PERFORMANCE PRODUIT — Score Sentiment" |
| M2 | Icônes manquantes TikTok / Google Maps | `Campagnes.tsx` | Importer `SiTiktok` depuis `react-icons/si` et `FaMapMarkerAlt` de `react-icons/fa` |
| M3 | `buildOwners()` hack avec initiales filtres | `Watchlists.tsx` | Remplacer par un avatar générique coloré + tooltip "owners non disponibles" |
| M4 | Delta NSS couleur identique positif/négatif | `Watchlists.tsx` | `delta > 0 ? 'text-green-400' : 'text-red-400'` |
| M5 | Label "Volume (m³)" pour système NLP | `Recommandations.tsx` | Remplacer par "Volume mentions" |
| M6 | Carte "Dernière run" : value/label inversés | `Recommandations.tsx` | Inverser `value` et `label` dans la map de la section stats |
| M7 | Dates ISO brutes dans tableau historique | `Recommandations.tsx` | `format(new Date(dateISO), 'dd/MM/yyyy HH:mm', { locale: fr })` via `date-fns` |
| M8 | Pas de loading/disabled sur boutons d'action alertes | `Alertes.tsx` | `disabled={isPending}` + spinner sur le bouton actif uniquement |
| M9 | Boutons affichés même si non pertinents (alerte résolue) | `Alertes.tsx` | Masquer les boutons selon `alert.status` : resolved → pas de "Résoudre", dismissed → pas d'"Écarter" |
| M10 | Limite 50 alertes hardcodée | `Alertes.tsx` | Ajouter un bouton "Charger plus" → `limit += 50` via state local |
| M11 | Filtre multi-source n'envoie pas de `channel` param | `Explorateur.tsx` | Mapper les chips sélectionnées vers le paramètre `channel` : `selectedChannels.join(',')` |
| M12 | Pas de dialogue confirmation pour actions destructives | `AdminSourcesOps.tsx` | Envelopper les appels DELETE dans un `AlertDialog` Shadcn/ui : "Confirmer la suppression ?" |

#### 2.4 Découper AdminSourcesOps.tsx (1441 lignes)

Découper en 4 sous-composants dans `components/admin/` :

```
components/admin/
├── AdminSourcesOps.tsx          # Orchestrateur (< 100 lignes, importe les 4 sous-vues)
├── AdminSourcesView.tsx         # Sous-vue Sources (sync, health, snapshots)
├── AdminCredentialsView.tsx     # Sous-vue Credentials
├── AdminCampaignOpsView.tsx     # Sous-vue Campaign Ops (posts, screenshots, revenue)
└── AdminSchedulerView.tsx       # Sous-vue Scheduler (tick)
```

Chaque sous-vue doit être autonome avec ses propres hooks et queries. Le composant parent gère uniquement le routing entre vues (tabs existants).

---

### Phase 3 : Polish & Intégration (Jours 7-8)

**Objectif** : Interface expo-ready, cohérente visuellement, bugs bas corrigés.

#### 3.1 Google Stitch — Redesign UI/UX

**Workflow exact (React web, PAS React Native) :**

```
1. Prendre des screenshots de chaque page principale (Dashboard, Explorateur, Alertes, Campagnes)
2. Ouvrir stitch.withgoogle.com en Experimental Mode (Gemini 2.5 Pro)
3. Uploader les screenshots + prompt :
   "App web React de marketing intelligence 'RamyPulse'. 
    Design system existant : dark mode, fond #0A0A14, accent #ffb693, 
    typographie Manrope (titres) + Inter (corps), primaire Shadcn/ui + Tailwind.
    Améliore la hiérarchie visuelle, la lisibilité des données, et les états vides.
    Garde la structure de navigation (sidebar gauche). 
    Output : HTML + Tailwind CSS exportable vers React web (Vite + Shadcn)."
4. Itérer jusqu'à satisfaction
5. Exporter DESIGN.md depuis Stitch
6. Commiter DESIGN.md dans la racine du repo : git add DESIGN.md && git commit -m "feat: add Stitch design system"
```

**Conversion Stitch HTML → React (web) :**

```
Workflow : Stitch → DESIGN.md → Claude Code → React (web)

Pour chaque page redesignée :
1. Copier le HTML + Tailwind exporté depuis Stitch
2. Prompt Claude Code :
   "Voici le HTML/Tailwind de l'écran [NOM] généré par Google Stitch 
    pour RamyPulse (React web SPA, Vite + Shadcn/ui + Tailwind).
    IMPORTANT : c'est du React WEB, pas React Native.
    Convertis en composants React TSX.
    Règles : 
    - Garder les classes Tailwind existantes (Tailwind est déjà installé)
    - Remplacer les balises HTML standard par Shadcn/ui où disponibles 
      (Button, Card, Badge, Input, etc.)
    - Conserver les hooks et appels API existants
    - Ne pas toucher à la logique métier (queryClient, mutations)
    DESIGN.md de référence : [coller contenu DESIGN.md]"
3. Valider visuellement dans le navigateur
4. Ajustements fins directement dans le fichier TSX
```

**Règle d'or** : DESIGN.md est la source de vérité. Jamais de valeurs de couleur ou d'espacement hardcodées en dehors des tokens du DESIGN.md.

#### 3.2 Corriger les 17 bugs bas

| # | Bug | Fichier | Fix |
|---|-----|---------|-----|
| L1 | Copyright "2024" hardcodé | `Dashboard.tsx` | `new Date().getFullYear()` |
| L2 | Typo "Base sur" | `Dashboard.tsx` | Chercher/remplacer → "Basé sur" |
| L3 | "Ecarter" / "Reconnaitre" sans accents | `Alertes.tsx` | "Écarter" / "Reconnaître" |
| L4 | MOYENNE et BASSE même gradient visuel | `Alertes.tsx` | Distinguer : MOYENNE = `amber-500/20`, BASSE = `slate-500/20` |
| L5 | Cercle avatar vide (extraits sociaux) | `Alertes.tsx` | Remplacer par initiales générées depuis `source` ou icône générique |
| L6 | Avatars campagne = 4 images CDN round-robin | `Campagnes.tsx` | Remplacer par des avatars avec initiales du nom de campagne (pas de CDN externe) |
| L7 | Avatar top performeur hardcodé | `Campagnes.tsx` | Idem — initiales ou icône générique |
| L8 | Formulaire création campagne ouvert par défaut | `Campagnes.tsx` | `const [isOpen, setIsOpen] = useState(false)` au lieu de `true` |
| L9 | Validation formulaire minimale | `Campagnes.tsx` | Ajouter validation Zod : budget > 0, dates cohérentes (fin > début) |
| L10 | "n/a" affiché littéralement | `Explorateur.tsx` | `value === 'n/a' ? '—' : value` |
| L11 | NotFound en anglais | `not-found.tsx` | "Page introuvable" + "Cette page n'existe pas." |
| L12 | `<a>` imbriqué (Link > a) | `Recommandations.tsx` | Remplacer `<Link><a>` par `<Link>` directement (Wouter Link accepte className) |
| L13 | Langues ["fr", "ar"] hardcodées | `WatchOnboarding.tsx` | Exposer comme champ optionnel du formulaire avec valeur par défaut |
| L14 | "Ammar, Brand Manager" hardcodé en sidebar | `Sidebar.tsx` | Remplacer par le tenant actif : `{tenantId || 'Démo'}` |
| L15 | Avatars CDN Google externe (toutes pages) | Multiple | Centraliser dans `lib/avatars.ts` avec fallback local (SVG initiales) |
| L16 | AdminSourcesOps sans `<label>` | `AdminSourcesOps.tsx` (futurs sous-composants) | Ajouter `htmlFor` + `<label>` sur tous les inputs du formulaire |
| L17 | TikTok filtré des options de création source | `AdminSourcesOps.tsx` | Ré-inclure TikTok dans `PLATFORM_OPTIONS` ou documenter l'exclusion |

---

### Phase 4 : Démo & Préparation Expo (Jours 9-10)

**Objectif** : Scénario de démo irréprochable, données réalistes, backup prêt.

#### 4.1 Seed data réaliste pour la démo

Créer un script `scripts/seed_demo.py` qui peuple la base avec :

```python
# Tenant demo : "DemoMarque" (brand de grande consommation algérienne)
DEMO_TENANT = {
    "client_id": "demo-expo-2026",
    "brand": "YaghurtPlus",
    "product": "Yaghourt Abricot 150g",
    "sector": "Agroalimentaire",
    "region": "Algérie"
}

# Verbatims : 200 entrées réalistes (Facebook, Google Maps, YouTube)
# Répartition sentiments : 40% positif, 30% neutre, 20% négatif, 10% très négatif
# Wilayas : Alger, Oran, Constantine, Annaba, Tlemcen
# Aspects : goût, texture, prix, disponibilité, packaging

# Score santé : 72/100 (tendance +5 vs mois précédent)
# Alertes : 2 critiques, 3 moyennes, 5 basses
# Actions IA : 3 recommandations générées
# Campagnes : 3 campagnes (1 active, 1 archivée, 1 en cours)
# Watchlists : 2 actives (marque + concurrent)
```

```bash
python scripts/seed_demo.py --tenant demo-expo-2026 --reset
```

#### 4.2 Scénario de démonstration (voir section 6)

#### 4.3 Tests E2E du parcours de démo

Créer `tests/e2e/demo_flow.spec.ts` dans Playwright :

```typescript
test('Parcours démo expo complet', async ({ page }) => {
  // 1. Onboarding
  await page.goto('http://localhost:5173');
  await expect(page.getByText('YaghurtPlus')).toBeVisible();
  
  // 2. Dashboard → score visible
  await expect(page.getByText('72')).toBeVisible(); // score santé
  
  // 3. Navigation alerte → action
  await page.click('[data-testid="alert-critique"]');
  await page.click('text=Reconnaître');
  
  // 4. Explorateur → recherche
  await page.goto('http://localhost:5173/#/explorateur');
  await page.fill('[placeholder*="Explorer"]', 'goût yaghourt');
  await page.click('text=Explorer');
  await expect(page.locator('.verbatim-card')).toHaveCount.greaterThan(0);
  
  // 5. Recommandations → génération
  await page.goto('http://localhost:5173/#/recommandations');
  await page.click('text=Générer');
  await expect(page.getByText('recommandation')).toBeVisible({ timeout: 30000 });
});
```

#### 4.4 Backup et déploiement

```bash
# Snapshot base de données
cp ramypulse.db backups/ramypulse_demo_$(date +%Y%m%d).db

# Build frontend
cd frontend && npm run build
# Output dans dist/public/

# Démarrage production
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
serve -s dist/public -l 3000
# OU : laisser FastAPI servir le frontend via mount StaticFiles

# Vérification finale
curl http://localhost:8000/api/health
curl http://localhost:8000/api/status
```

---

## 3. Matrice de priorisation

| # | Tâche | Phase | Priorité | Effort estimé | Impact démo | Risque si non fait |
|---|-------|-------|----------|---------------|-------------|-------------------|
| 1 | Merger `feat/discovery-brain-v1` | P0 | P0 | 15 min | Faible | Discovery brain inaccessible |
| 2 | Configurer `.env` (clés API collecteurs) | P0 | P0 | 1h | Critique | Collecteurs non fonctionnels |
| 3 | Vérifier démarrage backend + health check | P0 | P0 | 30 min | Critique | App inutilisable |
| 4 | Lancer pytest + tests frontend | P0 | P0 | 1h | Moyen | Tests ignorés → régressions cachées |
| 5 | B1 — Bouton "VOIR DETAILS" mort | P1 | P0 | 30 min | Critique | Démo bloquée sur CTA principal |
| 6 | B4 — Mutation campagne silencieuse | P1 | P0 | 20 min | Haute | Création campagne semble "planter" |
| 7 | B2 — Screenshot upload sans auth | P1 | P0 | 30 min | Moyenne | Upload échoue en prod |
| 8 | B3 — Sentiment "tres_negatif" manquant | P1 | P1 | 20 min | Haute | Données sentiment tronquées |
| 9 | B5 — Race condition "Tout Archiver" | P1 | P1 | 45 min | Moyenne | Cache corrompu, reload requis |
| 10 | Tuer/transformer les 20 boutons morts | P1 | P1 | 3h | Critique | Interface paraît incomplète |
| 11 | Mutations silencieuses (onError global) | P1 | P1 | 1h | Haute | Erreurs sans feedback utilisateur |
| 12 | Export CSV verbatims | P2 | P1 | 2h | Haute | Feature attendue non délivrée |
| 13 | Export CSV campagnes | P2 | P1 | 1h | Moyenne | Idem |
| 14 | CTA Dashboard → Recommandations | P2 | P1 | 1h | Haute | Navigation demo cassée |
| 15 | CTA Watchlists → Explorateur | P2 | P1 | 45 min | Haute | Navigation demo cassée |
| 16 | M11 — Filtre multi-source ineffectif | P2 | P1 | 1h | Haute | Filtre ne fait rien |
| 17 | M1 — Titre "VENTES PAR PRODUIT" trompeur | P2 | P2 | 10 min | Moyenne | Label incohérent avec les données |
| 18 | M6 — Value/label inversés (Recommandations) | P2 | P2 | 15 min | Moyenne | Confusion jury |
| 19 | M7 — Dates ISO brutes | P2 | P2 | 30 min | Moyenne | Interface non professionnelle |
| 20 | M8 — Loading/disabled boutons alertes | P2 | P2 | 45 min | Moyenne | Double-clic possible en demo |
| 21 | M9 — Boutons non contextuels (alertes) | P2 | P2 | 30 min | Faible | Confusion UX mineure |
| 22 | M10 — Pagination alertes (> 50) | P2 | P2 | 1h | Faible | Seulement avec seed data dense |
| 23 | M12 — Confirmation actions destructives | P2 | P2 | 1h | Faible | Risque accident en live |
| 24 | M2 — Icônes TikTok / Google Maps | P2 | P2 | 30 min | Faible | Visuel dégradé |
| 25 | M3 — Avatars owners hack | P2 | P2 | 1h | Faible | Visible en demo |
| 26 | M4 — Delta NSS couleur | P2 | P2 | 15 min | Faible | Lecture données dégradée |
| 27 | M5 — "Volume (m³)" label | P2 | P2 | 10 min | Faible | Terme confus |
| 28 | Découpage AdminSourcesOps (1441 lignes) | P2 | P2 | 4h | Faible | Maintenabilité seulement |
| 29 | Google Stitch redesign UI/UX | P3 | P2 | 4-6h | Haute | Interface acceptable mais non impressionnante |
| 30 | DESIGN.md commité comme source de vérité | P3 | P2 | 30 min | Faible | Incohérence future design/code |
| 31 | Bugs bas L1-L17 | P3 | P3 | 4h total | Faible | Détails, non bloquants |
| 32 | Seed data démo réaliste | P4 | P0 | 3h | Critique | Démo sur données vides |
| 33 | Script de démo documenté | P4 | P0 | 1h | Critique | Démo improvisée = désastre |
| 34 | Tests E2E parcours démo | P4 | P1 | 2h | Haute | Régression non détectée avant expo |
| 35 | Backup base de données | P4 | P1 | 15 min | Haute | Perte données si crash |
| 36 | Snapshot `.env` sécurisé | P4 | P1 | 15 min | Haute | Redémarrage impossible |

---

## 4. Risques et mitigations

### Risque 1 — Clés API collecteurs indisponibles
**Probabilité** : Haute | **Impact** : Critique  
**Symptôme** : Le wizard d'onboarding lance un run → timeout ou erreur 500  
**Mitigation** :  
- Préparer un tenant "demo-expo-2026" seedé manuellement avec `scripts/seed_demo.py` (Jour 1, en parallèle des démarches API)  
- Ajouter un mode `DEMO_MODE=true` dans `.env` : si activé, le watch-run retourne des données mock au lieu d'appeler les APIs externes  
- Documenter l'état des clés dans `docs/env_status.md`  
**Plan B** : L'onboarding est montré comme "déjà fait" — on démarre directement sur le dashboard du tenant démo

---

### Risque 2 — Régression lors du merge discovery brain
**Probabilité** : Faible | **Impact** : Moyen  
**Symptôme** : Tests pytest échouent après merge  
**Mitigation** :  
- Le merge test a déjà confirmé 0 conflit (audit_git.md §3)  
- `tests/test_config.py` modifié dans discovery brain → relancer en priorité après merge  
- Conserver `feat/watch-first-expo-ready` comme branche de secours en cas de revert  
**Plan B** : Revenir sur `feat/watch-first-expo-ready` sans le merge discovery brain — la feature est additive et non nécessaire pour la démo

---

### Risque 3 — Composant AdminSourcesOps bloque le découpage
**Probabilité** : Moyenne | **Impact** : Moyen  
**Symptôme** : Découpage en 4 sous-composants introduit des régressions (state partagé, queries)  
**Mitigation** :  
- Commencer par extraire `AdminSchedulerView` (le plus simple, 1 endpoint)  
- Valider chaque extraction avant de passer à la suivante  
- Garder une copie de sauvegarde `AdminSourcesOps_backup.tsx`  
**Plan B** : Si le découpage dépasse J6, le reporter — 1441 lignes fonctionnent, la démo ne souffre pas d'un composant monolithe

---

### Risque 4 — Google Stitch génère un design incompatible avec React web
**Probabilité** : Moyenne | **Impact** : Moyen  
**Symptôme** : Le HTML Stitch utilise des constructs non convertibles directement en Shadcn/ui  
**Mitigation** :  
- Utiliser Stitch uniquement pour les tokens (couleurs, typo, espacement) → DESIGN.md  
- Appliquer les tokens manuellement via les CSS variables Tailwind existantes dans `index.css`  
- Traiter Stitch comme inspiration visuelle, pas comme source de code  
**Plan B** : Si Stitch est trop lent ou peu fiable, utiliser v0.dev (génère React + Shadcn/ui nativement) pour les composants individuels à refaire

---

### Risque 5 — Données démo insuffisantes pour impressionner le jury
**Probabilité** : Haute | **Impact** : Haute  
**Symptôme** : Dashboard avec score 0, alertes vides, recommandations vides  
**Mitigation** :  
- Créer `scripts/seed_demo.py` en Jour 1 (Priorité P0)  
- Générer 200+ verbatims réalistes (produit algérien identifiable, wilayas réelles)  
- Pré-générer 3 recommandations IA avec des modèles de qualité  
- Vérifier le seed avec un parcours complet avant J9  
**Plan B** : Utiliser `faker` + templates prédéfinis pour générer rapidement des données cohérentes si la rédaction manuelle prend trop de temps

---

## 5. Checklist pré-expo

| # | Point | Responsable | Statut |
|---|-------|-------------|--------|
| 1 | `.env` configuré avec toutes les clés nécessaires | Dev | ☐ |
| 2 | Backend démarre sans erreur (`/api/health` → OK) | Dev | ☐ |
| 3 | Frontend démarre sans erreur console (`npm run dev`) | Dev | ☐ |
| 4 | Tenant démo "demo-expo-2026" seedé avec données réalistes | Dev | ☐ |
| 5 | Score santé marque visible (non nul) sur le Dashboard | Dev | ☐ |
| 6 | Au moins 2 alertes critiques visibles et actionnables | Dev | ☐ |
| 7 | Au moins 3 recommandations IA générées et visibles | Dev | ☐ |
| 8 | Moteur de recherche Explorateur retourne des résultats | Dev | ☐ |
| 9 | Filtres source Explorateur fonctionnent (Facebook, YouTube, etc.) | Dev | ☐ |
| 10 | Bouton "VOIR DETAILS" navigue vers Recommandations | Dev | ☐ |
| 11 | Export CSV fonctionne (Explorateur + Campagnes) | Dev | ☐ |
| 12 | Création d'une campagne affiche un toast succès | Dev | ☐ |
| 13 | Actions sur alertes (Reconnaître, Résoudre) mettent à jour le statut | Dev | ☐ |
| 14 | Aucun bouton mort visible dans le parcours de démo | Dev | ☐ |
| 15 | Tests E2E du parcours de démo passent sans échec | Dev | ☐ |
| 16 | Backup de la base SQLite effectué (`backups/`) | Dev | ☐ |
| 17 | Script de redémarrage documenté (`scripts/restart.sh`) | Dev | ☐ |
| 18 | Connexion internet confirmée (pour les collecteurs si en live) | Dev | ☐ |
| 19 | DESIGN.md commité — design tokens à jour | Dev | ☐ |
| 20 | Parcours démo répété 2 fois sans accroc (J9 et J10) | Chef de projet | ☐ |

---

## 6. Script de démo

**Durée** : 8 minutes | **Présentateur** : 1 personne | **Supports** : Navigateur + script papier

---

### Acte 1 : L'intelligence en action (0:00 → 1:30)

**Contexte annoncé** :
> "RamyPulse est un système de veille marketing intelligent pour les marques algériennes. En 8 minutes, je vais vous montrer comment une équipe marketing peut passer de l'alerte terrain à la décision stratégique."

**Actions** :
1. Ouvrir le navigateur sur `http://localhost:5173` → Dashboard visible
2. Pointer le **Score Santé Marque** : "72/100, en hausse de 5 points ce mois — le système analyse en temps réel les avis consommateurs sur Facebook, Google Maps et YouTube."
3. Zoomer sur la section **Distribution régionale** : "On voit que Tlemcen sous-performe — c'est un signal d'action, pas juste une statistique."
4. Cliquer sur une **Alerte Critique** dans la liste → l'alerte se sélectionne à droite

---

### Acte 2 : Gestion des alertes en temps réel (1:30 → 3:00)

**Navigation** : `#/alertes` via la sidebar

**Actions** :
1. Montrer la **Console d'Alertes** avec le compteur "3 alertes actives" + point vert pulsant
2. Filtrer par sévérité "Critique" → 2 alertes apparaissent
3. Cliquer sur l'alerte : "Hausse des mentions négatives sur le goût — Alger"
4. Lire l'extrait social affiché dans le panneau droit : "preuves terrain en temps réel"
5. Cliquer **"Reconnaître"** → badge statut change → "l'équipe est notifiée, l'alerte est prise en charge"

---

### Acte 3 : Exploration sémantique (3:00 → 4:30)

**Navigation** : `#/explorateur` via la sidebar

**Actions** :
1. Taper "goût yaghourt" dans la barre de recherche → cliquer "Explorer"
2. Montrer le **RAG Insight** en haut : "synthèse IA des verbatims — pas un résumé manuel"
3. Pointer les **scores de pertinence** sur les cartes résultats
4. Activer le filtre "Google Maps" → les résultats se filtrent : "je peux isoler par canal"
5. Cliquer "Exporter" → CSV téléchargé : "les données exportables pour l'équipe analytique"

---

### Acte 4 : L'IA recommande (4:30 → 6:00)

**Navigation** : `#/recommandations` via la sidebar

**Actions** :
1. Montrer les **3 recommandations actives** avec titre, priorité, rationale et timing
2. Pointer le **KPI attendu** sur chaque carte : "ce n'est pas de l'IA magique — c'est mesurable"
3. Cliquer "Générer" avec le déclencheur "Analyse mensuelle" sélectionné
4. Pendant le chargement (5-15s) : "RamyPulse appelle le moteur d'inférence avec le contexte complet — NSS, volume, alertes actives"
5. Nouvelle recommandation apparaît → pointer la **confiance %** et le **timing suggéré**

---

### Acte 5 : Suivi des campagnes (6:00 → 7:00)

**Navigation** : `#/campagnes` via la sidebar

**Actions** :
1. Pointer la **campagne active** dans le tableau
2. Cliquer dessus → l'**Analyse d'Impact NSS** s'affiche (3 barres : Pré / Pendant / Post)
3. "Avant la campagne influenceur : NSS 68. Pendant : 74. Après : 71. L'impact est mesuré, pas supposé."
4. Pointer le **Budget Total Engagé** et le ROI en bas de page

---

### Acte 6 : Conclusion (7:00 → 8:00)

**Retour au Dashboard**

**Message final** :
> "RamyPulse transforme le bruit des réseaux sociaux en décisions mesurables. De l'alerte terrain à la recommandation IA en passant par l'analyse sémantique — tout dans une interface unifiée, en arabe, en français, pour les marques qui opèrent en Algérie."

**Points techniques à mentionner si demandé** :
- Backend FastAPI + SQLite, 51 endpoints
- Collecteurs : Facebook, Google Maps, YouTube, Web Keywords
- Moteur NLP : ABSA (Aspect-Based Sentiment Analysis), NSS (Net Sentiment Score)
- RAG (Retrieval-Augmented Generation) pour l'Explorateur
- Multi-tenant : isolation des données par client

---

*Feuille de route générée automatiquement le 2026-04-11 depuis les audits backend, frontend, git et la stratégie Stitch.*
