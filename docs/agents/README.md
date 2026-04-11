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

## Setup worktrees

```bash
# Depuis la racine du repo (branche expo/main-dev)
git branch agent/claude-backend
git branch agent/codex-frontend
git worktree add .worktrees/agent-backend agent/claude-backend
git worktree add .worktrees/agent-frontend agent/codex-frontend

# Copier les configs
cp docs/agents/CLAUDE.md .worktrees/agent-backend/CLAUDE.md
cp docs/agents/AGENTS.md .worktrees/agent-frontend/AGENTS.md
cp .env .worktrees/agent-backend/.env
cp .env .worktrees/agent-frontend/.env
```

## Références

- [Plan multi-agent complet](../../plan_multi_agent_ramypulse.md) — 1404 lignes, document maître
- [Feuille de route expo](../../feuille_de_route_expo.md) — 36 tâches, 4 phases
- [Contrats pages](../../contrats_pages.md) — 14 contrats page-par-page
- [Synthèse croisée](../../synthese_croisee.md) — Score maturité 72/100
