# PROMPT P2-01 — Codex : Export CSV + onError global
**Phase** : 2 — Features (Jours 4-6)
**Agent** : Codex CLI (worktree frontend)
**Tâches** : T11, T12, T13

---

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
Lecture obligatoire : AGENTS.md, frontend/client/src/lib/utils.ts, frontend/client/src/lib/queryClient.ts

═══ TÂCHE T11 — onError global sur mutations silencieuses ═══

Exécuter : grep -rn "useMutation" frontend/client/src --include="*.tsx" | grep -v onError
Pour chaque mutation SANS onError, ajouter :
  onError: (error: Error) => {
    toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
  }
Fichiers : Campagnes.tsx, AdminSourcesOps.tsx, Recommandations.tsx

═══ TÂCHE T12 — Export CSV verbatims (Explorateur.tsx) ═══

1. Créer dans frontend/client/src/lib/utils.ts :
   export function convertToCSV(items: Record<string, unknown>[]): string
   // Extraire les headers du premier élément
   // Générer les lignes CSV avec échappement des virgules et guillemets

   export function downloadBlob(content: string, filename: string, mimeType: string): void
   // Blob → URL.createObjectURL → click → revokeObjectURL

2. Dans Explorateur.tsx, connecter le bouton "Exporter" :
   - GET /api/explorer/verbatims?page_size=1000
   - Colonnes : source, sentiment, content, wilaya, date, aspect
   - Nom fichier : verbatims_YYYY-MM-DD.csv
   - Toast "Export téléchargé (N verbatims)"

═══ TÂCHE T13 — Export CSV campagnes (Campagnes.tsx) ═══

Connecter "EXPORTER DATA" :
- GET /api/campaigns
- Colonnes : name, type, platform, influencer, budget, status, startDate, endDate
- Nom fichier : campagnes_YYYY-MM-DD.csv

CONTRAINTES :
- Pas de dépendance externe pour le CSV (pur JS)
- npm run check doit passer
- Commit : "feat(export): add CSV export for verbatims and campaigns"

CRITÈRES DE SUCCÈS :
✅ "Exporter" dans Explorateur → fichier .csv téléchargé
✅ "EXPORTER DATA" dans Campagnes → fichier .csv téléchargé
✅ Mutations sans onError → toast d'erreur visible
```
