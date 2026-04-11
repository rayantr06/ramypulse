# Documentation Agents AI — RamyPulse Expo

Configuration et prompts pour le développement multi-agent (Claude Code + Codex CLI).

## Fichiers de configuration

| Fichier | Agent | Placer dans |
|---------|-------|-------------|
| [CLAUDE.md](./CLAUDE.md) | Claude Code | Racine du worktree backend |
| [AGENTS.md](./AGENTS.md) | Codex CLI | Racine du worktree frontend |

## Prompts par phase

| Phase | Prompt | Agent | Tâches | Jour |
|-------|--------|-------|--------|------|
| **P0 — Stabilisation** | [P0-01](./prompts/P0-01_claude_stabiliser_backend_seed.md) | Claude Code | T03, T32 | J1 |
| | [P0-02](./prompts/P0-02_codex_setup_frontend_inventaire.md) | Codex | Setup, inventaire | J1 |
| **P1 — Bugs critiques** | [P1-01](./prompts/P1-01_claude_endpoint_bulk_status.md) | Claude Code | T09-backend | J2 |
| | [P1-02](./prompts/P1-02_codex_fix_5_bugs_critiques.md) | Codex | T05-T09 | J2-J3 |
| | [P1-03](./prompts/P1-03_codex_20_boutons_morts.md) | Codex | T10 | J3 |
| **P2 — Features** | [P2-01](./prompts/P2-01_codex_export_csv_onerror.md) | Codex | T11-T13 | J4-J5 |
| | [P2-02](./prompts/P2-02_codex_12_bugs_moyens.md) | Codex | T17-T27 | J5-J6 |
| **P3 — Polish** | [P3-01](./prompts/P3-01_codex_decoupage_admin_sources.md) | Codex | T28 | J7 |
| | [P3-02](./prompts/P3-02_codex_17_bugs_bas_polish.md) | Codex | T31 | J8 |
| **P4 — Tests E2E** | [P4-01](./prompts/P4-01_codex_tests_e2e_demo.md) | Codex | T34 | J9 |

## Workflow

```
J1  → P0-01 (Claude) + P0-02 (Codex) en parallèle → SYNC J1
J2  → P1-01 (Claude) + P1-02 (Codex) en parallèle
J3  → P1-03 (Codex) → SYNC J3 : MERGE backend + frontend
J4  → P2-01 (Codex)
J5  → P2-02 (Codex)
J6  → SYNC J6 : MERGE frontend
J7  → P3-01 (Codex) + Google Stitch redesign (humain)
J8  → P3-02 (Codex) → SYNC J8 : MERGE
J9  → P4-01 (Codex)
J10 → MERGE FINAL → tag v1.0-expo
```

## Setup worktrees (Windows — PowerShell)

> **Prérequis** : le repo root `G:\ramypulse` est sur `main` et ne doit PAS être basculé.
> Les branches `origin/agent/claude-backend` et `origin/agent/codex-frontend` existent
> déjà sur GitHub avec un commit chacune. On crée des worktrees qui trackent ces branches.

```powershell
# Depuis G:\ramypulse (repo root sur main — NE PAS changer de branche ici)

# 1. Récupérer les branches distantes
git fetch origin

# 2. Créer les worktrees avec branche locale trackée sur la distante
#    --track -b crée une branche locale qui suit origin/* (pas de detached HEAD)
git worktree add --track -b agent/claude-backend .worktrees\agent-backend origin/agent/claude-backend
git worktree add --track -b agent/codex-frontend .worktrees\agent-frontend origin/agent/codex-frontend

# 3. Copier les configs agents depuis docs/agents/
#    (les fichiers sont sur expo/main-dev, pas main — on les récupère via git show)
git show origin/expo/main-dev:docs/agents/CLAUDE.md > .worktrees\agent-backend\CLAUDE.md
git show origin/expo/main-dev:docs/agents/AGENTS.md > .worktrees\agent-frontend\AGENTS.md

# 4. Copier le .env dans les worktrees
Copy-Item .env .worktrees\agent-backend\.env -ErrorAction SilentlyContinue
Copy-Item .env .worktrees\agent-frontend\.env -ErrorAction SilentlyContinue

# 5. Vérification
git worktree list
# Attendu (parmi les 18+ existants) :
# G:/ramypulse/.worktrees/agent-backend   99023f2 [agent/claude-backend]
# G:/ramypulse/.worktrees/agent-frontend  a26c0a2 [agent/codex-frontend]
```

### Créer un worktree pour expo/main-dev (accès aux docs)

```powershell
# Si tu veux accéder aux fichiers de docs/agents/ localement sans toucher main :
git worktree add .worktrees\expo-main-dev origin/expo/main-dev
# Les 13 fichiers de docs/agents/ seront dans :
# G:\ramypulse\.worktrees\expo-main-dev\docs\agents\
```

## Lancer les agents

### Claude Code (backend)

```powershell
cd G:\ramypulse\.worktrees\agent-backend

# Lancer Claude Code
claude

# Copier-coller le prompt P0-01 (depuis docs/agents/prompts/)
```

### Codex CLI (frontend)

```powershell
cd G:\ramypulse\.worktrees\agent-frontend

# Lancer Codex
codex --model o4-mini

# Copier-coller le prompt P0-02
```

## Références

- [Plan multi-agent complet](../plan_multi_agent_ramypulse.md) — 1404 lignes, document maître
- [Feuille de route expo](../feuille_de_route_expo.md) — 36 tâches, 4 phases
- [Contrats pages](../contrats_pages.md) — 14 contrats page-par-page
- [Synthèse croisée](../synthese_croisee.md) — Score maturité 72/100
