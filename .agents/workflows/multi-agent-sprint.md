---
description: Workflow multi-agent (Antigravity + Codex + Claude Code) pour implémenter le PRD v6 sprint par sprint
---

# Workflow Multi-Agent — RamyPulse PRD v6

## Équipe

| Agent | Rôle | Forces | Convention branche |
|-------|------|--------|-------------------|
| **Antigravity** | Tech Lead + Intégrateur | Architecture, merge, tests d'intégration, UI Streamlit, coordination | `antigravity/sprint-XXX` |
| **Codex** | Backend Engineer | Modules Python isolés, TDD, logique pure, tâches autonomes | `codex/sprint-XXX` |
| **Claude Code** (superpowers) | Senior Engineer | Algorithmes complexes, ML, debugging, refactoring délicat | `claude/sprint-XXX` |

## Convention Git

### Branches
```
main                          ← toujours stable, tests verts
├── phase0/integration        ← branche d'intégration Phase 0
│   ├── codex/p0-faiss-fix    ← Sprint 0b — Codex
│   ├── claude/p0-rag-guards  ← Sprint 0c — Claude Code
│   └── claude/p0-eval-framework ← Sprint 0d — Claude Code
├── phase1/integration        ← branche d'intégration Phase 1
│   ├── codex/p1-sqlite-registry ← Sprint 1a — Codex
│   ├── codex/p1-catalog      ← Sprint 1b — Codex
│   ├── claude/p1-entity-resolver ← Sprint 1c — Claude Code
│   ├── codex/p1-import-engine ← Sprint 1d — Codex
│   └── antigravity/p1-dashboard ← Sprint 1e — Antigravity
└── phase2/integration
    ├── claude/p2-watchlist-alerts ← Sprint 2a — Claude Code
    ├── claude/p2-reco-engine  ← Sprint 2b — Claude Code
    ├── antigravity/p2-watch-center ← Sprint 2c — Antigravity
    └── antigravity/p2-reco-desk ← Sprint 2d — Antigravity
```

### Nommage des commits
```
[agent] sprint-XXX: description courte

Exemples:
[codex] p0-faiss: ajout incrémental sans rebuild HNSW
[claude] p0-rag: parsing JSON robuste + retry backoff
[antigravity] p1-dashboard: filtres produit/wilaya/canal
```

## Protocole de travail

### 1. Avant chaque sprint

// turbo
```bash
git checkout main
git pull origin main
python -m pytest tests/ --tb=short -q
```

Vérifier que la baseline est stable (275+ passed).

### 2. Créer la branche de sprint

```bash
git checkout -b [agent]/[phase]-[module]
```

### 3. Pendant le sprint

Chaque agent suit le cycle TDD :
1. Écrire les tests dans `tests/test_[module].py`
2. Vérifier qu'ils échouent (red)
3. Implémenter dans `core/[package]/[module].py`
4. Vérifier qu'ils passent (green)
5. Refactor si nécessaire
6. Vérifier que TOUS les tests passent (les 275+ anciens + les nouveaux)

### 4. Commit + Push

```bash
git add .
git commit -m "[agent] sprint-XXX: description"
git push origin [branch-name]
```

### 5. Merge vers integration

// turbo
```bash
git checkout phase[N]/integration
git merge [agent]/[sprint-branch] --no-ff
python -m pytest tests/ --tb=short -q
```

Si tests verts → OK. Si conflit ou test cassé → l'agent corrige avant merge.

### 6. Merge integration → main

Quand TOUS les sprints d'une phase sont mergés dans `phase[N]/integration` et que les tests passent :

```bash
git checkout main
git merge phase[N]/integration --no-ff -m "Phase [N] complete: [description]"
python -m pytest tests/ --tb=short -q
git tag v0.[N+1].0
git push origin main --tags
```

## Règles strictes

1. **Jamais de commit sur main** — toujours via merge depuis integration
2. **Jamais de merge sans tests verts** — les 275+ tests existants + les nouveaux
3. **Chaque agent lit le PRD v6** (section pertinente) avant de coder
4. **Chaque agent respecte CLAUDE.md** — docstrings français, logging, config.py, 5 classes
5. **Les agents ne modifient PAS les fichiers des autres** sauf coordination explicite
6. **Un sprint = un module = une branche = un merge**

## Template de prompt par agent

### Prompt Codex (tâches isolées, TDD)

```
Tu es sur le projet RamyPulse (Python 3.10+, Streamlit, ABSA sentiment analysis).

RÈGLES :
- Lis CLAUDE.md pour les conventions
- TDD : tests d'abord dans tests/test_[module].py
- Docstrings en français
- logging, jamais print()
- Config dans core/config.py
- NE MODIFIE PAS les fichiers existants sauf [liste]

TÂCHE : [description du sprint]

SPÉCIFICATION PRD :
[copier-coller la section du PRD v6]

SCHÉMA SQL (si applicable) :
[copier-coller le DDL]

CRITÈRE DE SORTIE :
- [ ] Tests écrits et passent
- [ ] Module implémenté
- [ ] pytest tests/ -q → tous verts (anciens + nouveaux)
- [ ] Commit sur la branche [branch-name]
```

### Prompt Claude Code superpowers (tâches complexes)

```
Tu es Senior Engineer sur RamyPulse. Tu as accès au terminal.

CONTEXTE :
- Repo : g:\ramypulse (ou /path)
- Branche de travail : claude/[sprint]
- Baseline : 275+ tests verts sur main
- PRD de référence : docs/RamyPulse_PRD_Post_Wave4_v6.md §[section]

ÉTAPES :
1. git checkout -b claude/[sprint] depuis main
2. Lis CLAUDE.md et la section PRD pertinente
3. Écris les tests d'abord
4. Implémente
5. Lance pytest tests/ --tb=short -q
6. Si tous verts : commit + push

TÂCHE : [description]

CONTRAINTE : Ne touche PAS aux fichiers :
[liste des fichiers protégés]
```

### Prompt Antigravity (intégration, UI, coordination)

Antigravity (moi) travaille directement dans cette conversation. Pas besoin de prompt externe.
Mon rôle :
- Coordonner les sprints
- Merger les branches
- Implémenter les pages Streamlit (UI)
- Résoudre les conflits de merge
- Valider les critères de sortie de phase
