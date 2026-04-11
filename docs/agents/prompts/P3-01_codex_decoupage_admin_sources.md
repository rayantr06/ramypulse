# PROMPT P3-01 — Codex : Découpage AdminSourcesOps.tsx
**Phase** : 3 — Polish (Jours 7-8)
**Agent** : Codex CLI (worktree frontend)
**Tâche** : T28

---

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
AdminSourcesOps.tsx = 1441 lignes monolithiques. Le découper en 4 sous-composants.
Lecture obligatoire : AGENTS.md, frontend/client/src/components/admin/AdminSourcesOps.tsx

═══ STRUCTURE CIBLE ═══

frontend/client/src/components/admin/
├── AdminSourcesOps.tsx          # Orchestrateur (< 80 lignes — tabs + routing)
├── AdminSourcesView.tsx         # Sources (sync, health, snapshots)
├── AdminCredentialsView.tsx     # Credentials (liste, création, désactivation)
├── AdminCampaignOpsView.tsx     # Campaign Ops (posts, screenshots, revenue)
└── AdminSchedulerView.tsx       # Scheduler (tick, résultat)

═══ RÈGLES D'EXTRACTION ═══

1. Commencer par AdminSchedulerView (la plus simple)
2. npm run check après CHAQUE extraction
3. Chaque sous-vue garde ses propres useQuery/useMutation
4. AdminSourcesOps.tsx = tabs + imports uniquement
5. AUCUN état partagé via props — chaque vue est autonome
6. Queries partagées : dupliquer plutôt que lifter
7. Créer AdminSourcesOps_backup.tsx avant de commencer

CONTRAINTES :
- Zéro changement fonctionnel — découpage pur
- Si une extraction cause une régression → revenir à backup
- npm run check doit passer après chaque étape
- Commit : "refactor(admin): split AdminSourcesOps into 4 sub-views"

CRITÈRES DE SUCCÈS :
✅ AdminSourcesOps.tsx < 100 lignes
✅ 4 sous-composants fonctionnels
✅ npm run check : 0 erreur
✅ Test manuel : toutes les sous-vues admin fonctionnent
```
