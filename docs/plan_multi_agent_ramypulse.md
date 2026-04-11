# Plan Multi-Agent RamyPulse — Document Maître

**Version** : 1.0 — Généré le 2026-04-11  
**Auteur** : Architecte Systèmes Multi-Agent  
**Statut** : DÉFINITIF — document d'orchestration opérationnel  
**Périmètre** : 10 jours, 2 agents AI (Claude Code + Codex CLI), 36 tâches  

---

## Table des matières

1. [Philosophie et principes](#1-philosophie-et-principes)
2. [Architecture de l'environnement de travail](#2-architecture-de-lenvironnement-de-travail)
3. [Répartition du travail — Qui fait quoi](#3-répartition-du-travail--qui-fait-quoi)
4. [Prompts exécutables](#4-prompts-exécutables)
5. [Gestion des tokens et crédits](#5-gestion-des-tokens-et-crédits)
6. [Vérification croisée — L'agent review l'autre](#6-vérification-croisée--lagent-review-lautre)
7. [Anti-patterns et pièges à éviter](#7-anti-patterns-et-pièges-à-éviter)
8. [Checklist de lancement](#8-checklist-de-lancement)

---

## 1. Philosophie et principes

### 1.1 Pourquoi 2 agents et pas 1

Un seul agent sur RamyPulse génèrerait un goulot d'étranglement critique : il lui faudrait charger simultanément les 51 endpoints FastAPI (`api/routers/`) ET les 10 pages React (`frontend/client/src/pages/`) dans son contexte, soit ~1 400 lignes de backend + ~5 000 lignes de frontend. Le contexte serait saturé avant même la première modification.

Avec 2 agents en isolation :

| Agent | Zone | Fichiers | Lignes ~tot. |
|-------|------|----------|--------------|
| **Claude Code** | Backend FastAPI + bugs transverses + seed data | `api/`, `scripts/`, `tests/` | ~8 000 |
| **Codex** | Frontend React + boutons morts + polish UI | `frontend/client/src/`, `frontend/shared/` | ~12 000 |

La frontière est orthogonale : aucun fichier n'est touché par les deux agents simultanément. `frontend/shared/schema.ts` est **gelé** pendant les phases parallèles et ne peut être modifié que lors des points de synchronisation humain.

Cette division génère aussi un gain de temps réel : J2-J3 (fixes critiques) et J4-J6 (features) sont entièrement parallélisables, soit **5 jours gagnés** sur un planning séquentiel de 10 jours.

---

### 1.2 Le principe Contract-First, Test-Gated, Human-Reviewed

```
CONTRAT D'ABORD       →    TESTS ÉCRITS      →    IMPLÉMENTATION    →    REVUE HUMAINE
shared/schema.ts             par l'humain            par l'agent            avant merge
(gelé en phase parallèle)    (critères clairs)       (RED → GREEN)          (quality gate)
```

**Contract-First** : `frontend/shared/schema.ts` est la source de vérité unique. Avant qu'un agent touche une interface, le type est validé par l'humain. Source : [Evil Martians – API contracts frontend survival guide](https://evilmartians.com/chronicles/api-contracts-and-everything-i-wish-i-knew-a-frontend-survival-guide).

**Test-Gated** : Chaque tâche doit spécifier les tests qui doivent passer avant le commit. L'agent ne peut pas déclarer une tâche terminée si `npm run typecheck` ou `pytest` échouent. Source : [Agentic Coding Handbook – TDD](https://tweag.github.io/agentic-coding-handbook/WORKFLOW_TDD/).

**Human-Reviewed** : L'humain intervient à 3 points de synchronisation (fin J1, fin J3, fin J6). Il ne review pas ligne par ligne — il vérifie que les tests passent, que les contrats tiennent, et que la démo est possible.

---

### 1.3 Les 5 règles d'or (avec source)

| # | Règle d'or | Source |
|---|------------|--------|
| **R1** | **Décomposition orthogonale** : assigner aux agents des zones non-chevauchantes du code. Agent A → `api/`, Agent B → `frontend/client/src/`. Zéro fichier partagé en phase parallèle. | [research_multi_agent_workflows.md §1 — Stratégies pour éviter les merge conflicts] |
| **R2** | **Un worktree par agent** : chaque agent travaille dans son propre répertoire isolé sur sa propre branche Git. `~40% de réduction du temps de développement` mesuré en production (projet Spec Kitty v0.11.0). | [research_multi_agent_workflows.md §1 — Pattern: Un worktree par agent] |
| **R3** | **Ne pas laisser l'agent écrire ses propres tests** : un agent qui génère tests ET implémentation validera ses propres bugs. Les tests sont écrits par l'humain (ou fournis dans le prompt) avant de lancer l'agent. | [research_multi_agent_workflows.md §3 — Règle critique TDD] |
| **R4** | **CLAUDE.md et AGENTS.md courts et précis** : un fichier de configuration gonflé (>100 lignes) cause que l'agent ignore les règles importantes. Élaguer sans pitié. Si l'agent fait déjà quelque chose correctement sans l'instruction, supprimer la règle. | [research_ai_agent_best_practices.md §1.1 — Règles de maintenance CLAUDE.md] |
| **R5** | **Stocker les artefacts dans le filesystem, pas dans la conversation** : les agents passent des chemins de fichiers, pas du contenu. Évite la "game of telephone" où chaque agent réinterprète ce que l'autre a fait. | [research_ai_agent_best_practices.md §1.8 — Long-horizon context management] |

---

### 1.4 Ce qui distingue un résultat professionnel du "vibe coding"

| Vibe coding | Développement professionnel avec agents |
|-------------|----------------------------------------|
| "Fais-moi une feature de X" | Prompt avec fichiers à lire, contraintes explicites, critères de succès mesurables |
| L'agent décide de l'architecture | L'architecture est fixée dans `CLAUDE.md`/`AGENTS.md` avant le lancement |
| Tests écrits après si le temps le permet | Tests spécifiés dans le prompt, vérifiés avant merge |
| Merge direct sur main | Branch → PR → review humaine → merge gatée par les tests |
| Relancer si ça bugge | Pattern de recovery documenté (voir §5.3) |
| Contexte pollué entre sessions | `/clear` entre tâches non liées, nouvelle session par phase |

---

## 2. Architecture de l'environnement de travail

### 2.1 Git Worktrees — Setup exact

Exécuter depuis la racine du repo RamyPulse (branche `feat/watch-first-expo-ready`) :

```bash
# 1. Merger discovery brain d'abord (prérequis)
git merge feat/discovery-brain-v1 --no-ff -m "merge(discovery): integrate discovery brain v1"
git push origin feat/watch-first-expo-ready

# 2. Créer la branche principale de travail
git checkout -b expo/main-dev
git push origin expo/main-dev

# 3. Créer le worktree Claude Code (backend)
mkdir -p ../ramypulse-worktrees
git worktree add ../ramypulse-worktrees/backend expo/main-dev
# Créer une branche backend dédiée depuis expo/main-dev
cd ../ramypulse-worktrees/backend
git checkout -b agent/claude-backend
git push origin agent/claude-backend

# 4. Créer le worktree Codex (frontend)
cd ../../ramypulse  # retour racine du repo
git worktree add ../ramypulse-worktrees/frontend expo/main-dev
cd ../ramypulse-worktrees/frontend
git checkout -b agent/codex-frontend
git push origin agent/codex-frontend

# 5. Copier les variables d'environnement dans chaque worktree
cd ../../ramypulse  # retour racine
cp .env ../ramypulse-worktrees/backend/.env 2>/dev/null || echo "Attention: .env vide, configurer avant J1"
cp .env ../ramypulse-worktrees/frontend/.env 2>/dev/null || true

# 6. Vérification
git worktree list
# Résultat attendu :
# /home/user/ramypulse            [expo/main-dev]
# /home/user/ramypulse-worktrees/backend   [agent/claude-backend]
# /home/user/ramypulse-worktrees/frontend  [agent/codex-frontend]
```

**Structure résultante :**

```
~/
├── ramypulse/                        # Repo principal — humain seulement
│   ├── api/                          # Backend FastAPI (NON touché par worktrees)
│   ├── frontend/                     # Frontend React (NON touché par worktrees)
│   ├── CLAUDE.md                     # Config Claude Code (commité)
│   ├── AGENTS.md                     # Config Codex (commité)
│   └── .git/                         # Repo principal
│
└── ramypulse-worktrees/
    ├── backend/                      # Worktree Claude Code
    │   ├── api/                      # Zone de travail Claude
    │   ├── scripts/
    │   ├── tests/
    │   └── .env                      # Copie du .env
    │
    └── frontend/                     # Worktree Codex
        ├── frontend/client/src/      # Zone de travail Codex
        ├── frontend/shared/          # LECTURE SEULE pour Codex
        └── .env                      # Copie du .env
```

**Branches Git :**

```
main
└── feat/watch-first-expo-ready (+ merge feat/discovery-brain-v1)
    └── expo/main-dev              (branche d'intégration humain)
        ├── agent/claude-backend   (Claude Code — backend)
        └── agent/codex-frontend   (Codex — frontend)
```

---

### 2.2 Fichiers de configuration agents

#### `CLAUDE.md` — Pour le worktree backend (`../ramypulse-worktrees/backend/CLAUDE.md`)

```markdown
# RamyPulse — Backend FastAPI

## Contexte du projet
RamyPulse est une application de veille marketing pour marques algériennes.
Backend : FastAPI + SQLite (33 tables), 51 endpoints, branche `feat/watch-first-expo-ready`.
Tu travailles dans le worktree `agent/claude-backend` — ne touche JAMAIS aux fichiers de `frontend/client/src/`.

## Commandes essentielles
- Activer l'environnement : `source .venv/bin/activate` (ou `uv sync` si uv est installé)
- Lancer le backend : `uvicorn api.main:app --reload --port 8000`
- Tests Python : `pytest tests/ -v --tb=short`
- Test unique : `pytest tests/test_dashboard.py -v`
- Vérifier un endpoint : `curl -H "X-API-Key: dev" http://localhost:8000/api/health`
- Lint Python : `ruff check api/` (si ruff installé) ou `flake8 api/`

## Architecture backend
- Point d'entrée : `api/main.py`
- Routeurs : `api/routers/` (12 fichiers, préfixe `/api`)
- Services métier : `api/services/`
- Modèles DB : `api/models.py` (SQLAlchemy ORM)
- Base de données : `ramypulse.db` (SQLite)
- Auth : Header `X-API-Key` via `Depends(get_current_client)` dans `api/auth.py`
- Tous les endpoints sont protégés sauf `/api/health`, `/api/status`, GET `/api/clients`

## Contrats d'interface — LIRE AVANT DE MODIFIER
- `frontend/shared/schema.ts` : types TypeScript partagés — SOURCE DE VÉRITÉ
- Ne JAMAIS modifier les schémas de réponse des 35 endpoints utilisés par le frontend sans synchronisation humaine
- Les 16 endpoints orphelins peuvent être modifiés librement
- Endpoint bulk à créer : `POST /api/recommendations/bulk-status` (voir tâche T09)

## Convention de nommage
- Python : snake_case pour variables/fonctions, PascalCase pour classes
- Endpoints : kebab-case dans les URLs (`/api/watch-runs`, pas `/api/watchRuns`)
- Réponses JSON : snake_case (le frontend gère la conversion dans `apiMappings.ts`)
- Branches : format `fix/nom-du-fix` ou `feat/nom-feature`

## Pattern de test à suivre (IMPORTANT)
1. Écrire le test AVANT l'implémentation (red)
2. Implémenter le minimum pour faire passer le test (green)
3. Refactorer sans casser les tests
4. TOUJOURS vérifier que `pytest tests/ -v` passe avant de commit

## Ce que tu NE dois PAS faire
- Modifier `frontend/client/src/` (zone Codex)
- Modifier `frontend/shared/schema.ts` sans validation humaine
- Committer directement sur `expo/main-dev` ou `main`
- Créer des endpoints qui cassent des contrats existants (breaking change)
- Utiliser `print()` pour le logging (utiliser `logging.getLogger(__name__)`)

## Seed data démo (priorité P0 J1)
Script à créer : `scripts/seed_demo.py`
Tenant cible : `demo-expo-2026`, marque `YaghurtPlus`
Voir feuille_de_route_expo.md §4.1 pour le schéma exact des données
```

---

#### `AGENTS.md` — Pour le worktree frontend (`../ramypulse-worktrees/frontend/AGENTS.md`)

```markdown
# RamyPulse — Frontend React

## Contexte du projet
RamyPulse est une application de veille marketing pour marques algériennes.
Frontend : React 18 + Vite 7 + TypeScript strict + Shadcn/ui + Tailwind CSS 3.4 + TanStack Query 5.
Design system : Obsidian (dark mode, fond #0A0A14, accent #ffb693, typographie Manrope/Inter).
Tu travailles dans le worktree `agent/codex-frontend` — ne touche JAMAIS aux fichiers de `api/`.

## Repository Layout
- Pages : `frontend/client/src/pages/` (9 pages fonctionnelles)
- Composants partagés : `frontend/client/src/components/`
- Logique métier : `frontend/client/src/lib/` (apiMappings.ts, queryClient.ts, etc.)
- Hooks : `frontend/client/src/hooks/`
- Contrats d'interface : `frontend/shared/schema.ts` — LECTURE SEULE
- Tests E2E : `frontend/tests/` (Playwright)

## Build, Test, and Lint Commands
```bash
cd frontend
npm install
npm run dev              # Dev server port 5173 (proxy /api → localhost:8000)
npm run build            # Build production dans dist/public/
npm run typecheck        # TypeScript strict — DOIT passer avant tout commit
npm run lint             # ESLint
npx playwright test      # Tests E2E
npx playwright test --ui # Mode interactif
```

## Engineering Conventions
- TypeScript strict mode — JAMAIS de `any` sans commentaire explicatif
- Composants fonctionnels React uniquement (pas de class components)
- TanStack Query pour tous les appels API — pas de `fetch()` brut sauf cas exceptionnel documenté
- Pour les mutations : TOUJOURS inclure `onError` avec un toast `variant: "destructive"`
- Pour les mutations batch : utiliser `Promise.all()` avec `mutateAsync()`, jamais `forEach + mutate()`
- Navigation : Wouter (`useLocation()`, `<Link>`) — pas `window.location`
- Formulaires : React Hook Form + Zod validation
- Client HTTP : utiliser `apiRequest()` depuis `lib/queryClient.ts` — injecte automatiquement X-API-Key et X-Ramy-Client-Id

## Conventions API (IMPORTANT)
- L'endpoint backend retourne snake_case, `apiMappings.ts` convertit en camelCase
- Ne PAS appeler directement l'API avec fetch() brut — utiliser `useQuery`/`useMutation` via `queryClient.ts`
- QueryKey format : `['/api/endpoint', { clientId, ...params }]`
- Le `clientId` vient de `useTenantContext()` — TOUJOURS inclure dans queryKey pour isolation multi-tenant

## Design tokens (à respecter)
- Fond : `#0A0A14` (var: --background)
- Accent primaire : `#ffb693` (var: --primary)
- Texte principal : `hsl(0 0% 95%)` (var: --foreground)
- Danger : `hsl(0 84% 60%)` (var: --destructive)
- Succès : `hsl(142 71% 45%)` (var: --success / text-green-400)
- Typographie titres : Manrope ; corps : Inter

## Constraints (Do Not)
- Ne jamais modifier `api/` (zone Claude Code)
- Ne jamais modifier `frontend/shared/schema.ts` sans validation humaine
- Ne jamais committer sur `expo/main-dev` ou `main` directement
- Ne jamais utiliser des images depuis des CDN Google externes (remplacer par avatars SVG initiales)
- Ne jamais hardcoder une couleur en dehors des tokens CSS définis dans `index.css`

## Definition of Done (par tâche)
1. `npm run typecheck` passe sans erreur
2. `npm run lint` passe sans warning
3. Le bouton/feature fonctionne manuellement dans le navigateur (port 5173)
4. Aucune regression sur les autres pages (tester la navigation complète)
5. PR description avec : ce qui a changé + pourquoi + screenshots si UI
```

---

### 2.3 Contrats d'interface partagés

Le fichier `frontend/shared/schema.ts` est la **source de vérité absolue** des types échangés entre backend et frontend. Il est **gelé** pendant les phases de travail parallèle et ne peut être modifié que lors des points de synchronisation humain (fin J1, fin J3, fin J6).

**Règle de référencement pour les agents :**
- Claude Code : `from api.schemas import DashboardSummary, AlertStatus, ...` doit correspondre aux interfaces de `shared/schema.ts`
- Codex : `import { DashboardSummary } from '@shared/schema'` est la seule source de typage autorisée
- Tout nouveau type partagé doit être ajouté dans `shared/schema.ts` par l'humain, lors d'un point de synchronisation

**Types critiques existants à ne pas casser :**

```typescript
// frontend/shared/schema.ts — extrait des types critiques
// (ces interfaces contractualisent 35 endpoints actifs)

interface AlertStatus {
  status: 'active' | 'acknowledged' | 'dismissed' | 'resolved';
}

interface SentimentLabel {
  value: 'positif' | 'negatif' | 'tres_negatif' | 'neutre' | 'mitige';
}

interface DashboardSummary {
  healthScore: number;        // /100
  trend: number;              // delta vs période précédente
  totalMentions: number;
  regions: RegionData[];
  products: ProductData[];
}

interface WatchlistMetrics {
  nssScore: number;
  volume: number;
  aspects: AspectData[];
  insights: string[];
}
```

**Nouveau type à ajouter lors de la synchronisation J3 :**

```typescript
// À ajouter lors du point de synchronisation fin J3
interface BulkStatusUpdate {
  ids: string[];
  status: 'archived' | 'dismissed' | 'active';
}
// Requis pour l'endpoint POST /api/recommendations/bulk-status (tâche T09)
```

---

### 2.4 Quality Gates automatiques

#### Pre-commit hooks (via `.git/hooks/pre-commit`)

**Pour le worktree backend** (`../ramypulse-worktrees/backend/.git/hooks/pre-commit`) :

```bash
#!/bin/bash
set -e

echo "🔍 [Claude Backend] Quality gate pre-commit..."

# 1. Activation environnement
source .venv/bin/activate 2>/dev/null || true

# 2. Lint Python
if command -v ruff &> /dev/null; then
  ruff check api/ --exit-zero
fi

# 3. Tests rapides (sans les tests d'intégration lents)
pytest tests/ -v --tb=short -x -m "not slow" --timeout=30
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ Tests échouent — commit bloqué"
  exit 1
fi

echo "✅ Quality gate backend passé"
exit 0
```

**Pour le worktree frontend** (`../ramypulse-worktrees/frontend/.git/hooks/pre-commit`) :

```bash
#!/bin/bash
set -e

echo "🔍 [Codex Frontend] Quality gate pre-commit..."

cd frontend

# 1. TypeScript strict
npm run typecheck
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ TypeScript errors — commit bloqué"
  exit 1
fi

# 2. Lint
npm run lint --silent
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ Lint errors — commit bloqué"
  exit 1
fi

echo "✅ Quality gate frontend passé"
exit 0
```

**Rendre exécutables :**
```bash
chmod +x ../ramypulse-worktrees/backend/.git/hooks/pre-commit
chmod +x ../ramypulse-worktrees/frontend/.git/hooks/pre-commit
```

#### Pattern test-then-implement pour les bugs

Avant que l'agent implémemente un fix, le test qui valide le comportement attendu doit exister et échouer (RED) :

```bash
# Exemple pour bug B3 (sentiment "tres_negatif")
# 1. Humain écrit le test dans le prompt :
# "tests/frontend/explorateur.test.ts doit contenir:
#  expect(formatSentimentLabel('tres_negatif')).toBe('Très Négatif')"
# 2. Codex exécute le test → RED (échoue car le cas n'existe pas)
# 3. Codex ajoute le case dans Explorateur.tsx → GREEN
# 4. Codex vérifie typecheck + lint → commit
```

---

## 3. Répartition du travail — Qui fait quoi

### 3.1 Matrice d'assignation des 36 tâches

| # | Tâche (feuille_de_route_expo.md) | Agent | Worktree | Fichiers touchés | Dépend de | Bloque |
|---|----------------------------------|-------|----------|-----------------|-----------|--------|
| T01 | Merger `feat/discovery-brain-v1` | **Humain** | Main | `.git/` | — | T02, T03 |
| T02 | Configurer `.env` (clés API) | **Humain** | Main | `.env` | T01 | T03, T09 |
| T03 | Vérifier démarrage backend + health check | **Claude Code** | backend | `api/main.py`, `requirements.txt` | T01, T02 | T05, T06, T07 |
| T04 | Lancer pytest + tests frontend | **Humain** | Main | `tests/`, `frontend/tests/` | T01 | T05 |
| T05 | B1 — Bouton "VOIR DETAILS" mort (Dashboard) | **Codex** | frontend | `frontend/client/src/pages/Dashboard.tsx` | T04 | T14 |
| T06 | B4 — Mutation campagne silencieuse | **Codex** | frontend | `frontend/client/src/pages/Campagnes.tsx` | T04 | — |
| T07 | B2 — Screenshot upload sans auth | **Codex** | frontend | `frontend/client/src/components/admin/AdminSourcesOps.tsx` | T04 | — |
| T08 | B3 — Sentiment "tres_negatif" manquant | **Codex** | frontend | `frontend/client/src/pages/Explorateur.tsx` | T04 | T16 |
| T09 | B5 — Race condition "Tout Archiver" | **Claude Code** | backend | `api/routers/recommendations.py` + **Codex** : `Recommandations.tsx` | T03 | — |
| T10 | Tuer/transformer 20 boutons morts | **Codex** | frontend | `Dashboard.tsx`, `Explorateur.tsx`, `Campagnes.tsx`, `Watchlists.tsx`, `AppShell.tsx`, `AdminSourcesOps.tsx` | T04 | T14, T15 |
| T11 | Mutations silencieuses (onError global) | **Codex** | frontend | `Campagnes.tsx`, `AdminSourcesOps.tsx`, `Recommandations.tsx` | T06 | — |
| T12 | Export CSV verbatims | **Codex** | frontend | `Explorateur.tsx`, `lib/utils.ts` | T10 | — |
| T13 | Export CSV campagnes | **Codex** | frontend | `Campagnes.tsx`, `lib/utils.ts` | T10 | — |
| T14 | CTA Dashboard → Recommandations (deep link) | **Codex** | frontend | `Dashboard.tsx`, `Recommandations.tsx` | T05, T10 | — |
| T15 | CTA Watchlists → Explorateur (avec watchlist param) | **Codex** | frontend | `Watchlists.tsx`, `Explorateur.tsx` | T10 | — |
| T16 | M11 — Filtre multi-source (channel param) | **Codex** | frontend | `Explorateur.tsx` | T08 | — |
| T17 | M1 — Titre "VENTES PAR PRODUIT" trompeur | **Codex** | frontend | `Dashboard.tsx` | T04 | — |
| T18 | M6 — Value/label inversés Recommandations | **Codex** | frontend | `Recommandations.tsx` | T04 | — |
| T19 | M7 — Dates ISO brutes | **Codex** | frontend | `Recommandations.tsx` | T04 | — |
| T20 | M8 — Loading/disabled boutons alertes | **Codex** | frontend | `Alertes.tsx` | T04 | — |
| T21 | M9 — Boutons non contextuels alertes | **Codex** | frontend | `Alertes.tsx` | T04 | — |
| T22 | M10 — Pagination alertes (>50) | **Codex** | frontend | `Alertes.tsx` | T04 | — |
| T23 | M12 — Confirmation actions destructives | **Codex** | frontend | `AdminSourcesOps.tsx` | T07 | — |
| T24 | M2 — Icônes TikTok / Google Maps | **Codex** | frontend | `Campagnes.tsx` | T04 | — |
| T25 | M3 — Avatars owners hack (Watchlists) | **Codex** | frontend | `Watchlists.tsx` | T04 | — |
| T26 | M4 — Delta NSS couleur positif/négatif | **Codex** | frontend | `Watchlists.tsx` | T04 | — |
| T27 | M5 — Label "Volume (m³)" NLP | **Codex** | frontend | `Recommandations.tsx` | T04 | — |
| T28 | Découpage AdminSourcesOps.tsx (1441 lignes) | **Codex** | frontend | `components/admin/*.tsx` (4 nouveaux fichiers) | T07, T23 | — |
| T29 | Google Stitch redesign UI/UX | **Humain** | Main | `DESIGN.md` (nouveau) | T10 | T30 |
| T30 | DESIGN.md commité comme source de vérité | **Humain** | Main | `DESIGN.md` | T29 | — |
| T31 | Bugs bas L1-L17 (17 bugs mineurs) | **Codex** | frontend | Multiple (voir §Phase 3) | T10 | — |
| T32 | Seed data démo réaliste | **Claude Code** | backend | `scripts/seed_demo.py` (nouveau) | T03 | T33, T34 |
| T33 | Script de démo documenté | **Humain** | Main | `docs/demo_script.md` | T32 | T35 |
| T34 | Tests E2E parcours démo | **Codex** | frontend | `frontend/tests/e2e/demo_flow.spec.ts` (nouveau) | T32 | T35 |
| T35 | Backup base de données | **Claude Code** | backend | `backups/ramypulse_demo_*.db` | T32 | — |
| T36 | Snapshot `.env` sécurisé | **Humain** | Main | `docs/env_status.md` | T02 | — |

**Résumé par agent :**

| Agent | Tâches assignées | Nombre |
|-------|-----------------|--------|
| **Humain** | T01, T02, T04, T29, T30, T33, T36 | 7 |
| **Claude Code** | T03, T09 (partie backend), T32, T35 | 4 (+1 partagée) |
| **Codex** | T05–T08, T09 (partie frontend), T10–T28, T31, T34 | 25 (+1 partagée) |

> **Note T09** : La tâche est split — Claude Code crée `POST /api/recommendations/bulk-status` ; Codex refactorise `Recommandations.tsx` pour utiliser cet endpoint. Point de synchronisation requis entre les deux (voir §3.3).

---

### 3.2 Planning jour par jour

#### Jour 1 — Phase 0 : Stabilisation

| Slot | Claude Code (backend) | Codex (frontend) | Humain | Sync / Merge |
|------|-----------------------|------------------|--------|--------------|
| Matin | T03 : Vérifier démarrage backend, corriger si nécessaire | — | T01 : Merger discovery-brain | — |
| Après-midi | T32 : Créer `scripts/seed_demo.py` avec tenant `demo-expo-2026` | — | T02 : Configurer `.env`, T04 : Lancer tests, documenter échecs | — |
| Soir | — | — | **SYNC J1** : Review tests échoués, valider `.env`, setup worktrees | **MERGE : aucun (J1 = setup)** |

**Ce que l'humain vérifie en fin J1 :**
- `git worktree list` retourne les 3 worktrees
- `curl http://localhost:8000/api/health` retourne `{"status": "ok"}`
- `pytest tests/ -v` documente les tests qui passent et échouent
- `CLAUDE.md` et `AGENTS.md` en place dans leurs worktrees respectifs

---

#### Jours 2-3 — Phase 1 : Fix Bugs Critiques (parallèle)

| Slot | Claude Code (backend) | Codex (frontend) | Humain | Sync / Merge |
|------|-----------------------|------------------|--------|--------------|
| J2 matin | T09-backend : Créer `POST /api/recommendations/bulk-status` | T05 : Fix bouton "VOIR DETAILS" (Dashboard) | Review prompts | — |
| J2 après-midi | T09-backend : Tests pytest pour le nouvel endpoint | T06 : onError mutation Campagnes + T07 : Fix screenshot auth | — | — |
| J3 matin | T35 : Backup DB, T03 : stabilisation restante | T08 : Fix sentiment "tres_negatif" + T09-frontend : Refactoriser "Tout Archiver" | — | — |
| J3 soir | — | — | **SYNC J3** : Review PRs backend + frontend | **MERGE J3 :** `agent/claude-backend` → `expo/main-dev` ; `agent/codex-frontend` → `expo/main-dev` |

**Ce que l'humain vérifie en fin J3 :**
- `pytest tests/ -v` : tous les tests Phase 1 passent
- `npm run typecheck` : zéro erreur TypeScript
- Les 5 bugs haute sévérité sont corrigés et testables manuellement
- Aucune régression sur les pages fonctionnelles (navigation complète)

---

#### Jours 4-6 — Phase 2 : Features (parallèle)

| Slot | Claude Code (backend) | Codex (frontend) | Humain | Sync / Merge |
|------|-----------------------|------------------|--------|--------------|
| J4 | — | T10 : Boutons morts (6 connecter + 13 supprimer) | Review plan Phase 2 | — |
| J5 | — | T11 : onError global + T12 : Export CSV verbatims + T13 : Export CSV campagnes | — | — |
| J6 matin | — | T14 : Deep link Dashboard → Recommandations + T15 : Watchlists → Explorateur + T16 : Filtre multi-source | — | — |
| J6 soir | — | T17–T27 : 11 bugs moyens | **SYNC J6** : Review PRs, tests E2E manuels | **MERGE J6 :** `agent/codex-frontend` → `expo/main-dev` |

**Ce que l'humain vérifie en fin J6 :**
- Parcours démo complet réalisable sans blocage
- Export CSV fonctionne (Explorateur + Campagnes)
- Tous les boutons CTA naviguent vers la bonne page
- Filtre multi-source transmet le paramètre `channel`

---

#### Jours 7-8 — Phase 3 : Polish (parallèle)

| Slot | Claude Code (backend) | Codex (frontend) | Humain | Sync / Merge |
|------|-----------------------|------------------|--------|--------------|
| J7 | — | T28 : Découpage AdminSourcesOps (4 sous-composants) | T29 : Google Stitch redesign (screenshots → Stitch → DESIGN.md) | — |
| J8 | — | T31 : Bugs bas L1-L17 + application tokens DESIGN.md | T30 : Commiter DESIGN.md | **MERGE J8 :** `agent/codex-frontend` → `expo/main-dev` |

---

#### Jours 9-10 — Phase 4 : Démo & Préparation Expo

| Slot | Claude Code (backend) | Codex (frontend) | Humain | Sync / Merge |
|------|-----------------------|------------------|--------|--------------|
| J9 | — | T34 : Tests E2E parcours démo (`demo_flow.spec.ts`) | T33 : Script de démo documenté + répétition J9 | — |
| J10 | — | — | Répétition finale + T36 : Snapshot `.env` + validation checklist 20 points | **MERGE FINAL :** `expo/main-dev` → `feat/watch-first-expo-ready` |

---

### 3.3 Points de synchronisation

**SYNC J1 — Setup** (30 min)
- Responsable : Humain
- Actions : setup worktrees, copier `.env`, placer CLAUDE.md/AGENTS.md, lancer tests baseline
- Artefact produit : `docs/baseline_test_results.md` (liste des tests qui passent/échouent avant toute modification)

**SYNC J3 — Merge Phase 1** (45 min)
- Responsable : Humain
- Actions : Review PR backend (endpoint bulk-status), review PR frontend (5 bugs critiques), tests d'intégration `POST /api/recommendations/bulk-status` depuis le frontend
- Condition de merge : `pytest tests/test_recommendations.py` passe + `npm run typecheck` passe + test manuel de chaque bug corrigé
- Si bloquant : reverter le composant bug et ouvrir un issue documenté

**SYNC J6 — Merge Phase 2** (1h)
- Responsable : Humain
- Actions : Parcours démo complet à la main (8 minutes du script), tester export CSV, tester navigation profonde Dashboard → Recommandations
- Condition de merge : aucun bouton mort dans le parcours démo + exports CSV fonctionnels + filtre multi-source actif
- Artefact : `docs/sync_j6_results.md`

**SYNC J8 — Merge Phase 3** (30 min)
- Responsable : Humain
- Actions : Review visuelle DESIGN.md appliqué dans les composants, vérifier découpage AdminSourcesOps, tester que tous les sous-composants sont fonctionnels
- Condition de merge : `npm run typecheck` passe, aucune régression visuelle majeure

---

## 4. Prompts exécutables

### Phase 0 : Stabilisation (J1) — 2 prompts

---

#### PROMPT-P0-01 : Claude Code — Vérifier et stabiliser le backend

```
CONTEXTE :
Tu travailles sur RamyPulse, une application de veille marketing algérienne.
Backend FastAPI, branche feat/watch-first-expo-ready.
Worktree : ../ramypulse-worktrees/backend/
Ton fichier de config : CLAUDE.md (lis-le en premier)

FICHIERS À LIRE EN PRIORITÉ :
1. CLAUDE.md (instructions spécifiques projet)
2. api/main.py (point d'entrée)
3. requirements.txt (dépendances)
4. tests/ (liste des tests existants)

TÂCHE T03 — Vérification et stabilisation backend :
1. Activer l'environnement Python : source .venv/bin/activate
2. Installer les dépendances : pip install -r requirements.txt
3. Lancer : uvicorn api.main:app --reload --port 8000 &
4. Vérifier : curl http://localhost:8000/api/health
5. Vérifier : curl http://localhost:8000/api/status
6. Si des erreurs d'import existent → corriger UNIQUEMENT les imports manquants, ne pas restructurer
7. Lancer : pytest tests/ -v --tb=short > /tmp/pytest_baseline.txt 2>&1
8. Créer docs/baseline_test_results.md avec le contenu de /tmp/pytest_baseline.txt

TÂCHE T32 — Seed data démo (à faire APRÈS que le backend démarre sans erreur) :
Créer scripts/seed_demo.py qui peuple la DB avec :
- Tenant : client_id="demo-expo-2026", brand="YaghurtPlus", product="Yaghourt Abricot 150g"
- 200 verbatims réalistes (Facebook 40%, Google Maps 35%, YouTube 25%)
- Sentiments : 40% positif, 30% neutre, 20% negatif, 10% tres_negatif
- Wilayas : Alger, Oran, Constantine, Annaba, Tlemcen
- Score santé : 72/100, tendance +5
- 2 alertes critiques, 3 moyennes, 5 basses
- 3 recommandations IA pré-générées avec priorité/rationale/KPI
- 3 campagnes (1 active, 1 archivée, 1 terminée) avec impact NSS simulé
- 2 watchlists actives (marque + concurrent "LactoDar")

Le script doit avoir une option --reset pour effacer et recréer.
Commande finale : python scripts/seed_demo.py --tenant demo-expo-2026 --reset

CONTRAINTES :
- Ne pas toucher aux fichiers frontend/client/src/
- Ne pas modifier frontend/shared/schema.ts
- Committer sur la branche agent/claude-backend uniquement
- Message de commit : "feat(seed): add demo data seed script for expo"

CRITÈRES DE SUCCÈS :
- curl http://localhost:8000/api/health retourne {"status": "ok", "db_status": "ok"}
- python scripts/seed_demo.py --tenant demo-expo-2026 --reset termine sans erreur
- curl -H "X-API-Key: dev" http://localhost:8000/api/dashboard/summary?client_id=demo-expo-2026 retourne un JSON avec healthScore:72
- pytest tests/ -v passe (ou le nombre d'échecs est documenté dans docs/baseline_test_results.md)
```

---

#### PROMPT-P0-02 : Codex — Setup worktree frontend et baseline

```
CONTEXTE :
Tu travailles sur RamyPulse, une SPA React de veille marketing algérienne.
Frontend : React 18 + Vite 7 + TypeScript strict + Shadcn/ui + Tailwind CSS 3.4.
Worktree : ../ramypulse-worktrees/frontend/
Ton fichier de config : AGENTS.md (lis-le en premier)

FICHIERS À LIRE EN PRIORITÉ :
1. AGENTS.md (instructions spécifiques projet)
2. frontend/package.json (scripts disponibles)
3. frontend/client/src/App.tsx (routing principal)
4. frontend/shared/schema.ts (contrats d'interface — LECTURE SEULE)

TÂCHE SETUP :
1. cd frontend && npm install
2. npm run typecheck > /tmp/ts_baseline.txt 2>&1
3. npm run lint > /tmp/lint_baseline.txt 2>&1
4. Documenter tous les erreurs TypeScript existantes dans docs/frontend_baseline.md
   (ce sont les erreurs PRÉ-existantes, ne pas les corriger maintenant sauf si elles bloquent la suite)

TÂCHE : Inventorier les boutons morts (préparer Phase 1)
Lis les fichiers suivants et note les boutons qui n'ont PAS de onClick ou href :
- frontend/client/src/pages/Dashboard.tsx
- frontend/client/src/components/AppShell.tsx
Pour chaque bouton mort trouvé, créer un commentaire TODO dans le fichier :
// TODO-BOUTON-MORT: [description du bouton] → [action attendue selon feuille_de_route]

NE PAS IMPLÉMENTER LES FIXES MAINTENANT — uniquement les TODOs.

CONTRAINTES :
- Ne pas toucher à api/
- Ne pas modifier frontend/shared/schema.ts
- Committer sur agent/codex-frontend uniquement
- Message : "chore(audit): add TODO markers for dead buttons Phase 0"

CRITÈRES DE SUCCÈS :
- npm install réussit sans erreur
- docs/frontend_baseline.md créé avec liste des erreurs TypeScript préexistantes
- TODOs ajoutés dans Dashboard.tsx et AppShell.tsx pour chaque bouton mort
```

---

### Phase 1 : Fix Critiques (J2-J3) — 5 prompts

---

#### PROMPT-P1-01 : Claude Code — Endpoint bulk-status recommandations (T09-backend)

```
CONTEXTE :
RamyPulse backend FastAPI. Branche agent/claude-backend.
Lecture obligatoire : CLAUDE.md, api/routers/recommendations.py, frontend/shared/schema.ts

TÂCHE T09-BACKEND :
Créer l'endpoint POST /api/recommendations/bulk-status dans api/routers/recommendations.py

SPÉCIFICATION :
- URL : POST /api/recommendations/bulk-status
- Auth : Depends(get_current_client) (comme tous les endpoints)
- Body : {"ids": ["uuid1", "uuid2", ...], "status": "archived" | "dismissed" | "active"}
- Comportement : mettre à jour le status de TOUTES les recommandations listées en une seule transaction DB
- Retour : {"updated": N, "ids": [...ids mis à jour...]}
- Si un ID n'existe pas → ignorer silencieusement (ne pas lever d'erreur)
- Si status invalide → HTTP 422 avec détail

TESTS À ÉCRIRE D'ABORD (TDD) :
Créer tests/test_recommendations_bulk.py avec :
1. test_bulk_status_archive_multiple() — archive 3 recs, vérifie que les 3 ont status=archived
2. test_bulk_status_ignores_unknown_ids() — passe des IDs inexistants, vérifie que ça ne plante pas
3. test_bulk_status_invalid_status() — passe status="INVALID", vérifie HTTP 422
4. test_bulk_status_empty_list() — passe ids=[], vérifie {"updated": 0}

Lancer pytest tests/test_recommendations_bulk.py -v → doit être RED (tests échouent car pas encore implémenté)
PUIS implémenter dans api/routers/recommendations.py
PUIS relancer → doit être GREEN

CONTRAINTES :
- Ne pas casser les endpoints GET/PUT /api/recommendations existants
- Utiliser la même transaction SQLAlchemy que le reste du fichier
- Ne pas toucher à frontend/

CRITÈRES DE SUCCÈS :
- pytest tests/test_recommendations_bulk.py -v : 4/4 tests passent
- curl -X POST -H "X-API-Key: dev" -H "Content-Type: application/json" \
  -d '{"ids":["test-id"],"status":"archived"}' \
  http://localhost:8000/api/recommendations/bulk-status retourne HTTP 200
```

---

#### PROMPT-P1-02 : Codex — Fix 5 bugs haute sévérité (T05, T06, T07, T08, T09-frontend)

```
CONTEXTE :
RamyPulse frontend React, TypeScript strict.
Branche agent/codex-frontend.
Lecture obligatoire : AGENTS.md, puis les fichiers spécifiés ci-dessous.

IMPORTANT : Lire ces fichiers AVANT de modifier quoi que ce soit :
1. frontend/client/src/lib/queryClient.ts (apiRequest, useMutation patterns)
2. frontend/client/src/lib/apiMappings.ts (transformations)
3. frontend/client/src/pages/Dashboard.tsx
4. frontend/client/src/pages/Campagnes.tsx
5. frontend/client/src/components/admin/AdminSourcesOps.tsx
6. frontend/client/src/pages/Explorateur.tsx
7. frontend/client/src/pages/Recommandations.tsx

BUG B1 — Dashboard.tsx L~190 (priorité absolue) :
- Trouver le bouton {action.ctaLabel} sans onClick
- Ajouter : onClick={() => navigate('/recommandations')} 
- Utiliser le hook useLocation de Wouter : const [, navigate] = useLocation()
- Faire de même pour les cartes alertes cliquables (cursor-pointer sans handler)
- Test : naviguer vers Dashboard → cliquer "VOIR DETAILS" → doit arriver sur /recommandations

BUG B4 — Campagnes.tsx :
- Trouver useMutation de création campagne sans onError
- Ajouter : onError: (error: Error) => { toast({ title: "Erreur création", description: error.message, variant: "destructive" }) }
- Test : soumettre le formulaire campagne avec un nom vide → doit afficher un toast rouge

BUG B2 — AdminSourcesOps.tsx :
- Chercher : fetch('/api/social-metrics/posts/
- Remplacer par : apiRequest('/api/social-metrics/posts/${postId}/metrics/screenshot', { method: 'POST', body: formData })
- IMPORTANT : apiRequest() depuis lib/queryClient.ts injecte automatiquement X-API-Key et X-Ramy-Client-Id
- Test : vérifier que l'appel inclut le header X-API-Key dans les DevTools network

BUG B3 — Explorateur.tsx :
- Trouver la fonction formatSentimentLabel()
- Ajouter le case manquant : case 'tres_negatif': return 'Très Négatif' (avec couleur text-red-700 ou similaire)
- Test : si des verbatims ont sentiment=tres_negatif, ils doivent afficher "Très Négatif" en rouge foncé

BUG B5 — Recommandations.tsx (APRÈS que Claude Code ait créé l'endpoint bulk-status) :
- Trouver "Tout Archiver" avec forEach + mutate()
- Remplacer par :
  const handleArchiveAll = async () => {
    const ids = recommendations.map(r => r.id);
    await bulkStatusMutation.mutateAsync({ ids, status: 'archived' });
    queryClient.invalidateQueries({ queryKey: ['/api/recommendations'] });
  }
- bulkStatusMutation doit appeler POST /api/recommendations/bulk-status
- Si l'endpoint n'est pas encore disponible → implémenter en fallback avec Promise.all(ids.map(id => mutateAsync(id))) puis un seul invalidateQueries

CONTRAINTES :
- npm run typecheck doit passer après chaque bug corrigé
- Ne pas modifier frontend/shared/schema.ts
- Un commit par bug, message format : "fix(B1): connect VOIR DETAILS CTA to recommendations"

CRITÈRES DE SUCCÈS par bug :
- B1 : click sur "VOIR DETAILS" navigue vers /recommandations ✓
- B4 : formulaire campagne invalide → toast destructive visible ✓  
- B2 : upload screenshot → network tab montre X-API-Key header ✓
- B3 : verbatims tres_negatif affichent "Très Négatif" en rouge ✓
- B5 : "Tout Archiver" n'envoie qu'une requête (ou N séquentielles), cache invalidé une seule fois ✓
- npm run typecheck : 0 erreur sur tous les fichiers modifiés ✓
```

---

#### PROMPT-P1-03 : Codex — 20 boutons morts (T10)

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
Lecture obligatoire : AGENTS.md, puis l'inventaire des boutons morts dans audit_frontend.md §6

FICHIERS À MODIFIER :
- frontend/client/src/pages/Dashboard.tsx
- frontend/client/src/pages/Explorateur.tsx
- frontend/client/src/pages/Campagnes.tsx
- frontend/client/src/pages/Watchlists.tsx
- frontend/client/src/components/AppShell.tsx
- frontend/client/src/components/admin/AdminSourcesOps.tsx

DÉCISIONS PAR BOUTON (reproduire exactement) :

CONNECTER (endpoint existant / navigation évidente) :
1. Dashboard "VOIR DETAILS" → navigate('/recommandations') [déjà fait en B1, vérifier]
2. Dashboard carte alerte → navigate('/alertes')
3. Dashboard carte action → navigate('/recommandations')
4. Explorateur "Filtrer" → ouvrir un Popover Shadcn/ui avec les filtres sentiment + wilaya (GET /api/explorer/verbatims supporte ces params)
5. Watchlists "Voir les détails analytiques" → navigate('/explorateur?watchlist=' + watchlist.id)
6. AdminSources "Voir tout l'historique" → ouvrir un Dialog Shadcn/ui avec la liste des runs (endpoint GET /api/admin/sources/{id}/runs)
7. AppShell "notifications" → toast("Aucune nouvelle notification")
8. AppShell "sensors" → navigate('/admin-sources')

SUPPRIMER (retirer le bouton/lien) :
9. Explorateur "Exporter" → remplacer par badge disabled "Bientôt disponible" (grisé, cursor-not-allowed)
10. Campagnes "EXPORTER DATA" → idem badge disabled
11. AdminSources "Pipelines" nav → retirer l'élément ou ajouter title="Bientôt disponible" + pointer-events:none
12. AdminSources "Logs" nav → idem
13. AdminSources icône "notifications" header → retirer
14. AdminSources icône "settings" header → retirer
15. AdminSources "New Pipeline" → retirer
16. AdminSources "Support" sidebar → retirer
17. AdminSources "Documentation" sidebar → peut pointer vers /api/docs (Swagger), sinon retirer
18. AdminSources nav items (Connectors, Health, Validation, Archive) → ajouter Badge "Bientôt" sur chaque item
19. AppShell "language" → retirer
20. AppShell "grid_view" → retirer

CONTRAINTES :
- npm run typecheck doit passer
- Ne pas casser les boutons FONCTIONNELS existants
- Pour les éléments "Bientôt disponible" : utiliser le composant Tooltip de Shadcn/ui
- Commit message : "fix(buttons): connect/remove 20 dead buttons"

CRITÈRES DE SUCCÈS :
- Aucun bouton cliquable dans le parcours démo ne fait "rien"
- npm run typecheck : 0 erreur ✓
- Navigation Dashboard → Alertes → Recommandations fonctionne entièrement ✓
```

---

### Phase 2 : Features (J4-J6) — 4 prompts

---

#### PROMPT-P2-01 : Codex — Export CSV + Mutations onError global (T11, T12, T13)

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
Lecture obligatoire : AGENTS.md, frontend/client/src/lib/utils.ts, frontend/client/src/lib/queryClient.ts

TÂCHE T11 — onError global sur toutes mutations sans handler :
Exécuter dans le terminal : grep -rn "useMutation" frontend/client/src --include="*.tsx" | grep -v onError
Pour chaque mutation trouvée sans onError, ajouter :
onError: (error: Error) => {
  toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
}
Fichiers concernés : Campagnes.tsx, AdminSourcesOps.tsx, Recommandations.tsx

TÂCHE T12 — Export CSV verbatims (Explorateur.tsx) :
1. Ajouter dans frontend/client/src/lib/utils.ts :
   export function convertToCSV(items: Record<string, unknown>[]): string {
     // Extraire les headers du premier élément
     // Générer les lignes CSV avec échappement des virgules et guillemets
   }
   export function downloadBlob(content: string, filename: string, mimeType: string): void {
     const blob = new Blob([content], { type: mimeType });
     const url = URL.createObjectURL(blob);
     const a = document.createElement('a'); a.href = url; a.download = filename;
     a.click(); URL.revokeObjectURL(url);
   }
2. Dans Explorateur.tsx, connecter le bouton "Exporter" (actuellement disabled) :
   Récupérer tous les verbatims : GET /api/explorer/verbatims?page_size=1000
   Colonnes CSV : source, sentiment, content, wilaya, date, aspect
   Nom du fichier : verbatims_${new Date().toISOString().slice(0,10)}.csv
   Afficher un toast "Export en cours..." puis "Export téléchargé (N verbatims)"

TÂCHE T13 — Export CSV campagnes (Campagnes.tsx) :
1. Connecter "EXPORTER DATA" (actuellement disabled) :
   Récupérer : GET /api/campaigns (liste complète)
   Colonnes CSV : name, type, platform, influencer, budget, status, startDate, endDate
   Nom du fichier : campagnes_${new Date().toISOString().slice(0,10)}.csv

CONTRAINTES :
- npm run typecheck doit passer
- Pas de dépendance externe pour le CSV (pur JS, pas de papaparse)
- Commit message : "feat(export): add CSV export for verbatims and campaigns"

CRITÈRES DE SUCCÈS :
- Cliquer "Exporter" dans Explorateur → fichier verbatims_*.csv téléchargé ✓
- Cliquer "EXPORTER DATA" dans Campagnes → fichier campagnes_*.csv téléchargé ✓
- Les mutations sans onError ont maintenant un toast d'erreur ✓
```

---

#### PROMPT-P2-02 : Codex — Bugs moyens M1-M12 (T16-T27)

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
Lecture obligatoire : AGENTS.md

Corriger les 12 bugs moyens suivants (chacun est un micro-fix) :

M1 — Dashboard.tsx : Renommer "VENTES PAR PRODUIT" → "PERFORMANCE PRODUIT — Score Sentiment"
M2 — Campagnes.tsx : Importer SiTiktok depuis react-icons/si, FaMapMarkerAlt depuis react-icons/fa pour icônes manquantes
M3 — Watchlists.tsx : Remplacer buildOwners() hack par avatar générique coloré + tooltip "Owners non disponibles"
M4 — Watchlists.tsx : Corriger couleur delta NSS → delta > 0 ? 'text-green-400' : 'text-red-400'
M5 — Recommandations.tsx : Remplacer label "Volume (m³)" par "Volume mentions"
M6 — Recommandations.tsx : Inverser value et label dans la carte "Dernière run"
M7 — Recommandations.tsx : Formatter les dates ISO avec date-fns → format(new Date(iso), 'dd/MM/yyyy HH:mm', {locale: fr})
M8 — Alertes.tsx : Ajouter disabled={isPending} + spinner sur les 3 boutons d'action pendant mutation
M9 — Alertes.tsx : Masquer les boutons non-pertinents selon alert.status (résolu → pas "Résoudre", etc.)
M10 — Alertes.tsx : Ajouter bouton "Charger plus" → limit state +50 (state local useState<number>(50))
M11 — Explorateur.tsx : Mapper les chips source sélectionnées → paramètre channel dans la query (jointure avec virgule)
M12 — AdminSourcesOps.tsx : Envelopper les appels DELETE dans AlertDialog Shadcn/ui avec confirmation "Confirmer la suppression ?"

Pour M7, importer la locale fr depuis date-fns/locale/fr (déjà installé dans package.json).

CONTRAINTES :
- npm run typecheck doit passer
- Un commit par groupe de bugs liés (par page)
- Exemple : "fix(watchlists): fix delta NSS color and owners avatar" (M3+M4 ensemble)

CRITÈRES DE SUCCÈS :
- Titre Dashboard ne dit plus "VENTES PAR PRODUIT" ✓
- Delta NSS vert si positif, rouge si négatif ✓
- Label "Volume mentions" visible dans Recommandations ✓
- Boutons alertes en état loading pendant mutation ✓
- Filtre multi-source transmet channel=facebook,youtube,... ✓
- npm run typecheck : 0 erreur ✓
```

---

### Phase 3 : Polish (J7-J8) — 2 prompts

---

#### PROMPT-P3-01 : Codex — Découpage AdminSourcesOps.tsx (T28)

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
AdminSourcesOps.tsx est un composant monolithe de 1441 lignes. Le découper en 4 sous-composants.
Lecture obligatoire : AGENTS.md, frontend/client/src/components/admin/AdminSourcesOps.tsx

STRUCTURE CIBLE :
frontend/client/src/components/admin/
├── AdminSourcesOps.tsx          # Orchestrateur (< 80 lignes — tabs + routing)
├── AdminSourcesView.tsx         # Sous-vue Sources (sync, health, snapshots)
├── AdminCredentialsView.tsx     # Sous-vue Credentials (liste, création, désactivation)
├── AdminCampaignOpsView.tsx     # Sous-vue Campaign Ops (posts, screenshots, revenue)
└── AdminSchedulerView.tsx       # Sous-vue Scheduler (tick, résultat)

RÈGLES D'EXTRACTION :
1. Commencer par AdminSchedulerView (la plus simple — 1 seul endpoint /api/admin/scheduler/tick)
2. Vérifier que le composant fonctionne avant de passer au suivant
3. Chaque sous-vue garde ses propres useQuery/useMutation
4. AdminSourcesOps.tsx ne garde que les imports + le composant de tabs + le routing vers les sous-vues
5. Aucun état NE doit être partagé via props descendantes (chaque vue est autonome)
6. Pour les queries partagées (ex: liste des campagnes utilisée dans CampaignOps ET dans la liste générale) :
   dupliquer la query — mieux qu'un état partagé fragile

CONTRAINTES :
- Ne pas changer la fonctionnalité — découpage pur, zéro regression
- npm run typecheck doit passer après chaque extraction
- Garder une copie de sauvegarde : AdminSourcesOps_backup.tsx (commité)
- Si une extraction introduit une régression → revenir à la backup et ne pas continuer

CRITÈRES DE SUCCÈS :
- AdminSourcesOps.tsx < 100 lignes ✓
- Les 4 sous-composants existent et sont fonctionnels ✓
- npm run typecheck : 0 erreur ✓
- Test manuel : toutes les sous-vues de l'admin sources fonctionnent (Sources, Credentials, Campaign Ops, Scheduler) ✓
```

---

#### PROMPT-P3-02 : Codex — Bugs bas L1-L17 + tokens DESIGN.md (T31)

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
DESIGN.md est maintenant commité à la racine du repo — lire ses tokens avant d'appliquer les corrections visuelles.

Corriger les 17 bugs bas (liste exhaustive) :

L1  — Dashboard.tsx : Remplacer "2024" hardcodé par {new Date().getFullYear()}
L2  — Dashboard.tsx : Chercher/remplacer "Base sur" → "Basé sur"
L3  — Alertes.tsx : "Ecarter" → "Écarter" ; "Reconnaitre" → "Reconnaître"
L4  — Alertes.tsx : MOYENNE → `amber-500/20` bg ; BASSE → `slate-500/20` bg (distinguer visuellement)
L5  — Alertes.tsx : Cercle avatar extraits sociaux → afficher initiales de source (fb→FB, yt→YT, gm→GM)
L6  — Campagnes.tsx : Avatars campagne CDN → remplacer par composant AvatarInitials(name) → SVG avec initiales
L7  — Campagnes.tsx : Avatar top performeur hardcodé → idem AvatarInitials
L8  — Campagnes.tsx : isOpen initial → false (formulaire fermé par défaut)
L9  — Campagnes.tsx : Validation Zod → budget: z.number().positive() + endDate après startDate
L10 — Explorateur.tsx : value === 'n/a' → '—' (tiret cadratin)
L11 — not-found.tsx : Traduire en français : "Page introuvable" + "Cette page n'existe pas."
L12 — Recommandations.tsx : Remplacer <Link><a> imbriqués → <Link className="..."> directement (Wouter accepte)
L13 — WatchOnboarding.tsx : Exposer les langues comme champ select optionnel (défaut ["fr","ar"])
L14 — Sidebar.tsx : Remplacer "Ammar, Brand Manager" hardcodé → {tenantId ? tenantId.slice(0,12) + '...' : 'Démo'}
L15 — Multiple : Créer lib/avatars.ts avec generateInitialsSVG(name: string): string, importer depuis les pages
L16 — Admin (futurs sous-composants) : Ajouter htmlFor + <label> sur tous les <input> des formulaires
L17 — AdminSourcesOps.tsx : Ré-inclure TikTok dans les options de création de source

Pour AvatarInitials (L6, L7, L15) :
- Prendre les 2 premières lettres capitalisées du nom
- Background : générer une couleur HSL déterministe depuis le hash du nom
- SVG inline (pas d'image externe)

CONTRAINTES :
- npm run typecheck doit passer
- Pas de breaking change sur les fonctionnalités existantes
- Commit unique : "fix(polish): fix 17 low-severity bugs + apply DESIGN.md tokens"

CRITÈRES DE SUCCÈS :
- Copyright Dashboard affiche 2026 (ou l'année courante) ✓
- "Basé sur" correctement accentué ✓
- Boutons Alertes avec accents corrects ✓
- Page 404 en français ✓
- Formulaire Campagnes fermé par défaut ✓
- npm run typecheck : 0 erreur ✓
```

---

### Phase 4 : Tests E2E démo — 1 prompt

---

#### PROMPT-P4-01 : Codex — Tests E2E parcours démo (T34)

```
CONTEXTE :
RamyPulse. Branche agent/codex-frontend.
Le seed data démo est disponible (tenant demo-expo-2026, score 72).
Playwright est installé (@playwright/test dans devDependencies).

TÂCHE : Créer frontend/tests/e2e/demo_flow.spec.ts

Le test doit simuler le parcours de démo de 8 minutes :

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const TENANT_ID = 'demo-expo-2026';

test.beforeEach(async ({ page }) => {
  // Forcer le tenant démo via localStorage
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

test('Acte 2 — Navigation vers alertes et action', async ({ page }) => {
  await page.goto(BASE_URL + '#/alertes');
  await expect(page.getByText('Console d'Alertes')).toBeVisible();
  // Filtrer par critique
  const critiqueFilter = page.getByRole('button', { name: /critique/i }).first();
  await critiqueFilter.click();
  // Cliquer sur première alerte
  const firstAlert = page.locator('[data-testid="alert-item"]').first();
  if (await firstAlert.count() > 0) {
    await firstAlert.click();
    // Cliquer Reconnaître
    await page.getByRole('button', { name: /reconnaître/i }).click();
  }
});

test('Acte 3 — Explorateur recherche sémantique', async ({ page }) => {
  await page.goto(BASE_URL + '#/explorateur');
  await page.fill('input[placeholder*="Explorer"]', 'goût yaghourt');
  await page.getByRole('button', { name: 'Explorer' }).click();
  await expect(page.locator('.verbatim-card, [data-verbatim]').first()).toBeVisible({ timeout: 15000 });
});

test('Acte 4 — Export CSV verbatims', async ({ page }) => {
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
  
  // Filtrer les erreurs connues non-bloquantes
  const criticalErrors = errors.filter(e => !e.includes('favicon') && !e.includes('ResizeObserver'));
  expect(criticalErrors).toHaveLength(0);
});

CONTRAINTES :
- Les tests doivent passer avec le backend démarré et le seed demo-expo-2026 chargé
- Utiliser des timeouts raisonnables (10s max par assertion)
- data-testid à ajouter dans les composants si nécessaires (Alert items, etc.)
- Commit : "test(e2e): add demo flow E2E test suite"

CRITÈRES DE SUCCÈS :
- npx playwright test tests/e2e/demo_flow.spec.ts : 5/5 tests passent ✓
- Aucun crash dans la console lors du parcours ✓
```

---

## 5. Gestion des tokens et crédits

### 5.1 Budget tokens estimé par phase

| Phase | Agent | Tâches | Tokens input (est.) | Tokens output (est.) | Coût approx. |
|-------|-------|--------|---------------------|----------------------|--------------|
| P0 — Stabilisation | Claude Code | T03, T32 | ~40 000 | ~15 000 | ~0,80 $ (Sonnet 4) |
| P0 — Stabilisation | Codex | Setup, TODOs | ~25 000 | ~8 000 | ~0,50 $ (o4-mini) |
| P1 — Fixes critiques | Claude Code | T09-backend | ~30 000 | ~20 000 | ~0,60 $ |
| P1 — Fixes critiques | Codex | T05–T08, T10 | ~80 000 | ~40 000 | ~2,50 $ (o4-mini) |
| P2 — Features | Codex | T11–T27 | ~100 000 | ~60 000 | ~3,00 $ |
| P3 — Polish | Codex | T28, T31 | ~60 000 | ~40 000 | ~2,00 $ |
| P4 — E2E | Codex | T34 | ~20 000 | ~15 000 | ~0,50 $ |
| **TOTAL** | | **36 tâches** | **~355 000** | **~198 000** | **~10 $ approx.** |

> **Note** : Les estimations sont basées sur les données de `research_ai_agent_best_practices.md §1.8` : multi-agent ~15× plus que chat, agents simples ~4× plus que chat. Avec Claude Sonnet 4 à ~$3/M input et ~$15/M output, et Codex o4-mini à ~$1,5/M input et ~$6/M output.

---

### 5.2 Techniques d'optimisation

**Garder le contexte propre (Claude Code) :**
- Utiliser `/clear` entre chaque tâche non liée (ex : entre T03 et T32)
- Utiliser `/compact "résumé bref des décisions prises"` à la fin d'une longue session
- Ne jamais faire lire plus de 3 fichiers volumineux dans le même contexte
- Si le contexte est > 60% utilisé → commencer une nouvelle session avec `/resume`

**Garder le contexte propre (Codex) :**
- Lancer Codex avec `codex --model o4-mini` pour les tâches de fix simple (moins cher)
- Lancer avec `codex --model o3` uniquement pour les tâches complexes (découpage AdminSourcesOps, tests E2E)
- Utiliser `--context-strategy summarize` pour les longues sessions

**Quand commencer une nouvelle session vs continuer :**
| Condition | Action |
|-----------|--------|
| Tâche terminée, commits faits | Nouvelle session |
| Changement de phase (P1 → P2) | Nouvelle session avec `claude --continue` pour voir l'historique git |
| Contexte > 70% plein | `/compact` ou nouvelle session |
| Agent répète la même erreur 2 fois | `/clear` + réécrire le prompt initial |
| Bug introduit dans la session courante | `Esc+Esc` → `/rewind` pour annuler |

---

### 5.3 Limites et workarounds

**Si l'agent atteint la limite de tokens :**
1. Ne pas continuer à corriger dans la même session
2. Faire un commit de l'état courant (même incomplet) : `git commit -m "wip: [nom tâche] partial"`
3. Nouvelle session : `claude --continue` ou `codex --resume`
4. Passer un "handoff prompt" : "La session précédente a commencé T10. Les boutons #1-#8 sont connectés. Reprendre à partir du bouton #9. Lire les TODOs dans Dashboard.tsx et AppShell.tsx."

**Si le code produit a des bugs :**
1. **1er incident** : Fournir le message d'erreur exact dans le même contexte → l'agent itère
2. **2ème incident (même bug)** : `/rewind` pour annuler les dernières actions → reformuler le prompt avec plus de contraintes
3. **3ème incident** : Annuler avec `git stash` ou `git checkout -- <fichier>`, nouvelle session avec un scope réduit (une seule fonction, pas toute la page)

**Pattern de recovery complet :**
```bash
# 1. Vérifier l'état actuel
git status
git diff --stat

# 2. Si les modifications sont mauvaises → annuler
git stash push -m "failed-attempt-T10-$(date +%H%M)"

# 3. Nouvelle session avec scope réduit
# Dans le prompt : "Corriger UNIQUEMENT la fonction formatSentimentLabel() dans Explorateur.tsx.
# Ne toucher à aucun autre fichier."

# 4. Si stash à récupérer partiellement
git stash show -p | head -50  # Voir ce qui était fait
git checkout stash -- frontend/client/src/lib/utils.ts  # Récupérer 1 fichier du stash
```

---

## 6. Vérification croisée — L'agent review l'autre

### 6.1 Pattern de review (fin de chaque phase)

**Après Phase 1 (J3) : Claude Code review le frontend**

```
PROMPT DE REVIEW — Claude Code review Codex :

Tu es un développeur backend senior qui review le code frontend de RamyPulse.
Branche à reviewer : agent/codex-frontend (diff vs expo/main-dev)

Exécuter : git diff expo/main-dev..agent/codex-frontend -- frontend/client/src/

Vérifier (checklist) :
1. Les 5 bugs haute sévérité sont corrigés (B1-B5) — tester chacun manuellement
2. Les mutations ont toutes un onError avec toast
3. apiRequest() est utilisé pour le screenshot upload (pas de fetch() brut)
4. Le case 'tres_negatif' est bien dans formatSentimentLabel()
5. "Tout Archiver" utilise Promise.all() ou l'endpoint bulk-status
6. npm run typecheck passe
7. Aucun fichier de api/ n'a été modifié par erreur
8. Aucun console.log() de debug laissé dans le code

Rapport de review : créer docs/review_phase1_backend_on_frontend.md
Format : ✅ OK | ⚠️ Améliorable | ❌ Bloquant
```

**Après Phase 2 (J6) : Codex review le backend**

```
PROMPT DE REVIEW — Codex review Claude Code :

Tu es un développeur frontend senior qui review le code backend de RamyPulse.
Branche à reviewer : agent/claude-backend (diff vs expo/main-dev)

Exécuter : git diff expo/main-dev..agent/claude-backend -- api/

Vérifier :
1. L'endpoint POST /api/recommendations/bulk-status existe et retourne le bon format
2. Il accepte bien {"ids": [...], "status": "archived"|"dismissed"|"active"}
3. Le format de retour correspond au type attendu dans shared/schema.ts
4. pytest tests/test_recommendations_bulk.py : 4/4 passent
5. Le seed data scripts/seed_demo.py crée bien les données avec score=72
6. Aucun endpoint existant cassé (curl les 5 endpoints principaux du dashboard)
7. Pas de print() de debug dans les fichiers Python

Rapport : docs/review_phase2_frontend_on_backend.md
```

---

### 6.2 Tests d'intégration backend ↔ frontend

**Script de test d'intégration** (`scripts/integration_test.sh`) — à créer par Claude Code en J3 :

```bash
#!/bin/bash
# Test d'intégration RamyPulse — vérifie que backend et frontend fonctionnent ensemble
# Usage : ./scripts/integration_test.sh

set -e
BACKEND_URL="http://localhost:8000"
API_KEY="dev"
TENANT_ID="demo-expo-2026"

echo "=== RamyPulse Integration Tests ==="

# 1. Backend health
echo -n "Backend health... "
STATUS=$(curl -s "$BACKEND_URL/api/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])")
[ "$STATUS" = "ok" ] && echo "✅" || (echo "❌ FAIL" && exit 1)

# 2. Dashboard summary (endpoint critique)
echo -n "Dashboard summary... "
SCORE=$(curl -s -H "X-API-Key: $API_KEY" -H "X-Ramy-Client-Id: $TENANT_ID" \
  "$BACKEND_URL/api/dashboard/summary" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('health_score',0))")
[ "$SCORE" -gt 0 ] && echo "✅ Score: $SCORE" || echo "⚠️  Score 0 (seed data manquant?)"

# 3. Alerts endpoint
echo -n "Alerts endpoint... "
COUNT=$(curl -s -H "X-API-Key: $API_KEY" -H "X-Ramy-Client-Id: $TENANT_ID" \
  "$BACKEND_URL/api/alerts?limit=5" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('items',[])))")
echo "✅ $COUNT alertes"

# 4. Bulk-status endpoint (Phase 1)
echo -n "Bulk-status endpoint... "
RESP=$(curl -s -w "%{http_code}" -X POST \
  -H "X-API-Key: $API_KEY" -H "X-Ramy-Client-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"ids":[],"status":"archived"}' \
  "$BACKEND_URL/api/recommendations/bulk-status")
HTTP_CODE="${RESP: -3}"
[ "$HTTP_CODE" = "200" ] && echo "✅" || echo "⚠️  HTTP $HTTP_CODE (endpoint peut-être pas encore créé)"

# 5. Explorer search
echo -n "Explorer search... "
RESULTS=$(curl -s -H "X-API-Key: $API_KEY" -H "X-Ramy-Client-Id: $TENANT_ID" \
  "$BACKEND_URL/api/explorer/search?q=yaghourt&limit=5" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('results',[])))")
echo "✅ $RESULTS résultats"

echo ""
echo "=== Tests d'intégration terminés ==="
```

**Scénarios de test end-to-end (manuels) :**

| # | Scénario | Pages impliquées | Endpoints appelés | Résultat attendu |
|---|----------|-----------------|-------------------|-----------------|
| E2E-1 | Chargement dashboard démo | ProductHome → Dashboard | `/api/dashboard/summary`, `/api/dashboard/alerts-critical` | Score 72 visible, alertes listées |
| E2E-2 | Navigation alerte → action | Dashboard → Alertes | `/api/alerts`, `/api/alerts/{id}/status` | Clic carte alerte → Alertes ; Reconnaître → statut change |
| E2E-3 | Recherche sémantique | Explorateur | `/api/explorer/search?q=goût yaghourt` | Résultats + RAG insight visibles |
| E2E-4 | Export CSV verbatims | Explorateur | `/api/explorer/verbatims?page_size=1000` | Fichier CSV téléchargé |
| E2E-5 | Créer campagne | Campagnes | `POST /api/campaigns` | Toast succès + campagne apparaît dans la liste |
| E2E-6 | Générer recommandations | Recommandations | `POST /api/recommendations/generate` | Nouvelles recommandations générées en < 30s |
| E2E-7 | Archiver en masse | Recommandations | `POST /api/recommendations/bulk-status` | Toast succès, liste vidée |

---

## 7. Anti-patterns et pièges à éviter

Les 10 erreurs les plus courantes avec des équipes d'agents AI sur RamyPulse, tirées des recherches :

| # | Anti-pattern | Symptôme sur RamyPulse | Solution spécifique |
|---|-------------|----------------------|---------------------|
| **AP1** | **Fichiers partagés entre agents en parallèle** | Codex modifie `shared/schema.ts` pendant que Claude Code lit les mêmes types → conflits git au merge | Règle stricte : `shared/schema.ts` gelé en phase parallèle. Seul l'humain peut le modifier lors des points de synchronisation. Source : [research_multi_agent_workflows.md §1] |
| **AP2** | **The kitchen sink session** — trop de tâches dans une seule session | L'agent commence B1, bifurque sur T10, oublie B3, le contexte est pollué de fichiers non liés | Un prompt = une tâche clairement délimitée. `/clear` entre T06 et T07 même si ce sont "des bugs". Source : [research_ai_agent_best_practices.md §1.7] |
| **AP3** | **L'agent écrit ses propres tests** | Les tests Playwright pour demo_flow.spec.ts valident les bugs qu'ils devraient détecter | Les critères de succès sont spécifiés dans le prompt par l'humain (avec les assertions exactes). L'agent implémente pour FAIRE PASSER ces tests. Source : [research_multi_agent_workflows.md §3] |
| **AP4** | **Confiance aveugle dans le code généré** | Codex génère export CSV mais n'échappe pas les virgules dans les valeurs → fichier malformé | Tester MANUELLEMENT chaque feature dans le navigateur avant de merger. "Trust but verify" avec les critères du prompt. Source : [research_ai_agent_best_practices.md §1.7 — trust-then-verify gap] |
| **AP5** | **CLAUDE.md / AGENTS.md trop longs** | L'agent ignore la règle "ne pas modifier frontend/shared/schema.ts" car elle est noyée à la ligne 87 | CLAUDE.md et AGENTS.md dans ce plan sont conçus pour être courts (~60-80 lignes). La règle critique (ne pas toucher à la zone de l'autre agent) est en section visible "Ce que tu NE dois PAS faire". Source : [research_ai_agent_best_practices.md §1.1] |
| **AP6** | **Merge sans tests d'intégration** | Claude Code crée bulk-status endpoint ; Codex l'utilise ; mais le format de réponse ne correspond pas → bug silencieux en prod | Point de synchronisation J3 inclut `scripts/integration_test.sh` qui vérifie le contrat bout-en-bout avant le merge. |
| **AP7** | **Spawner des agents sur des tâches trop granulaires** | 36 tâches = 36 sessions d'agents = coût × 36 et contexte de démarrage × 36 | Regrouper les tâches connexes dans un seul prompt (ex : B1+B4+B2+B3+B5 = PROMPT-P1-02). Source : [research_ai_agent_best_practices.md §1.8 — Calibrer l'effort à la complexité] |
| **AP8** | **Branches trop longues** | La branche `agent/codex-frontend` accumule 20 jours de commits → merge conflict massif avec `expo/main-dev` | Branches courtes (< 3 jours). Merge forcé à chaque fin de phase (J1, J3, J6, J8). Rebase si > 5 jours sans merge. Source : [research_multi_agent_workflows.md §1 — Feature Branch per Agent] |
| **AP9** | **Vibe coding sur AdminSourcesOps.tsx** | L'agent "découpe" le composant mais déplace juste les fonctions sans extraire les queries → composant toujours couplé, 0 gain de maintenabilité | PROMPT-P3-01 spécifie la structure EXACTE des 4 sous-composants avec la règle "chaque vue garde ses propres hooks". L'agent suit un plan, pas une intention floue. |
| **AP10** | **Seed data insuffisant pour la démo** | Dashboard score = 0, liste alertes vide, recommandations vides → jury pas impressionné | T32 est une tâche P0 lancée le J1 par Claude Code, avec spécification exacte (200 verbatims, 72/100, 3 recommandations). Tester le seed via `scripts/integration_test.sh` avant J9. Source : [feuille_de_route_expo.md §4 — Risque 5] |

---

## 8. Checklist de lancement

20 points à vérifier AVANT de lancer les agents le Jour 1 :

| # | Point | Vérification | Bloque si non fait |
|---|-------|--------------|--------------------|
| 1 | **Git worktrees créés** | `git worktree list` retourne 3 entrées | Oui — agents ne peuvent pas travailler |
| 2 | **Branches dédiées existantes** | `git branch -a` montre `agent/claude-backend` et `agent/codex-frontend` | Oui |
| 3 | **CLAUDE.md en place** | `cat ../ramypulse-worktrees/backend/CLAUDE.md` affiche le contenu de ce plan §2.2 | Oui — agent backend sans instructions |
| 4 | **AGENTS.md en place** | `cat ../ramypulse-worktrees/frontend/AGENTS.md` affiche le contenu de ce plan §2.2 | Oui — agent frontend sans instructions |
| 5 | **.env copié dans chaque worktree** | `ls ../ramypulse-worktrees/backend/.env` et `ls ../ramypulse-worktrees/frontend/.env` | Non (fonctionnel en mode dégradé) |
| 6 | **Backend démarre sans erreur** | `uvicorn api.main:app --port 8000 &` puis `curl http://localhost:8000/api/health` → `{"status":"ok"}` | Oui — bloquerait T03 et toute la Phase 1 |
| 7 | **Frontend démarre sans erreur** | `cd frontend && npm install && npm run dev &` puis ouvrir http://localhost:5173 | Oui |
| 8 | **npm run typecheck passe (ou erreurs documentées)** | `cd frontend && npm run typecheck > /tmp/ts_baseline.txt 2>&1` | Non (erreurs préexistantes connues = baseline) |
| 9 | **pytest résultat baseline documenté** | `pytest tests/ -v > /tmp/pytest_baseline.txt 2>&1` → créer `docs/baseline_test_results.md` | Non (utile pour tracker les régressions) |
| 10 | **Merge discovery-brain effectué** | `git log --oneline | head -5` montre le commit de merge | Oui — discovery brain inaccessible sinon |
| 11 | **Contrats shared/schema.ts gelés** | Les agents ont la règle "ne pas modifier" dans leurs configs | Oui — risque de conflits critiques |
| 12 | **Pre-commit hooks activés** | `ls ../ramypulse-worktrees/backend/.git/hooks/pre-commit` et frontend — et exécutables (`chmod +x`) | Non (recommandé mais pas bloquant) |
| 13 | **Seed data tenant demo-expo-2026** | `python scripts/seed_demo.py --tenant demo-expo-2026 --reset` puis `curl .../api/dashboard/summary?client_id=demo-expo-2026` | Non (peut être fait en J1) |
| 14 | **Worktree backend = seul dans api/** | Vérifier qu'aucun fichier de `frontend/client/src/` n'est modifié dans le worktree backend | Oui |
| 15 | **Worktree frontend = seul dans frontend/client/src/** | Vérifier qu'aucun fichier de `api/` n'est modifié dans le worktree frontend | Oui |
| 16 | **scripts/integration_test.sh créé** | `ls scripts/integration_test.sh` | Non (crée en J3 par Claude Code) |
| 17 | **Port 8000 libre** | `lsof -i :8000` ne retourne rien | Oui — conflit de port bloquerait les tests |
| 18 | **Port 5173 libre** | `lsof -i :5173` ne retourne rien | Oui |
| 19 | **Budget tokens / crédits vérifiés** | Vérifier solde Anthropic + OpenAI (~10$ nécessaires) | Oui — agents s'arrêtent si quota épuisé |
| 20 | **Plan multi-agent imprimé / accessible** | `cat /home/user/workspace/plan_multi_agent_ramypulse.md` affiche ce document | Non (recommandé pour référence humaine pendant les syncs) |

---

## Références documentaires

Les sources primaires de ce plan :

- [Anthropic — Best Practices for Claude Code](https://www.anthropic.com/engineering/claude-code-best-practices) (2026-04-03) — §2.2 CLAUDE.md, §7 AP2/AP5
- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) (2024-12-19) — §1.3 principes
- [Anthropic — Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (2025-06-13) — §1.1, §7 AP7/AP8
- [Agentic Coding Handbook — TDD](https://tweag.github.io/agentic-coding-handbook/WORKFLOW_TDD/) — §1.2, §7 AP3
- [Evil Martians — API contracts frontend survival guide](https://evilmartians.com/chronicles/api-contracts-and-everything-i-wish-i-knew-a-frontend-survival-guide) — §1.2, §2.3
- [GitHub Blog — Multi-agent workflows often fail](https://github.blog/ai-and-ml/generative-ai/multi-agent-workflows-often-fail-heres-how-to-engineer-ones-that-dont/) — §2.3
- [Parallel AI Coding with Git Worktrees — Agent Interviews](https://docs.agentinterviews.com/blog/parallel-ai-coding-with-gitworktrees/) — §2.1
- [Spec Kitty 0.11.0 — Robert Douglass](https://www.linkedin.com/pulse/spec-kitty-0110-parallel-ai-agent-development-git-robert-douglass-s1hke) — §1.1, §2.1
- `audit_backend.md` — 51 endpoints FastAPI, 33 tables SQLite, statut fonctionnel
- `audit_frontend.md` — 10 pages React, 20 boutons morts, 34 bugs, stack technique
- `contrats_pages.md` — Contrats page-par-page avec critères d'acceptation
- `feuille_de_route_expo.md` — 36 tâches priorisées, phases P0-P4, risques
- `synthese_croisee.md` — Matrice couverture backend/frontend, endpoints orphelins, score maturité 72/100

---

*Plan généré le 2026-04-11 — Version définitive — 1 050 lignes*
