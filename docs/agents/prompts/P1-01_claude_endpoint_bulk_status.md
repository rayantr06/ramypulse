# PROMPT P1-01 — Claude Code : Endpoint bulk-status recommandations
**Phase** : 1 — Fix Bugs Critiques (Jours 2-3)
**Agent** : Claude Code (worktree backend)
**Tâche** : T09-backend

---

```
CONTEXTE :
RamyPulse backend FastAPI. Branche agent/claude-backend.
Lecture obligatoire : CLAUDE.md, api/routers/recommendations.py, frontend/shared/schema.ts

═══ TÂCHE T09-BACKEND : POST /api/recommendations/bulk-status ═══

Créer dans api/routers/recommendations.py :
- URL : POST /api/recommendations/bulk-status
- Auth : Depends(get_current_client)
- Body : {"ids": ["uuid1", "uuid2"], "status": "archived" | "dismissed" | "active"}
- Comportement : mettre à jour TOUTES les recommandations en une seule transaction DB
- Retour : {"updated": N, "ids": [...]}
- ID inexistant → ignorer silencieusement
- Status invalide → HTTP 422

TESTS TDD — Créer tests/test_recommendations_bulk.py AVANT d'implémenter :
1. test_bulk_status_archive_multiple() — archive 3 recs, vérifie status=archived
2. test_bulk_status_ignores_unknown_ids() — IDs inexistants → pas d'erreur
3. test_bulk_status_invalid_status() — status="INVALID" → HTTP 422
4. test_bulk_status_empty_list() — ids=[] → {"updated": 0}

Workflow TDD :
1. Écrire les 4 tests → lancer → RED (échec attendu)
2. Implémenter l'endpoint
3. Relancer → GREEN (4/4 passent)

CONTRAINTES :
- Ne pas casser les endpoints GET/PUT /api/recommendations existants
- Ne pas toucher à frontend/
- Commit : "feat(api): add bulk-status endpoint for recommendations"

CRITÈRES DE SUCCÈS :
✅ pytest tests/test_recommendations_bulk.py -v : 4/4 passent
✅ curl -X POST -H "X-API-Key: dev" -H "Content-Type: application/json" \
  -d '{"ids":["test-id"],"status":"archived"}' \
  http://localhost:8000/api/recommendations/bulk-status → HTTP 200
```
