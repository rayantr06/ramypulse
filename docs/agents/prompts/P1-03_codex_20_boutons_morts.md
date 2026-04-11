# PROMPT P1-03 — Codex : Connecter/supprimer 20 boutons morts
**Phase** : 1 — Fix Bugs Critiques (Jours 2-3)
**Agent** : Codex CLI (worktree frontend)
**Tâche** : T10

---

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
Lecture obligatoire : AGENTS.md

═══ TÂCHE T10 — Tuer ou connecter les 20 boutons morts ═══

CONNECTER (ajouter onClick/navigation) :
1. Dashboard "VOIR DETAILS" → navigate('/recommandations') [déjà fait en B1, vérifier]
2. Dashboard carte alerte → navigate('/alertes')
3. Dashboard carte action → navigate('/recommandations')
4. Explorateur "Filtrer" → ouvrir un Popover (Shadcn/ui) avec filtres sentiment + wilaya
5. Watchlists "Voir les détails analytiques" → navigate('/explorateur?watchlist=' + watchlist.id)
6. AppShell "notifications" → toast("Aucune nouvelle notification")
7. AppShell "sensors" → navigate('/admin-sources')

DÉSACTIVER avec tooltip "Bientôt disponible" (cursor-not-allowed) :
8. Explorateur "Exporter" → badge disabled grisé
9. Campagnes "EXPORTER DATA" → badge disabled grisé
10. AdminSources "Pipelines" nav → title="Bientôt disponible" + pointer-events: none
11. AdminSources "Logs" nav → idem
12. AdminSources "New Pipeline" → disabled
13. AdminSources nav items (Connectors, Health, Validation, Archive) → Badge "Bientôt"

SUPPRIMER (retirer l'élément du DOM) :
14. AdminSources icône "notifications" header
15. AdminSources icône "settings" header
16. AdminSources "Support" sidebar
17. AdminSources "Documentation" sidebar
18. AdminSources "Voir tout l'historique"
19. AppShell "language" icône
20. AppShell "grid_view" icône

CONTRAINTES :
- npm run check (typecheck) doit passer
- Ne pas casser les boutons FONCTIONNELS existants
- Tooltip : utiliser le composant Tooltip de Shadcn/ui
- Commit : "fix(buttons): connect/remove 20 dead buttons"

CRITÈRES DE SUCCÈS :
✅ Aucun bouton cliquable ne fait "rien"
✅ npm run check : 0 erreur
✅ Navigation Dashboard → Alertes → Recommandations fonctionne
```
