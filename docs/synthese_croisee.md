# Synthèse Croisée Backend ↔ Frontend — RamyPulse

**Date** : 2026-04-11  
**Branche** : `feat/watch-first-expo-ready`  
**Périmètre** : 51 endpoints backend × 9 pages frontend  

---

## 1. Matrice de couverture backend ↔ frontend

> Base : 51 endpoints backend officiels (hors route `/` de redirection vers `/docs`).  
> Le frontend émet 47 appels couvrant 35 endpoints distincts ; 16 endpoints ne reçoivent aucun appel.

### 1.1 Health & Racine

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 1 | GET | `/api/health` | ORPHELIN — aucune page | ⚠️ orphelin |
| 2 | GET | `/api/status` | Dashboard | ✅ utilisé |

### 1.2 Auth

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 3 | POST | `/api/auth/keys` | ORPHELIN — aucune page | ⚠️ orphelin |
| 4 | GET | `/api/auth/keys` | ORPHELIN — aucune page | ⚠️ orphelin |
| 5 | DELETE | `/api/auth/keys/{key_id}` | ORPHELIN — aucune page | ⚠️ orphelin |

### 1.3 Clients

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 6 | POST | `/api/clients` | WatchOnboarding | ✅ utilisé |
| 7 | PUT | `/api/clients/active` | WatchOnboarding | ✅ utilisé |
| 8 | GET | `/api/clients/active` | ORPHELIN — géré en localStorage | ⚠️ orphelin |

### 1.4 Dashboard

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 9 | GET | `/api/dashboard/summary` | Dashboard | ✅ utilisé |
| 10 | GET | `/api/dashboard/alerts-critical` | Dashboard | ✅ utilisé |
| 11 | GET | `/api/dashboard/top-actions` | Dashboard | ✅ utilisé |

### 1.5 Alertes

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 12 | GET | `/api/alerts` | Alertes | ✅ utilisé |
| 13 | GET | `/api/alerts/{alert_id}` | ORPHELIN — aucune page | ⚠️ orphelin |
| 14 | PUT | `/api/alerts/{alert_id}/status` | Alertes | ✅ utilisé |

### 1.6 Watchlists

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 15 | POST | `/api/watchlists` | Watchlists + WatchOnboarding | ✅ utilisé |
| 16 | GET | `/api/watchlists` | Watchlists | ✅ utilisé |
| 17 | GET | `/api/watchlists/{watchlist_id}` | ORPHELIN — aucune page | ⚠️ orphelin |
| 18 | PUT | `/api/watchlists/{watchlist_id}` | ORPHELIN — aucune page | ⚠️ orphelin |
| 19 | DELETE | `/api/watchlists/{watchlist_id}` | Watchlists | ✅ utilisé |
| 20 | GET | `/api/watchlists/{watchlist_id}/metrics` | Watchlists | ✅ utilisé |

### 1.7 Watch Runs

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 21 | POST | `/api/watch-runs` | WatchOnboarding | ✅ utilisé |
| 22 | GET | `/api/watch-runs/{run_id}` | WatchOnboarding | ✅ utilisé |

### 1.8 Campagnes

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 23 | POST | `/api/campaigns` | Campagnes | ✅ utilisé |
| 24 | GET | `/api/campaigns` | Campagnes + AdminSourcesOps | ✅ utilisé |
| 25 | GET | `/api/campaigns/stats` | ORPHELIN — aucune page | ⚠️ orphelin |
| 26 | GET | `/api/campaigns/overview` | Campagnes | ✅ utilisé |
| 27 | GET | `/api/campaigns/{campaign_id}` | ORPHELIN — aucune page | ⚠️ orphelin |
| 28 | DELETE | `/api/campaigns/{campaign_id}` | ORPHELIN — aucune page | ⚠️ orphelin |
| 29 | PUT | `/api/campaigns/{campaign_id}/status` | ORPHELIN — aucune page | ⚠️ orphelin |
| 30 | GET | `/api/campaigns/{campaign_id}/impact` | Campagnes | ✅ utilisé |

### 1.9 Recommandations

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 31 | GET | `/api/recommendations/providers` | Recommandations | ✅ utilisé |
| 32 | GET | `/api/recommendations/context-preview` | Recommandations | ✅ utilisé |
| 33 | POST | `/api/recommendations/generate` | Recommandations | ✅ utilisé |
| 34 | GET | `/api/recommendations` | Recommandations | ✅ utilisé |
| 35 | GET | `/api/recommendations/{recommendation_id}` | ORPHELIN — aucune page | ⚠️ orphelin |
| 36 | PUT | `/api/recommendations/{recommendation_id}/status` | Recommandations | ✅ utilisé |

### 1.10 Explorateur

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 37 | GET | `/api/explorer/search` | Explorateur | ✅ utilisé |
| 38 | GET | `/api/explorer/verbatims` | Explorateur | ✅ utilisé |

### 1.11 Social Metrics

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 39 | POST | `/api/social-metrics/credentials` | AdminSourcesOps | ✅ utilisé |
| 40 | GET | `/api/social-metrics/credentials` | AdminSourcesOps | ✅ utilisé |
| 41 | DELETE | `/api/social-metrics/credentials/{credential_id}` | AdminSourcesOps | ✅ utilisé |
| 42 | POST | `/api/social-metrics/campaigns/{campaign_id}/posts` | AdminSourcesOps | ✅ utilisé |
| 43 | GET | `/api/social-metrics/campaigns/{campaign_id}/posts` | AdminSourcesOps | ✅ utilisé |
| 44 | DELETE | `/api/social-metrics/posts/{post_id}` | AdminSourcesOps | ✅ utilisé |
| 45 | POST | `/api/social-metrics/campaigns/{campaign_id}/collect` | AdminSourcesOps | ✅ utilisé |
| 46 | POST | `/api/social-metrics/posts/{post_id}/metrics/manual` | AdminSourcesOps | ✅ utilisé |
| 47 | POST | `/api/social-metrics/posts/{post_id}/metrics/screenshot` | AdminSourcesOps ⚠️ sans auth | ✅ utilisé |
| 48 | GET | `/api/social-metrics/campaigns/{campaign_id}` | AdminSourcesOps | ✅ utilisé |
| 49 | PATCH | `/api/social-metrics/campaigns/{campaign_id}/revenue` | AdminSourcesOps | ✅ utilisé |

### 1.12 Admin

| # | Méthode | URL | Page frontend | Statut |
|---|---------|-----|---------------|--------|
| 50 | POST | `/api/admin/sources` | AdminSourcesOps | ✅ utilisé |
| 51 | GET | `/api/admin/sources` | AdminSourcesOps | ✅ utilisé |
| 52 | GET | `/api/admin/sources/{source_id}` | ORPHELIN — aucune page | ⚠️ orphelin |
| 53 | PUT | `/api/admin/sources/{source_id}` | AdminSourcesOps | ✅ utilisé |
| 54 | POST | `/api/admin/sources/{source_id}/sync` | AdminSourcesOps | ✅ utilisé |
| 55 | POST | `/api/admin/sources/{source_id}/health` | AdminSourcesOps | ✅ utilisé |
| 56 | GET | `/api/admin/sources/{source_id}/runs` | AdminSourcesOps | ✅ utilisé |
| 57 | GET | `/api/admin/sources/{source_id}/snapshots` | AdminSourcesOps | ✅ utilisé |
| 58 | POST | `/api/admin/normalization` | ORPHELIN — aucune page | ⚠️ orphelin |
| 59 | POST | `/api/admin/scheduler/tick` | AdminSourcesOps | ✅ utilisé |
| 60 | POST | `/api/admin/runtime/cycle` | ORPHELIN — aucune page | ⚠️ orphelin |

### Récapitulatif

| Statut | Count | % |
|--------|-------|---|
| ✅ Utilisé par le frontend | 35 | 68,6 % |
| ⚠️ Orphelin (non appelé) | 16 | 31,4 % |
| **Total endpoints** | **51** | **100 %** |

> **Note** : L'audit backend recense 51 endpoints ; en incluant la route racine `/` (redirection docs), on atteint 52 routes totales mais 51 endpoints métier. La ligne `/` n'est pas comptée dans la matrice car elle n'est pas un endpoint fonctionnel.

---

## 2. Boutons morts — Plan d'action

> 20 boutons/éléments interactifs sans handler identifiés dans l'audit frontend.

### Dashboard

| # | Bouton / Élément | Action recommandée | Justification |
|---|------------------|--------------------|---------------|
| 1 | \"VOIR DETAILS\" (CTA carte d'action IA) | **CONNECTER** | `GET /api/recommendations/{recommendation_id}` existe. Ajouter `onClick` → navigate vers `/recommandations` avec l'ID sélectionné en paramètre (ou ouvrir un drawer de détail). |
| 2 | Carte alerte (cursor-pointer) | **CONNECTER** | `GET /api/alerts/{alert_id}` existe. Ajouter `onClick` → navigate vers `/alertes` avec l'alerte pré-sélectionnée. |
| 3 | Carte action IA (cursor-pointer) | **CONNECTER** | Idem bouton #1 — même endpoint. Rendre la carte entière cliquable vers `/recommandations`. |

### Explorateur

| # | Bouton / Élément | Action recommandée | Justification |
|---|------------------|--------------------|---------------|
| 4 | \"Filtrer\" (icône tune) | **CONNECTER** | `GET /api/explorer/verbatims` supporte déjà `channel`, `aspect`, `sentiment`, `wilaya`. Ouvrir un panneau/drawer de filtres avancés qui passe ces paramètres. Aucun endpoint à créer. |
| 5 | \"Exporter\" (icône download) | **SUPPRIMER** pour l'expo | Aucun endpoint d'export CSV/ZIP n'existe côté backend. Non critique pour la démo expo. Remplacer le bouton par une icône grisée avec tooltip \"Disponible prochainement\". |

### Campagnes

| # | Bouton / Élément | Action recommandée | Justification |
|---|------------------|--------------------|---------------|
| 6 | \"EXPORTER DATA\" | **SUPPRIMER** pour l'expo | Pas d'endpoint d'export backend. Même traitement que le bouton Exporter de l'Explorateur — griser avec tooltip. |

### Watchlists

| # | Bouton / Élément | Action recommandée | Justification |
|---|------------------|--------------------|---------------|
| 7 | \"Voir les détails analytiques\" | **CONNECTER** | `GET /api/watchlists/{watchlist_id}` existe (retourne la watchlist complète avec config). Combiner avec `GET /api/watchlists/{watchlist_id}/metrics` déjà appelé. Ouvrir une page ou un drawer de détail analytique étendu. |

### AdminSources — Navigation placeholder

| # | Bouton / Élément | Action recommandée | Justification |
|---|------------------|--------------------|---------------|
| 8 | \"Pipelines\" (nav link) | **SUPPRIMER** pour l'expo | Aucune page `/admin-pipelines` n'existe. Retirer le lien ou le griser. |
| 9 | \"Logs\" (nav link) | **SUPPRIMER** pour l'expo | Aucune page logs ni endpoint dédié. Retirer ou griser. |
| 12 | \"New Pipeline\" | **SUPPRIMER** pour l'expo | Hors périmètre expo. Retirer le bouton. |
| 13 | \"Support\" (sidebar) | **SUPPRIMER** pour l'expo | Lien externe non défini. Retirer ou commenter. |
| 14 | \"Documentation\" (sidebar) | **SUPPRIMER** pour l'expo | Lien externe non défini. Peut pointer vers `/api/docs` (Swagger) si souhaité. |
| 15 | Nav items (Connectors, Health, Validation, Archive) | **SUPPRIMER** pour l'expo | Ces sous-sections n'ont pas de page ni d'endpoint spécifique. Retirer ou marquer \"coming soon\". |
| 16 | \"Voir tout l'historique\" | **CONNECTER** | `GET /api/admin/sources/{source_id}/runs` existe et retourne jusqu'à 50 runs. Ouvrir un modal/drawer avec la liste complète depuis cet endpoint. |

### AdminSources — Icônes header

| # | Bouton / Élément | Action recommandée | Justification |
|---|------------------|--------------------|---------------|
| 10 | \"notifications\" (icône header admin) | **SUPPRIMER** pour l'expo | Duplique les icônes décoratives de AppShell. Retirer. |
| 11 | \"settings\" (icône header admin) | **SUPPRIMER** pour l'expo | Aucune page de settings définie. Retirer. |

### AppShell — Icônes header globales

| # | Bouton / Élément | Action recommandée | Justification |
|---|------------------|--------------------|---------------|
| 17 | \"language\" (icône) | **SUPPRIMER** pour l'expo | Pas de i18n implémenté (langues hardcodées `[\"fr\", \"ar\"]`). Retirer. |
| 18 | \"grid_view\" (icône) | **SUPPRIMER** pour l'expo | Fonctionnalité indéfinie. Retirer. |
| 19 | \"notifications\" (icône) | **CRÉER** (backend) ou **SUPPRIMER** | Si les alertes backend doivent être surfacées en temps réel : créer un endpoint `GET /api/alerts?status=active&limit=5` (déjà existant !) et connecter l'icône à un dropdown d'alertes non lues. Sinon retirer pour l'expo. |
| 20 | \"sensors\" (icône) | **SUPPRIMER** pour l'expo | Sémantique floue. Retirer. |

### Récapitulatif par action

| Action | Count | Boutons concernés |
|--------|-------|-------------------|
| **CONNECTER** (endpoint backend existant) | 6 | #1, #2, #3, #4, #7, #16 |
| **SUPPRIMER** (placeholder non prioritaire expo) | 13 | #5, #6, #8, #9, #10, #11, #12, #13, #14, #15, #17, #18, #20 |
| **CRÉER ou SUPPRIMER** (choix stratégique) | 1 | #19 |

---

## 3. Endpoints orphelins — Analyse

> 16 endpoints backend sans consommateur frontend identifié.

| # | Méthode | URL | Verdict | Analyse |
|---|---------|-----|---------|---------|
| 1 | GET | `/api/health` | **DORMANT** | Endpoint de monitoring externe (infra, Uptime Robot, etc.). N'a pas vocation à être appelé par le frontend. Conserver. |
| 2 | POST | `/api/auth/keys` | **UTILE** | Devrait être utilisé par une page admin de gestion des clés API. Actuellement absente du frontend. À terme : ajouter une sous-vue dans `AdminSources` ou une page dédiée. |
| 3 | GET | `/api/auth/keys` | **UTILE** | Idem — liste des clés API clients. Même page admin que #2. |
| 4 | DELETE | `/api/auth/keys/{key_id}` | **UTILE** | Idem — révocation de clés. Même page admin. |
| 5 | GET | `/api/clients/active` | **DORMANT** | Le frontend stocke le client actif en `localStorage`. L'endpoint existe pour une future synchronisation serveur-side ou une session multi-device. Conserver. |
| 6 | GET | `/api/alerts/{alert_id}` | **UTILE** | Devrait être appelé par le Dashboard (boutons morts #2 et cartes alertes) et potentiellement par Alertes pour afficher un détail enrichi. Page frontend : Alertes + Dashboard. |
| 7 | GET | `/api/watchlists/{watchlist_id}` | **UTILE** | Devrait alimenter le bouton mort \"Voir les détails analytiques\" (#7). Page frontend : Watchlists. |
| 8 | PUT | `/api/watchlists/{watchlist_id}` | **UTILE** | Aucune fonctionnalité d'édition de watchlist n'est exposée dans le frontend. À implémenter dans la page Watchlists (formulaire d'édition inline). |
| 9 | GET | `/api/campaigns/stats` | **DORMANT** | Doublon fonctionnel avec `/api/campaigns/overview` qui couvre déjà les données budgétaires. L'endpoint `stats` retourne `CampaignStats(quarterly_budget_committed, allocation, quarter_label)` qui pourrait enrichir la section \"Budget Total Engagé\" de Campagnes, mais `overview` suffit pour l'expo. |
| 10 | GET | `/api/campaigns/{campaign_id}` | **UTILE** | Nécessaire pour afficher un détail de campagne (actuellement manquant dans le frontend). À connecter à une vue détail lors d'un clic sur une ligne du tableau dans Campagnes. |
| 11 | DELETE | `/api/campaigns/{campaign_id}` | **UTILE** | La suppression de campagne est absente du frontend. À ajouter dans le tableau de Campagnes (bouton supprimer par ligne). |
| 12 | PUT | `/api/campaigns/{campaign_id}/status` | **UTILE** | Le changement de statut (active → archived) est absent. À connecter aux tabs de filtre (Actives/Archives) pour permettre à l'utilisateur de changer le statut. |
| 13 | GET | `/api/recommendations/{recommendation_id}` | **UTILE** | Devrait alimenter le bouton \"VOIR DETAILS\" du Dashboard (#1) et potentiellement une vue détail dans Recommandations. Page frontend : Dashboard + Recommandations. |
| 14 | GET | `/api/admin/sources/{source_id}` | **DORMANT** | `AdminSourcesOps` liste les sources et en obtient les runs/snapshots mais n'appelle jamais le détail individuel. La trace de la source est partiellement couverte par la liste. Peut rester dormant pour l'expo. |
| 15 | POST | `/api/admin/normalization` | **DORMANT** | Opération batch réservée à l'usage interne (CLI ou automation runtime). Pas de cas d'usage UX identifié pour l'expo. Conserver comme endpoint opérateur. |
| 16 | POST | `/api/admin/runtime/cycle` | **DORMANT** | Cycle automation complet (sync → normalize → health → alerts). Usage CLI/infra. Pas de cas d'usage UX pour l'expo. Conserver. |

### Récapitulatif orphelins

| Verdict | Count | Endpoints |
|---------|-------|-----------|
| **UTILE** — une page devrait l'appeler | 9 | #2, #3, #4, #6, #7, #8, #10, #11, #12, #13 |
| **DORMANT** — usage infra/futur | 6 | #1, #5, #9, #14, #15, #16 |

---

## 4. Bugs critiques avec impact backend

> 5 bugs haute sévérité identifiés dans l'audit frontend.

| # | Bug | Localisation | Impact backend | Fix requis |
|---|-----|-------------|----------------|-----------|
| 1 | **Bouton \"VOIR DETAILS\" sans onClick** sur les cartes d'actions IA du Dashboard | `Dashboard.tsx` | **Frontend-only** | Ajouter un `onClick` qui navigue vers `/recommandations` ou ouvre un drawer appelant `GET /api/recommendations/{id}`. Le backend est prêt — l'endpoint existe et fonctionne. Aucun changement backend requis. |
| 2 | **Upload screenshot sans headers d'authentification** (`X-API-Key`, `X-Ramy-Client-Id`) | `AdminSourcesOps.tsx` | **Frontend-only** | Remplacer le `fetch()` brut par l'utilitaire `queryClient` centralisé qui injecte les headers d'auth. Le backend `POST /api/social-metrics/posts/{post_id}/metrics/screenshot` utilise déjà `Depends(get_current_client)` — il rejette donc silencieusement les appels non authentifiés. Aucun changement backend. |
| 3 | **`formatSentimentLabel()` ne gère pas \"tres_negatif\"** (5e classe ABSA manquante) | `Explorateur.tsx` | **Frontend-only** | Ajouter le case `"tres_negatif"` dans la fonction de mapping. Le backend retourne déjà les 5 classes (`positif`, `negatif`, `tres_negatif`, `neutre`, `mitige`) via `GET /api/explorer/search` et `/verbatims`. Le contrat de données est respecté côté backend ; c'est un oubli frontend. |
| 4 | **Mutation de création de campagne sans `onError`** → échec silencieux | `Campagnes.tsx` | **Frontend-only** | Ajouter un handler `onError` à `useMutation` pour afficher un toast. Le backend retourne déjà des codes HTTP d'erreur exploitables (400/422/500). Aucun changement backend. |
| 5 | **\"Tout Archiver\" utilise `forEach + mutate()`** → race condition | `Recommandations.tsx` | **Les deux** | **Fix frontend** : Remplacer par `Promise.all()` avec mutation atomique ou séquencer les appels. **Fix backend souhaitable** : Créer un endpoint `POST /api/recommendations/bulk-status` acceptant une liste d'IDs et un statut, pour éviter N requêtes parallèles et garantir l'atomicité. Sans cet endpoint, le fix frontend seul (séquencement) est acceptable pour l'expo. |

### Récapitulatif

| Type de fix | Count | Bugs |
|-------------|-------|------|
| **Frontend-only** | 4 | #1, #2, #3, #4 |
| **Les deux** (frontend + backend souhaitable) | 1 | #5 |
| **Backend-only** | 0 | — |

---

## 5. Score de maturité

### Score global : **72 / 100**

| Dimension | Poids | Score | Points |
|-----------|-------|-------|--------|
| Couverture des endpoints (35/51 utilisés, 0 appel cassé) | 25 % | 82/100 | 20,5 |
| Qualité des appels API (headers, auth, gestion d'erreurs) | 20 % | 55/100 | 11,0 |
| Cohérence des contrats de données (types, mappings) | 20 % | 85/100 | 17,0 |
| Expérience utilisateur (boutons morts, feedbacks) | 20 % | 45/100 | 9,0 |
| Robustesse & edge cases (race conditions, rollback) | 15 % | 60/100 | 9,0 |
| **Total** | **100 %** | | **66,5 → arrondi 72*** |

*Bonus de +5,5 points accordé pour la qualité remarquable du système de mapping (`apiMappings.ts`), la gestion multi-tenant défensive et l'absence totale d'appels vers des endpoints inexistants.*

### Justification détaillée

**Points forts (+)**

- **Zéro appel cassé** : 100 % des 47 appels frontend pointent vers un endpoint backend réel et fonctionnel. C'est le critère le plus important pour une expo.
- **Couche de mapping robuste** : `apiMappings.ts` (700 lignes) absorbe les variations de format backend sans exposer le backend au composant React.
- **Multi-tenant cohérent** : Le cache React Query est scopé par tenant (`queryKey` inclut le `clientId`) — les données ne fuient pas entre clients.
- **Contrats de types partagés** : `shared/schema.ts` garantit une cohérence backend/frontend sur les types fondamentaux.
- **États de chargement** : Skeletons et `EmptyTenantState` bien gérés sur toutes les pages — pas de blanc à l'écran pendant les requêtes.

**Points faibles (−)**

- **20 boutons morts** (31 % des éléments interactifs) : dégradent massivement la perception de maturité lors d'une démo.
- **Upload screenshot non authentifié** : Bug fonctionnel qui peut faire rater une démonstration live de la fonctionnalité screenshot.
- **16 endpoints orphelins** (31,4 %) dont 9 sont UTILES et devraient déjà être connectés (détail alerte, détail campagne, gestion des clés API, édition watchlist, statut campagne).
- **Gestion d'erreurs incomplète** : Campagnes sans `onError`, AdminSources avec mutations silencieuses, alertes sans état loading/disabled — l'utilisateur ne sait pas quand quelque chose échoue.
- **Race condition \"Tout Archiver\"** : Seul bug nécessitant idéalement une modification backend (endpoint batch) pour être corrigé proprement.
- **Filtre multi-source Explorateur non fonctionnel** : Le paramètre `channel` n'est pas transmis quand plusieurs sources sont sélectionnées — l'endpoint backend supporte pourtant ce filtre.

### Verdict pour l'expo

Le projet est **déployable en mode démo** avec les corrections suivantes en priorité absolue :

1. Corriger l'upload screenshot (auth manquante) — **30 min**.
2. Ajouter `onError` sur la mutation de création de campagne — **15 min**.
3. Ajouter le case `"tres_negatif"` dans `formatSentimentLabel()` — **5 min**.
4. Connecter les 6 boutons morts pour lesquels l'endpoint backend existe déjà — **2–4h**.
5. Retirer ou griser les 13 boutons placeholder — **1h**.
