# RamyPulse — Frontend React

## Contexte du projet
RamyPulse est une application de veille marketing pour marques algériennes.
Frontend : React 18 + Vite 7 + TypeScript strict + Shadcn/ui + Tailwind CSS 3.4 + TanStack Query 5.
Design system : Obsidian (dark mode, fond #0A0A14, accent #ffb693, typographie Manrope/Inter).
Tu travailles dans le worktree `agent/codex-frontend` — ne touche JAMAIS aux fichiers de `api/`.

## Repository Layout
- Pages : `frontend/client/src/pages/` (9 pages fonctionnelles)
- Composants partagés : `frontend/client/src/components/`
- Logique métier : `frontend/client/src/lib/` (apiMappings.ts, queryClient.ts, etc.)
- Hooks : `frontend/client/src/hooks/`
- Contrats d'interface : `frontend/shared/schema.ts` — LECTURE SEULE
- Tests E2E : `frontend/tests/` (Playwright)

## Build, Test, and Lint Commands
```bash
cd frontend
npm install
npm run dev              # Dev server port 5173 (proxy /api → localhost:8000)
npm run build            # Build production dans dist/public/
npm run check            # TypeScript strict (tsc) — DOIT passer avant tout commit
npm run lint             # ESLint
npx playwright test      # Tests E2E
npx playwright test --ui # Mode interactif
```

## Engineering Conventions
- TypeScript strict mode — JAMAIS de `any` sans commentaire explicatif
- Composants fonctionnels React uniquement (pas de class components)
- TanStack Query pour tous les appels API — pas de `fetch()` brut sauf cas exceptionnel documenté
- Pour les mutations : TOUJOURS inclure `onError` avec un toast `variant: "destructive"`
- Pour les mutations batch : utiliser `Promise.all()` avec `mutateAsync()`, jamais `forEach + mutate()`
- Navigation : Wouter (`useLocation()`, `<Link>`) — pas `window.location`
- Formulaires : React Hook Form + Zod validation
- Client HTTP : utiliser `apiRequest()` depuis `lib/queryClient.ts` — injecte automatiquement X-API-Key et X-Ramy-Client-Id

## Conventions API (IMPORTANT)
- L'endpoint backend retourne snake_case, `apiMappings.ts` convertit en camelCase
- Ne PAS appeler directement l'API avec fetch() brut — utiliser `useQuery`/`useMutation` via `queryClient.ts`
- QueryKey format : `['/api/endpoint', { clientId, ...params }]`
- Le `clientId` vient de `useTenantContext()` — TOUJOURS inclure dans queryKey pour isolation multi-tenant

## Design tokens (à respecter)
- Fond : `#0A0A14` (var: --background)
- Accent primaire : `#ffb693` (var: --primary)
- Texte principal : `hsl(0 0% 95%)` (var: --foreground)
- Danger : `hsl(0 84% 60%)` (var: --destructive)
- Succès : `hsl(142 71% 45%)` (var: --success / text-green-400)
- Typographie titres : Manrope ; corps : Inter

## Constraints (Do Not)
- Ne jamais modifier `api/` (zone Claude Code)
- Ne jamais modifier `frontend/shared/schema.ts` sans validation humaine
- Ne jamais committer sur `expo/main-dev` ou `main` directement
- Ne jamais utiliser des images depuis des CDN Google externes (remplacer par avatars SVG initiales)
- Ne jamais hardcoder une couleur en dehors des tokens CSS définis dans `index.css`

## Definition of Done (par tâche)
1. `npm run check` passe sans erreur (tsc)
2. `npm run lint` passe sans warning
3. Le bouton/feature fonctionne manuellement dans le navigateur (port 5173)
4. Aucune régression sur les autres pages (tester la navigation complète)
5. PR description avec : ce qui a changé + pourquoi + screenshots si UI
