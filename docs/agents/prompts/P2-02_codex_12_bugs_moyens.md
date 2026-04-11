# PROMPT P2-02 — Codex : 12 bugs moyens
**Phase** : 2 — Features (Jours 4-6)
**Agent** : Codex CLI (worktree frontend)
**Tâches** : T17-T27

---

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.
Lecture obligatoire : AGENTS.md

═══ 12 BUGS MOYENS — liste exhaustive ═══

M1  — Dashboard.tsx : Renommer "VENTES PAR PRODUIT" → "PERFORMANCE PRODUIT — Score Sentiment"
M2  — Campagnes.tsx : Importer SiTiktok (react-icons/si) + FaMapMarkerAlt (react-icons/fa) pour icônes manquantes
M3  — Watchlists.tsx : Remplacer buildOwners() hack → avatar générique coloré + tooltip "Owners non disponibles"
M4  — Watchlists.tsx : Delta NSS → delta > 0 ? 'text-green-400' : 'text-red-400'
M5  — Recommandations.tsx : "Volume (m³)" → "Volume mentions"
M6  — Recommandations.tsx : Inverser value/label dans carte "Dernière run"
M7  — Recommandations.tsx : Dates ISO → format(new Date(iso), 'dd/MM/yyyy HH:mm', {locale: fr})  (date-fns)
M8  — Alertes.tsx : disabled={isPending} + spinner sur boutons d'action
M9  — Alertes.tsx : Masquer boutons selon alert.status (résolu → pas "Résoudre")
M10 — Alertes.tsx : Bouton "Charger plus" → limit state +50 (useState<number>(50))
M11 — Explorateur.tsx : Chips source → paramètre channel : selectedChannels.join(',')
M12 — AdminSourcesOps.tsx : DELETE → AlertDialog Shadcn/ui "Confirmer la suppression ?"

Pour M7 : import { format } from 'date-fns'; import { fr } from 'date-fns/locale/fr'

CONTRAINTES :
- npm run check doit passer
- Un commit par page : "fix(watchlists): fix delta NSS color and owners avatar"

CRITÈRES DE SUCCÈS :
✅ Titre Dashboard corrigé
✅ Delta NSS vert/rouge correct
✅ Dates formatées dd/MM/yyyy HH:mm
✅ Boutons alertes disabled pendant mutation
✅ Filtre multi-source transmet channel param
✅ npm run check : 0 erreur
```
