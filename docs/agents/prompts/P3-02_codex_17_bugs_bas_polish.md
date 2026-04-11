# PROMPT P3-02 — Codex : 17 bugs bas + polish
**Phase** : 3 — Polish (Jours 7-8)
**Agent** : Codex CLI (worktree frontend)
**Tâche** : T31

---

```
CONTEXTE :
RamyPulse frontend. Branche agent/codex-frontend.

═══ 17 BUGS BAS ═══

L1  — Dashboard.tsx : "2024" hardcodé → {new Date().getFullYear()}
L2  — Dashboard.tsx : "Base sur" → "Basé sur"
L3  — Alertes.tsx : "Ecarter" → "Écarter" ; "Reconnaitre" → "Reconnaître"
L4  — Alertes.tsx : MOYENNE → bg-amber-500/20 ; BASSE → bg-slate-500/20
L5  — Alertes.tsx : Cercle avatar → initiales source (fb→FB, yt→YT, gm→GM)
L6  — Campagnes.tsx : Avatars CDN → composant AvatarInitials(name) SVG
L7  — Campagnes.tsx : Avatar top performeur hardcodé → AvatarInitials
L8  — Campagnes.tsx : isOpen initial → false (formulaire fermé par défaut)
L9  — Campagnes.tsx : Validation Zod → budget > 0, endDate > startDate
L10 — Explorateur.tsx : 'n/a' → '—' (tiret cadratin)
L11 — not-found.tsx : Traduire FR : "Page introuvable" + "Cette page n'existe pas."
L12 — Recommandations.tsx : <Link><a> imbriqués → <Link className="..."> directement
L13 — WatchOnboarding.tsx : Langues hardcodées → champ select optionnel (défaut ["fr","ar"])
L14 — Sidebar.tsx : "Ammar, Brand Manager" → {tenantId || 'Démo'}
L15 — Créer lib/avatars.ts :
      export function generateInitialsSVG(name: string): string
      - 2 premières lettres capitalisées
      - Background HSL déterministe depuis hash du nom
      - SVG inline (pas d'image externe)
L16 — Admin sous-composants : htmlFor + <label> sur tous les <input>
L17 — AdminSourcesOps.tsx : Ré-inclure TikTok dans PLATFORM_OPTIONS

CONTRAINTES :
- npm run check doit passer
- Commit : "fix(polish): fix 17 low-severity bugs"

CRITÈRES DE SUCCÈS :
✅ Copyright = 2026 (année courante)
✅ Accents corrects partout (Écarter, Reconnaître, Basé)
✅ Page 404 en français
✅ Formulaire Campagnes fermé par défaut
✅ Aucun avatar CDN externe
✅ npm run check : 0 erreur
```
