# PROMPT P1-02 — Codex : Fix 5 bugs haute sévérité
**Phase** : 1 — Fix Bugs Critiques (Jours 2-3)
**Agent** : Codex CLI (worktree frontend)
**Tâches** : T05, T06, T07, T08, T09-frontend

---

```
CONTEXTE :
RamyPulse frontend React, TypeScript strict. Branche agent/codex-frontend.
Lecture obligatoire : AGENTS.md

FICHIERS À LIRE AVANT de modifier quoi que ce soit :
1. frontend/client/src/lib/queryClient.ts (apiRequest, patterns mutation)
2. frontend/client/src/lib/apiMappings.ts
3. frontend/client/src/pages/Dashboard.tsx
4. frontend/client/src/pages/Campagnes.tsx
5. frontend/client/src/components/admin/AdminSourcesOps.tsx
6. frontend/client/src/pages/Explorateur.tsx
7. frontend/client/src/pages/Recommandations.tsx

═══ BUG B1 — Dashboard.tsx (priorité absolue) ═══
Trouver le bouton {action.ctaLabel} sans onClick.
Fix : onClick={() => navigate('/recommandations')}
Hook : const [, navigate] = useLocation()  (Wouter)
Aussi : cartes alertes avec cursor-pointer sans handler → onClick={() => navigate('/alertes')}

═══ BUG B4 — Campagnes.tsx ═══
Trouver useMutation de création campagne SANS onError.
Ajouter : onError: (error: Error) => { toast({ title: "Erreur création", description: error.message, variant: "destructive" }) }

═══ BUG B2 — AdminSourcesOps.tsx ═══
Chercher : fetch('/api/social-metrics/posts/
Remplacer par : apiRequest('/api/social-metrics/posts/${postId}/metrics/screenshot', { method: 'POST', body: formData })
apiRequest() injecte automatiquement X-API-Key et X-Ramy-Client-Id.

═══ BUG B3 — Explorateur.tsx ═══
Trouver formatSentimentLabel().
Ajouter : case 'tres_negatif': return 'Très Négatif'
Couleur associée : text-red-700 ou bg-red-900/30

═══ BUG B5 — Recommandations.tsx ═══
Trouver "Tout Archiver" avec forEach + mutate().
Remplacer par :
  const handleArchiveAll = async () => {
    const ids = recommendations.map(r => r.id);
    await apiRequest('/api/recommendations/bulk-status', {
      method: 'POST',
      body: JSON.stringify({ ids, status: 'archived' })
    });
    queryClient.invalidateQueries({ queryKey: ['/api/recommendations'] });
  }
Si endpoint bulk pas encore disponible → fallback : Promise.all(ids.map(id => mutateAsync(id))) puis un seul invalidateQueries

CONTRAINTES :
- npm run check (typecheck) doit passer après CHAQUE bug corrigé
- Ne pas modifier frontend/shared/schema.ts
- Un commit par bug : "fix(B1): connect VOIR DETAILS CTA to recommendations"

CRITÈRES DE SUCCÈS :
✅ B1 : click "VOIR DETAILS" → navigue vers /recommandations
✅ B4 : formulaire campagne invalide → toast rouge
✅ B2 : upload screenshot → X-API-Key dans les headers
✅ B3 : verbatims tres_negatif → "Très Négatif" en rouge
✅ B5 : "Tout Archiver" → une seule requête (ou N + 1 seul invalidateQueries)
✅ npm run check : 0 erreur
```
