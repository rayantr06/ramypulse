# PROMPT P0-02 — Codex : Setup frontend + inventaire boutons morts
**Phase** : 0 — Stabilisation (Jour 1)
**Agent** : Codex CLI (worktree frontend)
**Tâches** : Setup, inventaire

---

```
CONTEXTE :
Tu travailles sur RamyPulse, une SPA React de veille marketing algérienne.
Frontend : React 18 + Vite 7 + TypeScript strict + Shadcn/ui + Tailwind CSS 3.4.
Worktree : agent/codex-frontend
Ton fichier de config : AGENTS.md (lis-le en premier)

IMPORTANT : Tu es peut-être sur Windows (PowerShell) ou Linux/macOS.
Détecte ton environnement avant d'exécuter des commandes shell.

FICHIERS À LIRE EN PRIORITÉ :
1. AGENTS.md
2. frontend/package.json (scripts disponibles)
3. frontend/client/src/App.tsx (routing)
4. frontend/shared/schema.ts (contrats — LECTURE SEULE)

═══ TÂCHE SETUP ═══

1. cd frontend
2. npm install
3. npm run check   (script "check" = tsc — typecheck strict)
   Sauvegarder la sortie dans docs/frontend_baseline.md
4. Documenter les erreurs TypeScript préexistantes dans docs/frontend_baseline.md
   (ces erreurs sont connues, ne pas les corriger maintenant sauf si elles bloquent)

═══ TÂCHE : Inventorier les boutons morts ═══

Lire ces fichiers et noter les boutons SANS onClick ni href :
- frontend/client/src/pages/Dashboard.tsx
- frontend/client/src/pages/Explorateur.tsx
- frontend/client/src/pages/Campagnes.tsx
- frontend/client/src/pages/Watchlists.tsx
- frontend/client/src/components/AppShell.tsx
- frontend/client/src/components/admin/AdminSourcesOps.tsx

Pour chaque bouton mort, ajouter un commentaire dans le fichier :
// TODO-DEAD-BUTTON: [description] → [action attendue]

NE PAS IMPLÉMENTER LES FIXES — uniquement les TODOs.

CONTRAINTES :
- Ne pas toucher à api/
- Ne pas modifier frontend/shared/schema.ts
- Committer sur agent/codex-frontend uniquement
- Message : "chore(audit): add TODO markers for dead buttons Phase 0"

CRITÈRES DE SUCCÈS :
✅ npm install réussit
✅ docs/frontend_baseline.md créé
✅ TODOs ajoutés dans tous les fichiers avec boutons morts
```
