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
