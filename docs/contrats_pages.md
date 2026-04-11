# Contrats Page-par-Page — RamyPulse

**Date** : 2026-04-11  
**Basé sur** : `audit_backend.md` (51 endpoints, 33 tables SQLite) + `audit_frontend.md` (10 pages, 47 appels API, 20 boutons morts, 34 bugs)  
**Branche de référence** : `feat/watch-first-expo-ready`  
**Usage** : Référence de développement. Chaque page dispose d'un contrat complet : données, actions, bugs à corriger, critères d'acceptation.

---

## Table des matières

1. [ProductHome](#1-producthome--contrat)
2. [WatchOnboarding](#2-watchonboarding--contrat)
3. [Dashboard](#3-dashboard--contrat)
4. [Explorateur](#4-explorateur--contrat)
5. [Campagnes](#5-campagnes--contrat)
6. [Watchlists](#6-watchlists--contrat)
7. [Alertes](#7-alertes--contrat)
8. [Recommandations](#8-recommandations--contrat)
9. [AdminSources](#9-adminsources--contrat)
10. [NotFound](#10-notfound--contrat)
11. [Composants partagés — AppShell](#11-composant-partagé--appshell)
12. [Composants partagés — Sidebar](#12-composant-partagé--sidebar)
13. [Composants partagés — TenantSwitcher](#13-composant-partagé--tenantswitcher)
14. [Composants partagés — EmptyTenantState](#14-composant-partagé--emptytenantstate)

---

---

## 1. ProductHome — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/` |
| Fichier(s) | `client/src/pages/ProductHome.tsx` (10 lignes) |
| Rôle | Point d'entrée de l'application. Redirige conditionnellement : si un `tenantId` est présent dans `localStorage` (`ramypulse.activeTenantId`), affiche `<Dashboard />` ; sinon, affiche `<WatchOnboarding />`. Composant pur — aucun état propre, aucun appel réseau. |

#### Données consommées

Aucun appel API direct. La décision de routage repose entièrement sur la valeur lue depuis `localStorage` via `tenantContext.ts`.

| Endpoint | Méthode | Payload envoyé | Réponse attendue | Fréquence |
|----------|---------|----------------|------------------|-----------|
| — | — | — | — | — |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Aucune action propre | — | — | — | — |

> Toutes les actions sont déléguées aux composants enfants `Dashboard` ou `WatchOnboarding`.

#### Dépendances

- **Composants partagés** : `Dashboard.tsx`, `WatchOnboarding.tsx` (imports conditionnels)
- **Bibliothèques** : `tenantContext.ts` (lecture `localStorage`)
- **Routing** : Wouter 3.3.5 (hash-based)

#### Bugs à corriger

Aucun bug identifié pour ce composant.

#### Critères d'acceptation (Definition of Done)

- [ ] Si `localStorage['ramypulse.activeTenantId']` est défini et non vide, `<Dashboard />` est rendu
- [ ] Si `localStorage['ramypulse.activeTenantId']` est null/undefined/vide, `<WatchOnboarding />` est rendu
- [ ] Aucun flash/clignotement lors du rendu conditionnel (state lu de façon synchrone)
- [ ] La redirection fonctionne après un rafraîchissement de page (F5)
- [ ] Aucun appel réseau parasite au montage du composant

---

---

## 2. WatchOnboarding — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/nouveau-client` (aussi affiché comme fallback sur `#/` quand pas de tenant) |
| Fichier(s) | `client/src/pages/WatchOnboarding.tsx` (42 lignes), `client/src/components/watch/WatchOnboardingWizard.tsx`, `client/src/components/watch/RunProgressPanel.tsx`, `client/src/lib/watchWizard.ts` |
| Rôle | Wizard 2 étapes pour créer un nouveau client (marque/produit) puis définir la première watchlist (URLs/canaux), lancer le watch run initial, et suivre sa progression en temps réel. Point d'entrée obligatoire pour tout nouveau tenant. |

#### Données consommées

| Endpoint | Méthode | Payload envoyé | Réponse attendue (schéma) | Fréquence |
|----------|---------|----------------|---------------------------|-----------|
| `/api/clients` | POST | `{ client_name: string, industry: string }` | `{ client_id, client_name, industry, created_at, updated_at }` | Au clic "Lancer l'analyse" (étape 2) |
| `/api/clients/active` | PUT | `{ client_id: string }` | `{ client_id, client_name, industry, ... }` | Après création client (chaîne) |
| `/api/watchlists` | POST | `{ name: string, description: string, scope_type: string, filters: { seed_urls: string[], channels: string[], languages: ["fr","ar"], keywords: string[] } }` | `{ watchlist_id, status }` | Après activation client (chaîne) |
| `/api/watch-runs` | POST | `{ watchlist_id: string, requested_channels: string[] }` | `WatchRunResponse` (202 Accepted) avec `{ run_id, status: "queued", watchlist_id, ... }` | Après création watchlist (chaîne) |
| `/api/watch-runs/{run_id}` | GET | Aucun (path param) | `{ run_id, status: "queued"\|"collecting"\|"normalizing"\|"indexing"\|"finished"\|"failed", steps: [...], started_at, ended_at }` | Polling toutes les 1 seconde jusqu'à `status === "finished"` ou `"failed"` |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| "Continuer" (étape 1 → 2) | Valide le formulaire étape 1 (nom marque, industrie), passe à l'étape 2 | Aucun | ✅ Fonctionnel | — |
| "Retour" (étape 2 → 1) | Revient à l'étape 1 sans perte de données | Aucun | ✅ Fonctionnel | — |
| "Lancer l'analyse" (soumission finale) | Exécute la chaîne POST clients → PUT active → POST watchlists → POST watch-runs dans l'ordre | `/api/clients` → `/api/clients/active` → `/api/watchlists` → `/api/watch-runs` | ✅ Fonctionnel | Ajouter rollback (voir Bugs) |
| "Explorer un exemple abouti" | Charge le tenant démo (`ramy-demo`) en `localStorage` et redirige vers `#/` | Aucun | ✅ Fonctionnel | — |

#### Dépendances

- **Composants partagés** : Aucun (page autonome, pas d'AppShell)
- **Composants internes** : `WatchOnboardingWizard`, `RunProgressPanel`
- **Bibliothèques** : React Hook Form 7.55, Zod 3.24, TanStack React Query 5.60, Framer Motion 11.13
- **Lib** : `watchWizard.ts` (construction payload), `tenantContext.ts` (écriture `localStorage`)

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | ⚠️ MOYENNE | Pas de rollback si un appel échoue au milieu de la chaîne (ex : client créé, watchlist échoue → client orphelin dans la DB) | Implémenter un try/catch global sur la chaîne. Si échec après `POST /api/clients`, appeler un nettoyage ou stocker l'`client_id` pour permettre une reprise. À défaut, afficher un message clair indiquant l'étape ayant échoué et permettre la reprise. |
| 2 | 🔵 BASSE | Langues `["fr", "ar"]` hardcodées dans `watchWizard.ts` sans possibilité de changement dans l'UI | Ajouter un champ de sélection multi-langues à l'étape 2 du wizard. Valeurs possibles : `fr`, `ar`, `arabizi`. |

#### Critères d'acceptation (Definition of Done)

- [ ] L'étape 1 valide que `client_name` est non vide avant d'autoriser "Continuer"
- [ ] L'étape 2 valide qu'au moins une URL seed ou un canal est sélectionné
- [ ] La chaîne de création s'exécute dans l'ordre séquentiel : POST clients → PUT active → POST watchlists → POST watch-runs
- [ ] En cas d'erreur à n'importe quelle étape, un message d'erreur explicite est affiché (toast ou inline), indiquant quelle étape a échoué
- [ ] `RunProgressPanel` affiche les 4 étapes (collecting → normalizing → indexing → finished) avec états visuels distincts
- [ ] Le polling s'arrête dès que `status === "finished"` ou `"failed"`
- [ ] Quand `status === "finished"`, l'utilisateur est redirigé automatiquement vers `#/` (Dashboard)
- [ ] "Explorer un exemple abouti" charge le tenant `ramy-demo` et affiche le Dashboard sans erreur

---

---

## 3. Dashboard — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/` (rendu par `ProductHome` quand un tenant est actif) |
| Fichier(s) | `client/src/pages/Dashboard.tsx` (513 lignes) |
| Rôle | Tableau de bord principal de l'application. Agrège 6 sections : Score Santé de Marque (jauge NSS circulaire), Alertes Critiques (top 3), Actions Recommandées par l'IA (top 3), Performance Produit (barres sentiment par produit), Distribution Régionale (wilayas), Statut API (footer). C'est la page d'accueil pour tout tenant actif. |

#### Données consommées

| Endpoint | Méthode | Payload envoyé | Réponse attendue (schéma) | Fréquence |
|----------|---------|----------------|---------------------------|-----------|
| `/api/dashboard/summary` | GET | Header `X-API-Key`, `X-Ramy-Client-Id` | `{ health_score: number, nss_progress: { current: number, trend: "up"\|"down"\|"stable", delta: number }, total_mentions: number, regional_distribution: [{ region: string, count: number, pct: number }], product_performance: [{ product: string, score: number }], ai_summary: string }` | Au montage (mount) |
| `/api/dashboard/alerts-critical` | GET | Header `X-API-Key`, `X-Ramy-Client-Id` | `{ alerts: [{ alert_id, severity: "critical"\|"high"\|"medium"\|"low", title, description, created_at }] }` (max 3) | Au montage (mount) |
| `/api/dashboard/top-actions` | GET | Header `X-API-Key`, `X-Ramy-Client-Id` | `{ actions: [{ action_id, priority: string, title, rationale, cta_label, confidence_pct: number }] }` (max 3) | Au montage (mount) |
| `/api/status` | GET | Aucun (endpoint public) | `{ api_status: string, db_status: string, latency_ms: number }` | Au montage (mount) |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Bouton CTA `{action.ctaLabel}` ("VOIR DETAILS") sur chaque carte d'action IA | Naviguer vers la page pertinente (ex : Recommandations, Alertes) ou afficher un détail modal | Aucun | 🔴 BOUTON MORT (onClick absent) | Implémenter la navigation : selon le type d'action, router vers `#/recommandations`, `#/alertes` ou `#/explorateur` |
| Carte alerte (div `cursor-pointer`) | Naviguer vers `#/alertes` avec la sélection de l'alerte correspondante | Aucun | 🔴 CLIC MORT (onClick absent) | Ajouter `onClick` → `navigate('#/alertes')` avec l'`alert_id` en query param ou state |
| Carte action IA (div `cursor-pointer`) | Naviguer vers `#/recommandations` ou afficher détail | Aucun | 🔴 CLIC MORT (onClick absent) | Ajouter `onClick` → `navigate('#/recommandations')` |

#### Dépendances

- **Composants partagés** : `AppShell`, `Sidebar`, `TenantSwitcher`, `EmptyTenantState`
- **Bibliothèques** : Recharts 2.15 (graphiques barres), Framer Motion 11.13 (animations), TanStack React Query 5.60
- **Lib** : `apiMappings.ts` (transformation des réponses API), `queryClient.ts`

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | 🔴 HAUTE | Bouton "VOIR DETAILS" sur chaque carte d'action IA n'a pas de `onClick` | Ajouter handler de navigation vers la page appropriée selon le type d'action |
| 2 | 🔴 HAUTE | Cartes alertes (cursor-pointer) sans `onClick` | Ajouter `onClick={() => navigate('#/alertes')}` avec transmission de l'`alert_id` |
| 3 | 🔴 HAUTE | Cartes actions IA (cursor-pointer) sans `onClick` | Ajouter `onClick={() => navigate('#/recommandations')}` |
| 4 | ⚠️ MOYENNE | Section "Performance Produit" titrée "VENTES PAR PRODUIT" alors que les données représentent des tendances de sentiment (scores NSS) | Renommer en "PERFORMANCE PRODUIT — Score NSS" ou "SENTIMENT PAR PRODUIT" |
| 5 | 🔵 BASSE | Copyright hardcodé à "2024" dans le footer | Remplacer par `new Date().getFullYear()` |
| 6 | 🔵 BASSE | Typo "Base sur" → "Basé sur" dans le résumé IA | Corriger la chaîne de caractères |

#### Critères d'acceptation (Definition of Done)

- [ ] Les 4 endpoints sont appelés au montage et les données s'affichent sans erreur (états loading avec skeleton, puis données réelles)
- [ ] Le clic sur une carte alerte navigue vers `#/alertes`
- [ ] Le clic sur une carte action IA ou son bouton CTA navigue vers la page appropriée
- [ ] La section "Performance Produit" est correctement intitulée (suppression de "VENTES PAR PRODUIT")
- [ ] Si aucune donnée n'est disponible (tenant sans signaux), `EmptyTenantState` est affiché à la place du contenu
- [ ] Le footer affiche le statut API correct (vert/rouge selon `api_status`) et la latence en ms
- [ ] Le copyright affiche l'année en cours

---

---

## 4. Explorateur — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/explorateur` (protégée par `TenantProtectedRoute` — redirige vers `#/nouveau-client` si pas de tenant) |
| Fichier(s) | `client/src/pages/Explorateur.tsx` (631 lignes), `client/src/lib/explorerAiView.ts`, `client/src/lib/pageSearchFilters.ts` |
| Rôle | Moteur de recherche sémantique et navigateur de verbatims. Deux modes : (1) Recherche RAG (FAISS + BM25) avec synthèse IA des résultats et scores de pertinence, (2) Exploration paginée de tous les verbatims du tenant avec filtres par source. |

#### Données consommées

| Endpoint | Méthode | Payload envoyé | Réponse attendue (schéma) | Fréquence |
|----------|---------|----------------|---------------------------|-----------|
| `/api/explorer/search` | GET | Query params : `q=<string>`, `limit=10`, `channel=<string\|undefined>` | `{ query: string, results: [{ verbatim_id, content, source, channel, relevance_score: number, sentiment_label: string, aspect: string, wilaya: string }], total: number }` | Au clic "Explorer" (on-click) |
| `/api/explorer/verbatims` | GET | Query params : `page=<number>`, `page_size=50`, `channel=<string\|undefined>` | `{ results: [{ verbatim_id, text, channel, source_url, published_at, sentiment_label, aspect, wilaya, confidence: number }], total: number, page: number, page_size: number, total_pages: number }` | Au montage (mount) puis à chaque changement de page ou de filtre |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| "Explorer" (bouton recherche) | Lance `GET /api/explorer/search` avec la requête saisie, affiche les résultats RAG avec synthèse IA | `/api/explorer/search` | ✅ Fonctionnel | — |
| Chip source "Facebook" | Toggle filtre source, relance la recherche avec `channel=facebook` | `/api/explorer/search` + `/api/explorer/verbatims` | ✅ Toggle UI fonctionnel — ⚠️ Bug : paramètre `channel` non transmis | Corriger la transmission du paramètre `channel` dans la query string |
| Chip source "Google Maps" | Toggle filtre source, relance avec `channel=google_maps` | idem | ✅ Toggle UI — ⚠️ Même bug | Même fix |
| Chip source "YouTube" | Toggle filtre source, relance avec `channel=youtube` | idem | ✅ Toggle UI — ⚠️ Même bug | Même fix |
| Chip source "Instagram" | Toggle filtre source, relance avec `channel=instagram` | idem | ✅ Toggle UI — ⚠️ Même bug | Même fix |
| Chip source "Import" | Toggle filtre source, relance avec `channel=import` | idem | ✅ Toggle UI — ⚠️ Même bug | Même fix |
| "Filtrer" (icône tune) | Ouvrir un panneau/modal de filtres avancés (aspect, sentiment, wilaya) | `/api/explorer/verbatims` avec params supplémentaires | 🔴 BOUTON MORT (onClick absent) | Implémenter un panneau de filtres avancés utilisant les params `aspect`, `sentiment`, `wilaya` de l'endpoint `/api/explorer/verbatims` |
| "Exporter" (icône download) | Exporter les verbatims filtrés en CSV | Aucun endpoint existant | 🔴 BOUTON MORT (onClick absent) | Option 1 : implémenter export CSV client-side depuis les données chargées. Option 2 : créer un endpoint backend `GET /api/explorer/verbatims/export`. Pour l'expo, option 1 suffira. |
| Boutons pagination ◀/▶ | Navigation entre pages de verbatims | `/api/explorer/verbatims?page=N` | ✅ Fonctionnel | — |

#### Dépendances

- **Composants partagés** : `AppShell`, `Sidebar`, `TenantSwitcher`, `EmptyTenantState`
- **Bibliothèques** : TanStack React Query 5.60, Framer Motion 11.13
- **Lib** : `explorerAiView.ts` (synthèse RAG côté client), `pageSearchFilters.ts` (filtres client-side), `apiMappings.ts`

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | 🔴 HAUTE | `formatSentimentLabel()` ne gère pas la valeur `"tres_negatif"` (5e classe du modèle ABSA). Affiche "Négatif" au lieu de "Très Négatif". | Ajouter le cas `"tres_negatif"` (et `"très_négatif"`) dans le switch/map de `formatSentimentLabel()`. Les 5 classes sont : `très_positif`, `positif`, `neutre`, `négatif`, `très_négatif`. |
| 2 | ⚠️ MOYENNE | Filtre multi-source (chips) n'envoie aucun paramètre `channel` dans la requête API → le filtre est purement visuel, sans effet réel | Lors du toggle d'un chip, construire la valeur `channel` à transmettre en query param. Si plusieurs chips actifs, envisager soit `channel=facebook,youtube` (si le backend supporte), soit des requêtes séparées. Vérifier le comportement du backend pour canaux multiples. |
| 3 | 🔵 BASSE | `"n/a"` affiché littéralement dans les cellules "Aspect" et "Wilaya" quand la valeur est absente | Remplacer par `"—"` (tiret em) ou `<span class="text-muted">Non identifié</span>` |

#### Critères d'acceptation (Definition of Done)

- [ ] La recherche sémantique retourne des résultats avec scores de pertinence et synthèse IA affichés correctement
- [ ] Les 5 classes de sentiment (`très_positif`, `positif`, `neutre`, `négatif`, `très_négatif`) sont toutes affichées avec le bon libellé et la bonne couleur
- [ ] Le filtre par source transmet réellement le paramètre `channel` à l'API et filtre les résultats
- [ ] Les valeurs manquantes (aspect, wilaya) affichent `"—"` et non `"n/a"`
- [ ] La pagination fonctionne (50 verbatims par page, navigation ◀/▶)
- [ ] `EmptyTenantState` s'affiche si le tenant n'a pas de verbatims indexés
- [ ] Les boutons "Filtrer" et "Exporter" ont un comportement implémenté (même minimal pour l'expo)

---

---

## 5. Campagnes — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/campagnes` (protégée par `TenantProtectedRoute`) |
| Fichier(s) | `client/src/pages/Campagnes.tsx` (1000 lignes) |
| Rôle | Module de gestion des campagnes marketing. Permet de créer des campagnes (nom, type, plateforme, budget, dates, mots-clés, influenceur), visualiser l'analyse d'impact NSS (pré/pendant/post campagne), suivre toutes les campagnes dans un tableau filtrable, consulter le top performeur du mois et le budget trimestriel engagé. |

#### Données consommées

| Endpoint | Méthode | Payload envoyé | Réponse attendue (schéma) | Fréquence |
|----------|---------|----------------|---------------------------|-----------|
| `/api/campaigns` | GET | Query params : `status=<string\|undefined>`, `platform=<string\|undefined>` | `[{ campaign_id, name, platform, status: "active"\|"archived"\|"planned", budget_dza: number, start_date, end_date, influencer_name, keywords: string[], created_at }]` | Au montage (mount) |
| `/api/campaigns/overview` | GET | Header `X-Ramy-Client-Id` | `{ top_performer: { campaign_id, name, roi_pct, engagement_rate, signals_count }, budget_summary: { total_budget_dza, quarterly_allocation_dza, quarter_label } }` | Au montage (mount) |
| `/api/campaigns/{campaign_id}/impact` | GET | Path param `campaign_id` | `{ campaign_id, pre_nss: number, active_nss: number, post_nss: number, ai_insight: string, signal_count_pre: number, signal_count_active: number, signal_count_post: number }` | On-click sur une ligne du tableau (sélection campagne) |
| `/api/campaigns` | POST | `{ name: string, campaign_type: string, platform: string, influencer_name: string\|null, budget_dza: number, start_date: string (ISO), end_date: string (ISO), keywords: string[] }` | `{ campaign_id, status: "created" }` | Au clic "Lancer la Campagne" |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| "EXPORTER DATA" | Exporter la liste des campagnes en CSV/XLSX | Aucun endpoint | 🔴 BOUTON MORT (onClick absent) | Implémenter export CSV client-side depuis les données de la requête `GET /api/campaigns` déjà chargée |
| "CREER UNE CAMPAGNE" (en-tête) | Scroll vers le formulaire de création | Aucun | ✅ Fonctionnel | — |
| "Ouvrir le formulaire" | Ouvre/déplie le formulaire de création | Aucun | ✅ Fonctionnel | — |
| Icône expand/collapse | Toggle pliage du formulaire | Aucun | ✅ Fonctionnel | — |
| "Lancer la Campagne" (soumission formulaire) | POST de la nouvelle campagne, invalide le cache React Query, ferme le formulaire | `/api/campaigns` POST | ✅ Fonctionnel — ⚠️ Bug : pas de `onError` | Ajouter `onError` avec toast d'erreur |
| Ligne de tableau (clic) | Sélectionne la campagne, charge l'analyse d'impact via `GET /api/campaigns/{id}/impact` | `/api/campaigns/{id}/impact` | ✅ Fonctionnel | — |
| Tabs filtre "Toutes" | Affiche toutes les campagnes | `/api/campaigns` (sans filtre status) | ✅ Fonctionnel | — |
| Tabs filtre "Actives" | Filtre campagnes `status=active` | `/api/campaigns?status=active` | ✅ Fonctionnel | — |
| Tabs filtre "Archives" | Filtre campagnes `status=archived` | `/api/campaigns?status=archived` | ✅ Fonctionnel | — |
| Boutons pagination ◀/▶ | Navigation entre pages du tableau (4 campagnes/page) | Aucun (pagination client-side) | ✅ Fonctionnel | — |
| Tag mot-clé (×N) — icône ×  | Supprime le mot-clé de la liste dans le formulaire | Aucun | ✅ Fonctionnel | — |

#### Dépendances

- **Composants partagés** : `AppShell`, `Sidebar`, `TenantSwitcher`, `EmptyTenantState`
- **Bibliothèques** : React Hook Form 7.55, Zod 3.24, TanStack React Query 5.60, Recharts 2.15 (barres impact NSS)
- **Lib** : `apiMappings.ts`

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | 🔴 HAUTE | Mutation `POST /api/campaigns` n'a pas de callback `onError` → l'échec est silencieux, aucun feedback utilisateur | Ajouter `onError: (err) => toast({ title: "Erreur", description: "Impossible de créer la campagne", variant: "destructive" })` dans `useMutation` |
| 2 | ⚠️ MOYENNE | Icônes plateforme manquantes pour TikTok et Google Maps (affiche une icône générique) | Ajouter les SVG ou composants icône pour TikTok et Google Maps dans le map des plateformes |
| 3 | 🔵 BASSE | Avatars campagne sont 4 images hébergées sur CDN Google externe, en round-robin | Remplacer par des avatars générés localement (initiales + couleur HSL dérivée du `campaign_id`) |
| 4 | 🔵 BASSE | Avatar du "Top Performeur" hardcodé | Même fix que #3 |
| 5 | 🔵 BASSE | Validation formulaire minimale : seul le champ `name` est vérifié | Ajouter validation Zod pour `budget_dza` (nombre > 0), `start_date` < `end_date`, `platform` non vide |
| 6 | 🔵 BASSE | Formulaire de création est ouvert par défaut au chargement de la page | Fermer par défaut (`isOpen = false`) |

#### Critères d'acceptation (Definition of Done)

- [ ] La liste des campagnes se charge au montage et supporte le filtrage par statut (Toutes/Actives/Archives)
- [ ] La sélection d'une campagne affiche les barres d'impact NSS (pré/pendant/post) et l'insight IA
- [ ] La création d'une campagne affiche un toast de succès/échec selon le résultat de l'API
- [ ] Le formulaire de création est fermé par défaut
- [ ] La validation Zod couvre au minimum : nom non vide, budget > 0, start_date < end_date
- [ ] L'export CSV fonctionne (même minimal) depuis les données déjà chargées
- [ ] Les icônes plateformes s'affichent pour toutes les plateformes supportées (Facebook, Instagram, YouTube, TikTok, Google Maps)

---

---

## 6. Watchlists — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/watchlists` (protégée par `TenantProtectedRoute`) |
| Fichier(s) | `client/src/pages/Watchlists.tsx` (558 lignes) |
| Rôle | Interface de gestion des watchlists. Affiche une grille de cartes (une par watchlist) avec scope, statut actif/inactif, description, avatars des "owners". Permet de créer, désactiver et sélectionner des watchlists. Un panneau de détail s'ouvre à droite lors de la sélection, affichant le score NSS, le volume de mentions, la répartition par aspects et des insights rapides. |

#### Données consommées

| Endpoint | Méthode | Payload envoyé | Réponse attendue (schéma) | Fréquence |
|----------|---------|----------------|---------------------------|-----------|
| `/api/watchlists?is_active=true` | GET | Query param `is_active=true` | `[{ watchlist_id, watchlist_name, description, scope_type, filters: object, is_active: true, created_at }]` | Au montage (mount) et après mutation |
| `/api/watchlists?is_active=false` | GET | Query param `is_active=false` | `[{ watchlist_id, watchlist_name, description, scope_type, filters: object, is_active: false, created_at }]` | Au montage (mount) |
| `/api/watchlists/{watchlist_id}/metrics` | GET | Path param `watchlist_id` | `{ nss_score: number, nss_delta: number, mentions_count: number, aspect_breakdown: [{ aspect: string, count: number, sentiment_avg: number }], quick_insights: string[] }` | On-click sur une carte watchlist (sélection) |
| `/api/watchlists` | POST | `{ name: string, description: string, scope_type: "product"\|"region"\|"channel"\|"cross_dimension", filters: { keywords: string[], channels: string[], min_volume: number, period_days: number } }` | `{ watchlist_id, status: "created" }` | Au clic "Créer" dans le formulaire inline |
| `/api/watchlists/{watchlist_id}` | DELETE | Path param `watchlist_id` | 204 No Content | Au clic icône delete/deactivate |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Tab "Toutes" | Affiche toutes les watchlists (actives + inactives) | Les deux requêtes GET | ✅ Fonctionnel | — |
| Tab "Actives" | Affiche uniquement `is_active=true` | `/api/watchlists?is_active=true` | ✅ Fonctionnel | — |
| Tab "Inactives" | Affiche uniquement `is_active=false` | `/api/watchlists?is_active=false` | ✅ Fonctionnel | — |
| Carte watchlist (clic) | Sélectionne la watchlist, charge ses métriques dans le panneau de droite | `/api/watchlists/{id}/metrics` | ✅ Fonctionnel | — |
| Carte watchlist (2e clic) | Désélectionne, ferme le panneau de droite | Aucun | ✅ Fonctionnel | — |
| "Créer une watchlist" (placeholder) | Ouvre le formulaire de création inline | Aucun | ✅ Fonctionnel | — |
| "Créer" (soumission formulaire) | POST nouvelle watchlist, invalide cache | `/api/watchlists` POST | ✅ Fonctionnel | — |
| "Annuler" | Ferme le formulaire sans soumettre | Aucun | ✅ Fonctionnel | — |
| Icône delete/deactivate | DELETE (soft delete) de la watchlist | `/api/watchlists/{id}` DELETE | ✅ Fonctionnel | Ajouter dialogue de confirmation avant suppression |
| "Voir les détails analytiques" | Devrait ouvrir une vue détail approfondie ou naviguer vers Explorateur filtré | Aucun | 🔴 BOUTON MORT (onClick absent) | Implémenter navigation vers `#/explorateur` avec le contexte de la watchlist en paramètre, ou afficher un panneau de détails étendu |

#### Dépendances

- **Composants partagés** : `AppShell`, `Sidebar`, `TenantSwitcher`, `EmptyTenantState`
- **Bibliothèques** : React Hook Form 7.55, TanStack React Query 5.60, `react-resizable-panels` (panneau détail)
- **Lib** : `apiMappings.ts`, `stitchAssets.ts` (avatars), `utils.ts`

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | ⚠️ MOYENNE | `buildOwners()` est un hack : utilise les initiales des clés de l'objet `filters` comme avatars "owners" (ex : `filters.keywords[0]` → initiales) — sans aucun rapport avec de vrais utilisateurs | La table `watchlists` ne stocke pas de champ `owner`. Solution court terme : supprimer les avatars owners ou afficher un avatar générique "Équipe". Solution long terme : ajouter un champ `owner_ids` au schéma watchlist. |
| 2 | ⚠️ MOYENNE | Delta NSS affiché avec la même couleur pour positif et négatif (pas de distinction rouge/vert) | Appliquer `text-green-400` si `nss_delta >= 0`, `text-red-400` si `nss_delta < 0`. Idem pour l'icône flèche (↑ vert / ↓ rouge). |
| 3 | ⚠️ MOYENNE | Pas de dialogue de confirmation avant suppression (DELETE irréversible même si soft delete) | Ajouter un `<AlertDialog>` Shadcn/ui : "Êtes-vous sûr de désactiver cette watchlist ?" avec boutons Annuler/Confirmer |

#### Critères d'acceptation (Definition of Done)

- [ ] Les onglets Toutes/Actives/Inactives filtrent correctement la grille de watchlists
- [ ] La sélection d'une watchlist affiche ses métriques NSS, volume et répartition aspects dans le panneau de droite
- [ ] Le delta NSS est coloré en vert si positif, rouge si négatif
- [ ] La création d'une watchlist fonctionne et la liste se rafraîchit automatiquement
- [ ] La suppression déclenche un dialogue de confirmation avant l'appel DELETE
- [ ] Le bouton "Voir les détails analytiques" est fonctionnel (navigation ou panneau)
- [ ] Les avatars "owners" n'affichent pas de données incohérentes (fix ou suppression du hack `buildOwners()`)

---

---

## 7. Alertes — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/alertes` (protégée par `TenantProtectedRoute`) |
| Fichier(s) | `client/src/pages/Alertes.tsx` (521 lignes) |
| Rôle | Console de gestion des alertes en mode master-detail. Panneau gauche : liste scrollable d'alertes avec filtres par statut (new/acknowledged/resolved/dismissed) et sévérité (critical/high/medium/low). Panneau droit : détail de l'alerte sélectionnée avec description, extraits sociaux temps réel, localisation géographique, évaluation d'impact, et boutons d'action (Reconnaître / Écarter / Résoudre). Indicateur temps réel : compteur d'alertes actives avec point vert pulsant. |

#### Données consommées

| Endpoint | Méthode | Payload envoyé | Réponse attendue (schéma) | Fréquence |
|----------|---------|----------------|---------------------------|-----------|
| `/api/alerts` | GET | Query params : `status=<string\|undefined>`, `severity=<string\|undefined>`, `limit=50` | `[{ alert_id, severity: "critical"\|"high"\|"medium"\|"low", title, description, status: "new"\|"acknowledged"\|"resolved"\|"dismissed", social_excerpts: [{ content, source, url }], location: string, impact_score: number, created_at, updated_at }]` | Au montage (mount) et après chaque mutation de statut |
| `/api/alerts/{alert_id}/status` | PUT | Path param `alert_id`, body `{ status: "acknowledged"\|"dismissed"\|"resolved" }` | `{ result: "ok", alert_id, status }` | On-click "Reconnaître", "Écarter", ou "Résoudre" |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Filtre statut "Nouvelle" | Toggle filtre `status=new` — relance GET alerts | `/api/alerts?status=new` | ✅ Fonctionnel | — |
| Filtre statut "Reconnu" | Toggle filtre `status=acknowledged` | `/api/alerts?status=acknowledged` | ✅ Fonctionnel | — |
| Filtre statut "Résolu" | Toggle filtre `status=resolved` | `/api/alerts?status=resolved` | ✅ Fonctionnel | — |
| Filtre statut "Écarté" | Toggle filtre `status=dismissed` | `/api/alerts?status=dismissed` | ✅ Fonctionnel | — |
| Filtre sévérité "Critique" | Toggle filtre `severity=critical` | `/api/alerts?severity=critical` | ✅ Fonctionnel | — |
| Filtre sévérité "Haute" | Toggle filtre `severity=high` | `/api/alerts?severity=high` | ✅ Fonctionnel | — |
| Filtre sévérité "Moyenne" | Toggle filtre `severity=medium` | `/api/alerts?severity=medium` | ✅ Fonctionnel | — |
| Filtre sévérité "Basse" | Toggle filtre `severity=low` | `/api/alerts?severity=low` | ✅ Fonctionnel | — |
| Carte alerte (clic) | Sélectionne l'alerte, affiche son détail dans le panneau droit | Aucun (données déjà chargées) | ✅ Fonctionnel | — |
| "Reconnaître" | PUT `status=acknowledged`, invalide cache, rafraîchit la liste | `/api/alerts/{id}/status` PUT | ✅ Fonctionnel — ⚠️ Pas de disabled pendant mutation | Ajouter état `isPending` pour désactiver les 3 boutons |
| "Écarter" | PUT `status=dismissed` | `/api/alerts/{id}/status` PUT | ✅ Fonctionnel — ⚠️ Accent manquant + pas de disabled | Corriger "Ecarter" → "Écarter", ajouter `isPending` |
| "Résoudre" | PUT `status=resolved` | `/api/alerts/{id}/status` PUT | ✅ Fonctionnel — ⚠️ Pas de disabled pendant mutation | Ajouter état `isPending` |

#### Dépendances

- **Composants partagés** : `AppShell`, `Sidebar`, `TenantSwitcher`, `EmptyTenantState`
- **Bibliothèques** : TanStack React Query 5.60, Framer Motion 11.13
- **Lib** : `apiMappings.ts`

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | ⚠️ MOYENNE | Pas d'état `loading`/`disabled` sur les boutons "Reconnaître", "Écarter", "Résoudre" pendant la mutation → double-clic possible | Utiliser `isPending` de `useMutation` pour `disabled={isPending}` et afficher un spinner |
| 2 | ⚠️ MOYENNE | Les 3 boutons d'action sont toujours affichés même quand non pertinents (ex : "Résoudre" sur une alerte déjà résolue) | Afficher conditionnellement : si `status === "resolved"`, masquer "Résoudre". Si `status === "dismissed"`, masquer "Écarter". Si `status === "acknowledged"`, masquer "Reconnaître". |
| 3 | ⚠️ MOYENNE | Limite hardcodée à `limit=50` sans pagination → données tronquées si > 50 alertes | Ajouter une pagination ou un scroll infini. À défaut, augmenter la limite ou afficher un avertissement "Affichage limité à 50 alertes". |
| 4 | ⚠️ MOYENNE | Sévérités MOYENNE et BASSE partagent le même gradient visuel (indistinguables) | Attribuer des couleurs distinctes : CRITIQUE = rouge, HAUTE = orange, MOYENNE = jaune, BASSE = bleu/gris. |
| 5 | 🔵 BASSE | Fautes d'accent sur les boutons : "Ecarter" → "Écarter", "Reconnaitre" → "Reconnaître" | Corriger les chaînes de caractères |
| 6 | 🔵 BASSE | Cercle avatar vide pour les extraits sociaux (aucune image réelle, placeholder vide) | Remplacer par un avatar générique avec initiales de la source (ex : "F" pour Facebook) |

#### Critères d'acceptation (Definition of Done)

- [ ] Les filtres statut et sévérité fonctionnent en combinaison et filtrent correctement la liste
- [ ] La sélection d'une alerte affiche son détail complet (description, extraits sociaux, localisation, impact)
- [ ] Les boutons "Reconnaître", "Écarter", "Résoudre" sont désactivés pendant la mutation et affichent un spinner
- [ ] Les boutons d'action sont affichés conditionnellement selon le statut actuel de l'alerte
- [ ] Les libellés des boutons sont correctement accentués ("Reconnaître", "Écarter")
- [ ] Les 4 niveaux de sévérité sont visuellement distincts
- [ ] Une indication est donnée à l'utilisateur si la liste dépasse 50 alertes

---

---

## 8. Recommandations — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/recommandations` (protégée par `TenantProtectedRoute`) |
| Fichier(s) | `client/src/pages/Recommandations.tsx` (743 lignes) |
| Rôle | Module IA de génération et suivi des recommandations marketing. Trois sections : (1) Générateur — formulaire (déclencheur, provider LLM, modèle) + preview du contexte (NSS, volume, alertes, estimation tokens et coût USD) avant génération, (2) Recommandations actives — résumé + grille de cartes (priorité, titre, rationale, cible, timing, KPI cible), (3) Historique des runs — tableau daté. FAB flottant (bas droit) vers `/explorateur`. |

#### Données consommées

| Endpoint | Méthode | Payload envoyé | Réponse attendue (schéma) | Fréquence |
|----------|---------|----------------|---------------------------|-----------|
| `/api/recommendations/providers` | GET | Aucun | `{ providers: [{ provider_id: string, display_name: string, models: [{ model_id, display_name, price_per_1k_tokens_usd }] }] }` | Au montage (mount) |
| `/api/recommendations/context-preview` | GET | Query params : `trigger_type`, `trigger_id`, `provider`, `model` | `{ estimated_tokens: number, estimated_cost_usd: number, nss_score: number, mentions_count: number, active_alerts: number, context_summary: string }` | On-change des sélecteurs (debounced ou on-click "Actualiser") |
| `/api/recommendations` | GET | Query params : `status=active`, `limit=50` | `[{ recommendation_id, title, rationale, priority: "high"\|"medium"\|"low", target_audience: string, suggested_timing: string, kpi_target: string, confidence_pct: number, status, created_at }]` | Au montage (mount) |
| `/api/recommendations/generate` | POST | `{ trigger_type: string, trigger_id: string\|null, provider: string, model: string, api_key: string }` | `{ result: "ok", recommendation_id, count: number, confidence: number, generation_ms: number }` | Au clic "Générer" |
| `/api/recommendations/{recommendation_id}/status` | PUT | Path param `recommendation_id`, body `{ status: "archived"\|"dismissed" }` | `{ result: "ok", recommendation_id, status }` | Au clic "Archiver" (par carte), "✕" dismiss (par carte), "Tout Archiver" |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| "Générer" | POST vers `/api/recommendations/generate`, invalide cache, rafraîchit la liste des recommandations actives | `/api/recommendations/generate` POST | ✅ Fonctionnel | — |
| "Archiver" (par carte individuelle) | PUT `status=archived` sur la recommandation, invalide cache | `/api/recommendations/{id}/status` PUT | ✅ Fonctionnel | — |
| "✕" dismiss (par carte individuelle) | PUT `status=dismissed` sur la recommandation, invalide cache | `/api/recommendations/{id}/status` PUT | ✅ Fonctionnel | — |
| "Tout Archiver" | Archive en masse toutes les recommandations actives via forEach + mutate() | `/api/recommendations/{id}/status` PUT (N fois) | ⚠️ Fonctionnel mais race condition | Remplacer par `Promise.all()` ou implémenter un endpoint batch côté backend |
| FAB sparkle (bas droit) | Naviguer vers `#/explorateur` | Aucun | ✅ Fonctionnel | — |

#### Dépendances

- **Composants partagés** : `AppShell`, `Sidebar`, `TenantSwitcher`, `EmptyTenantState`
- **Bibliothèques** : TanStack React Query 5.60, React Hook Form 7.55, `date-fns` 3.6 (formatage dates), Framer Motion 11.13
- **Lib** : `apiMappings.ts`

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | 🔴 HAUTE | "Tout Archiver" utilise `forEach + mutate()` → race condition : le cache React Query est invalidé après le premier `mutate()`, relançant un rechargement avant que les autres mutations ne soient parties | Remplacer par `Promise.all(ids.map(id => mutateAsync({ id, status: 'archived' })))` puis invalider le cache une seule fois |
| 2 | ⚠️ MOYENNE | Label "Volume (m³)" dans le preview contexte — unité incohérente pour un système NLP (les m³ sont une unité de volume physique) | Remplacer par "Volume de mentions" |
| 3 | ⚠️ MOYENNE | Carte "Dernière run" : la valeur et le label sont inversés dans l'affichage | Corriger l'ordre value/label dans le composant de carte |
| 4 | ⚠️ MOYENNE | Dates ISO brutes (`2026-04-11T14:23:00Z`) affichées dans le tableau historique et dans l'en-tête des recommandations actives | Utiliser `date-fns` (déjà installé) : `format(parseISO(date), 'dd MMM yyyy HH:mm', { locale: fr })` |
| 5 | 🔵 BASSE | Possible `<a>` imbriqué : `<Link>` de Wouter enveloppe un `<a>` natif → HTML invalide | Vérifier tous les usages de `<Link>` dans la page. Utiliser `useNavigate()` + `<button>` ou `<div>` quand l'élément enfant est déjà un block interactif |

#### Critères d'acceptation (Definition of Done)

- [ ] Le formulaire de génération charge les providers et modèles LLM disponibles depuis l'API
- [ ] Le preview contexte affiche les estimations de tokens/coût avec les bons libellés (Volume de mentions, pas Volume m³)
- [ ] La carte "Dernière run" affiche value et label dans le bon ordre
- [ ] Les dates sont formatées en français lisible dans le tableau historique et les en-têtes
- [ ] "Tout Archiver" s'exécute sans race condition (Promise.all ou séquentiel avec invalidation unique)
- [ ] Les boutons Archiver/Dismiss individuels désactivent la carte pendant la mutation
- [ ] Le FAB navigue correctement vers `#/explorateur`

---

---

## 9. AdminSources — Contrat

| Élément | Détail |
|---------|--------|
| Route | `#/admin-sources` (pas de protection — accès libre sans tenant) |
| Fichier(s) | `client/src/pages/AdminSources.tsx` (111 lignes), `client/src/components/admin/AdminSourcesOps.tsx` (1441 lignes), `client/src/lib/adminSourcesViewModel.ts` |
| Rôle | Console d'opérateur pour la gestion de l'infrastructure de collecte. 4 sous-vues accessibles via tabs : (1) **Sources** — CRUD sources d'ingestion avec pipeline trace, historique sync et snapshots santé, (2) **Credentials** — gestion des credentials plateformes (OAuth tokens), (3) **Campaign Ops** — gestion des posts liés aux campagnes, métriques manuelles, screenshots, revenue, (4) **Scheduler** — visualisation et déclenchement du scheduler d'ingestion. |

#### Données consommées

| Endpoint | Méthode | Payload envoyé | Réponse attendue (schéma) | Fréquence |
|----------|---------|----------------|---------------------------|-----------|
| `/api/admin/sources` | GET | Query params : `client_id`, `platform`, `owner_type`, `status` | `[{ source_id, source_name, platform, source_type, owner_type, auth_mode, is_active, sync_frequency_minutes, last_sync_at, health_score, coverage_key }]` | Au montage (sous-vue Sources) |
| `/api/admin/sources/{source_id}/runs` | GET | Path param `source_id`, `limit=50` | `[{ sync_run_id, run_mode, status, records_fetched, records_inserted, records_failed, error_message, started_at, ended_at }]` | On-click sur une source (sélection) |
| `/api/admin/sources/{source_id}/snapshots` | GET | Path param `source_id`, `limit=50` | `[{ snapshot_id, health_score, success_rate_pct, freshness_hours, records_fetched_avg, computed_at }]` | On-click sur une source (sélection) |
| `/api/social-metrics/credentials` | GET | Query params : `platform`, `entity_type`, `is_active=true` | `[{ credential_id, entity_type, entity_name, platform, account_id, is_active, created_at }]` | Au montage (sous-vue Credentials) |
| `/api/campaigns` | GET | Header `X-Ramy-Client-Id` | `[{ campaign_id, name, platform, status }]` | Au montage (sous-vue Campaign Ops) |
| `/api/social-metrics/campaigns/{campaign_id}/posts` | GET | Path param `campaign_id` | `[{ post_id, platform, post_platform_id, post_url, entity_type, entity_name }]` | On-select campagne dans Campaign Ops |
| `/api/social-metrics/campaigns/{campaign_id}` | GET | Path param `campaign_id` | `{ campaign_id, total_likes, total_comments, total_shares, total_views, total_reach, total_impressions, total_saves, posts_count }` | On-select campagne dans Campaign Ops |

#### Actions utilisateur — Sous-vue Sources

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| "New Pipeline" | Ouvrir formulaire de création de source | Aucun | 🔴 BOUTON MORT (onClick absent) | Implémenter l'ouverture du formulaire (formulaire déjà présent dans AdminSourcesOps mais inaccessible via ce bouton) |
| Formulaire création source (soumission) | POST nouvelle source | `/api/admin/sources` POST | ✅ Fonctionnel | — |
| Formulaire édition source (soumission) | PUT mise à jour source | `/api/admin/sources/{id}` PUT | ✅ Fonctionnel | — |
| Bouton "Sync" (par source) | Déclenche sync manuelle de la source | `/api/admin/sources/{id}/sync` POST | ✅ Fonctionnel — ⚠️ Erreur silencieuse | Ajouter `onError` avec toast |
| Bouton "Health" (par source) | Calcule le snapshot de santé | `/api/admin/sources/{id}/health` POST | ✅ Fonctionnel — ⚠️ Erreur silencieuse | Ajouter `onError` avec toast |
| "Voir tout l'historique" | Afficher l'historique complet des sync runs | Aucun | 🔴 LIEN MORT (onClick absent) | Implémenter via une modale ou une extension du tableau déjà affiché (modifier `limit` à la demande) |

#### Actions utilisateur — Sous-vue Credentials

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Formulaire création credential (soumission) | POST nouveau credential | `/api/social-metrics/credentials` POST | ✅ Fonctionnel | — |
| Icône désactivation credential | DELETE (soft) du credential | `/api/social-metrics/credentials/{id}` DELETE | ✅ Fonctionnel — ⚠️ Pas de confirmation | Ajouter dialogue de confirmation |

#### Actions utilisateur — Sous-vue Campaign Ops

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Formulaire ajout post (soumission) | POST lier post social à la campagne | `/api/social-metrics/campaigns/{id}/posts` POST | ✅ Fonctionnel | — |
| Icône supprimer post | DELETE post + ses métriques | `/api/social-metrics/posts/{id}` DELETE | ✅ Fonctionnel — ⚠️ Pas de confirmation | Ajouter dialogue de confirmation |
| "Collecter automatiquement" | Collecte métriques Graph API pour la campagne | `/api/social-metrics/campaigns/{id}/collect` POST | ✅ Fonctionnel — ⚠️ Erreur silencieuse | Ajouter `onError` |
| Formulaire métriques manuelles (soumission) | POST métriques saisies manuellement | `/api/social-metrics/posts/{id}/metrics/manual` POST | ✅ Fonctionnel | — |
| Upload screenshot | POST fichier image pour parsing automatique des métriques | `/api/social-metrics/posts/{id}/metrics/screenshot` POST | ✅ Fonctionnel — 🔴 Bug auth : headers manquants | Remplacer `fetch()` brut par `queryClient.ts` ou ajouter manuellement les headers `X-API-Key` et `X-Ramy-Client-Id` |
| Formulaire revenue (soumission) | PATCH revenue attribué à la campagne | `/api/social-metrics/campaigns/{id}/revenue` PATCH | ✅ Fonctionnel | — |

#### Actions utilisateur — Sous-vue Scheduler

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| "Lancer un tick" | Déclenche un tick scheduler (exécute toutes les syncs dues) | `/api/admin/scheduler/tick` POST | ✅ Fonctionnel — ⚠️ Erreur silencieuse | Ajouter `onError` avec toast et `onSuccess` avec résultat (nb syncs déclenchées) |

#### Actions utilisateur — Sidebar AdminSources (AdminSources.tsx)

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| "Dashboard" (nav link) | Navigue vers `#/` | Aucun | ✅ Fonctionnel | — |
| "Ingestion" (nav active) | Page courante | Aucun | ✅ N/A | — |
| "Pipelines" (nav) | Naviguer vers une page Pipelines (non existante) | Aucun | 🔴 LIEN MORT (href absent) | Pour l'expo : masquer l'élément ou le désactiver visuellement avec `cursor-not-allowed` et tooltip "Disponible prochainement" |
| "Logs" (nav) | Naviguer vers une page Logs (non existante) | Aucun | 🔴 LIEN MORT (href absent) | Même traitement que Pipelines |
| "notifications" (icône header) | Ouvrir panneau notifications | Aucun | 🔴 BOUTON MORT (onClick absent) | Pour l'expo : masquer ou désactiver |
| "settings" (icône header) | Ouvrir paramètres | Aucun | 🔴 BOUTON MORT (onClick absent) | Pour l'expo : masquer ou désactiver |
| "Support" (sidebar footer) | Ouvrir page support | Aucun | 🔴 LIEN MORT (href absent) | Pour l'expo : masquer ou ajouter `mailto:support@ramypulse.com` |
| "Documentation" (sidebar footer) | Ouvrir doc | Aucun | 🔴 LIEN MORT (href absent) | Pour l'expo : masquer ou ajouter une URL docs |
| Nav items (Connectors, Health, Validation, Archive) | Naviguer vers sous-vues admin | Aucun | 🔴 LIENS MORTS (onClick absent) | Pour l'expo : masquer ces items non implémentés ou les désactiver visuellement |
| "Voir tout l'historique" | Étendre l'historique sync | Aucun | 🔴 LIEN MORT (onClick absent) | Implémenter via augmentation du `limit` de la requête |

#### Dépendances

- **Composants partagés** : Aucun `AppShell` (layout admin propriétaire avec sa propre sidebar)
- **Bibliothèques** : TanStack React Query 5.60, React Hook Form 7.55, Shadcn/ui
- **Lib** : `adminSourcesViewModel.ts`, `apiMappings.ts`

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | 🔴 HAUTE | Upload screenshot utilise `fetch()` brut sans les headers d'authentification `X-API-Key` et `X-Ramy-Client-Id` → l'upload peut échouer en production | Remplacer `fetch()` par le client HTTP configuré dans `queryClient.ts` (qui injecte automatiquement les headers), ou ajouter manuellement les headers dans la requête `fetch()` |
| 2 | ⚠️ MOYENNE | Pas de dialogue de confirmation avant suppression de post ou désactivation de credential (actions destructives) | Ajouter `<AlertDialog>` Shadcn/ui pour ces deux actions |
| 3 | ⚠️ MOYENNE | Mutations silencieuses sur sync, health check et scheduler tick : les erreurs ne sont pas présentées à l'utilisateur | Ajouter `onError` avec toast sur chaque `useMutation` concerné |
| 4 | 🔵 BASSE | `AdminSourcesOps.tsx` est un monolithe de 1441 lignes — difficile à maintenir | Découper en au moins 4 sous-composants : `SourcesTab`, `CredentialsTab`, `CampaignOpsTab`, `SchedulerTab` |
| 5 | 🔵 BASSE | Manque de `<label>` associé aux champs de formulaire (accessibilité) | Ajouter `htmlFor` sur tous les `<label>` et `id` correspondants sur les `<input>` |
| 6 | 🔵 BASSE | TikTok est filtré des options de création source dans l'UI mais présent dans `PLATFORM_OPTIONS` côté backend | Aligner : soit ajouter TikTok dans les options UI, soit le retirer de `PLATFORM_OPTIONS` backend |

#### Critères d'acceptation (Definition of Done)

- [ ] La sous-vue Sources liste toutes les sources avec leur statut de santé
- [ ] La création et l'édition de sources fonctionnent avec feedback succès/erreur
- [ ] La sync manuelle et le health check affichent un résultat (succès ou erreur) dans un toast
- [ ] La sous-vue Credentials liste et permet de créer/désactiver des credentials avec confirmation
- [ ] La sous-vue Campaign Ops permet d'ajouter/supprimer des posts et de saisir des métriques
- [ ] L'upload de screenshot transmet les headers d'authentification (bug critique corrigé)
- [ ] Le tick scheduler affiche le résultat (nombre de syncs déclenchées)
- [ ] Les éléments de navigation sans cible (Pipelines, Logs, etc.) sont masqués ou désactivés avec mention "Disponible prochainement"

---

---

## 10. NotFound — Contrat

| Élément | Détail |
|---------|--------|
| Route | Wildcard — toute route non matchée par le router (`*`) |
| Fichier(s) | `client/src/pages/not-found.tsx` (22 lignes) |
| Rôle | Page d'erreur 404. Affiche un message d'erreur quand une route inconnue est accédée. |

#### Données consommées

Aucun appel API.

| Endpoint | Méthode | Payload envoyé | Réponse attendue | Fréquence |
|----------|---------|----------------|------------------|-----------|
| — | — | — | — | — |

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| (Aucun bouton actuellement) | — | — | — | Ajouter un bouton "Retour au tableau de bord" → `navigate('#/')` |

#### Dépendances

- **Composants partagés** : Aucun (page autonome, pas d'AppShell)
- **Bibliothèques** : Wouter (hook `useLocation` ou `Link` pour le bouton retour)

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | 🔵 BASSE | Message d'erreur en anglais : "Did you forget to add the page to the router?" — incohérent avec le reste de l'application en français | Remplacer par "Cette page n'existe pas." et "Vérifiez l'URL ou retournez au tableau de bord." |
| 2 | 🔵 BASSE | Pas de lien/bouton de retour — l'utilisateur doit utiliser le bouton Précédent du navigateur | Ajouter `<Link to="/">Retour au tableau de bord</Link>` |

#### Critères d'acceptation (Definition of Done)

- [ ] Le message d'erreur est en français
- [ ] Un bouton "Retour au tableau de bord" est visible et fonctionnel
- [ ] La page s'intègre visuellement dans le design system Obsidian (fond sombre, typographie cohérente)
- [ ] Aucun appel réseau parasite au montage

---

---

## 11. Composant partagé — AppShell

| Élément | Détail |
|---------|--------|
| Route | N/A (composant layout) |
| Fichier(s) | `client/src/components/AppShell.tsx` (116 lignes) |
| Rôle | Layout principal de l'application : sidebar fixe à gauche (64px / w-64), header sticky en haut avec barre de recherche optionnelle, `TenantSwitcher`, icônes d'action, avatar utilisateur. Wraps toutes les pages produit (Dashboard, Explorateur, Campagnes, Watchlists, Alertes, Recommandations, WatchOnboarding). |

#### Props reçues

| Prop | Type | Obligatoire | Description |
|------|------|-------------|-------------|
| `children` | ReactNode | Oui | Contenu de la page |
| `title` | string | Oui | Titre de la page affiché dans le header |
| `subtitle` | string | Non | Sous-titre optionnel |
| `headerRight` | ReactNode | Non | Contenu custom côté droit du header |
| `headerSearchPlaceholder` | string | Non | Placeholder de la barre de recherche (si absent, pas de barre) |
| `onSearch` | (query: string) => void | Non | Callback de recherche |
| `avatar(s)` | ReactNode | Non | Avatar(s) utilisateur |
| `sidebarFooter` | ReactNode | Non | Contenu footer de la sidebar |

#### Données consommées

Aucun appel API direct.

#### Actions utilisateur — Header AppShell

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Icône "language" | Changer la langue de l'interface | Aucun | 🔴 BOUTON MORT (onClick absent) | Pour l'expo : masquer l'icône (l'app est 100% en français, pas de i18n implémenté). Long terme : implémenter i18next |
| Icône "grid_view" | Vue en grille (toggle layout ?) | Aucun | 🔴 BOUTON MORT (onClick absent) | Pour l'expo : masquer l'icône |
| Icône "notifications" | Ouvrir un panneau de notifications | Aucun | 🔴 BOUTON MORT (onClick absent) | Pour l'expo : masquer ou badger avec le nombre d'alertes critiques (depuis le cache React Query de `GET /api/dashboard/alerts-critical`) |
| Icône "sensors" | Statut temps réel / live mode | Aucun | 🔴 BOUTON MORT (onClick absent) | Pour l'expo : masquer l'icône |

#### Dépendances

- **Composants internes** : `Sidebar`, `TenantSwitcher`
- **Bibliothèques** : Wouter (routing), Material Symbols (icônes)

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | ⚠️ MOYENNE | 4 icônes du header sans `onClick` (language, grid_view, notifications, sensors) — UX trompeuse | Masquer les icônes non fonctionnelles pour l'expo. L'icône "notifications" peut être activée avec le badge d'alertes critiques. |

#### Critères d'acceptation (Definition of Done)

- [ ] La sidebar s'affiche correctement sur toutes les pages produit
- [ ] Le header affiche le titre, le `TenantSwitcher` et l'avatar utilisateur
- [ ] Aucun bouton du header n'est affiché sans comportement fonctionnel associé (masquer ou implémenter)
- [ ] La barre de recherche s'affiche uniquement quand `headerSearchPlaceholder` est fourni
- [ ] L'icône "notifications" affiche optionnellement un badge avec le nombre d'alertes actives

---

---

## 12. Composant partagé — Sidebar

| Élément | Détail |
|---------|--------|
| Route | N/A (composant navigation) |
| Fichier(s) | `client/src/components/Sidebar.tsx` (92 lignes) |
| Rôle | Barre de navigation latérale fixe. Affiche le logo "RamyPulse / Marketing Intelligence", les 7 liens de navigation principaux (avec icônes Material Symbols), et un footer avec l'avatar utilisateur. Utilisé exclusivement via `AppShell`. |

#### Liens de navigation

| Lien | Destination | Icône | Statut |
|------|-------------|-------|--------|
| Tableau de bord | `#/` | dashboard | ✅ Fonctionnel |
| Explorateur | `#/explorateur` | explore | ✅ Fonctionnel |
| Campagnes | `#/campagnes` | campaign | ✅ Fonctionnel |
| Watchlists | `#/watchlists` | visibility | ✅ Fonctionnel |
| Alertes | `#/alertes` | notifications_active | ✅ Fonctionnel |
| Recommandations | `#/recommandations` | auto_awesome | ✅ Fonctionnel |
| Admin Sources | `#/admin-sources` | settings_input_component | ✅ Fonctionnel |

#### Données consommées

Aucun appel API direct.

#### Bugs à corriger

| # | Sévérité | Bug | Fix proposé |
|---|----------|-----|-------------|
| 1 | 🔵 BASSE | Footer avec "Ammar, Brand Manager" hardcodé — pas dynamique | Remplacer par un prop `user` passé depuis `AppShell` (nom + rôle). À court terme pour l'expo, peut rester tel quel si le tenant de démo s'appelle Ammar. |

#### Critères d'acceptation (Definition of Done)

- [ ] Tous les liens de navigation fonctionnent et naviguent vers la bonne route
- [ ] Le lien actif est mis en surbrillance (classe active correcte selon la route courante)
- [ ] Le logo s'affiche correctement
- [ ] Le footer affiche un nom d'utilisateur (même hardcodé pour l'expo)

---

---

## 13. Composant partagé — TenantSwitcher

| Élément | Détail |
|---------|--------|
| Route | N/A (composant header) |
| Fichier(s) | `client/src/components/TenantSwitcher.tsx` (49 lignes) |
| Rôle | Sélecteur de tenant intégré dans le header d'AppShell. Permet à l'opérateur de saisir un `client_id` manuellement, de le sauvegarder en `localStorage` (`ramypulse.activeTenantId`), et de l'effacer. Les autres composants lisent ce `client_id` depuis le contexte tenant et l'injectent dans le header `X-Ramy-Client-Id` de chaque appel API. |

#### Données consommées

Aucun appel API — lecture/écriture directe dans `localStorage` via `tenantContext.ts`.

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Champ texte (saisie tenant ID) | Met à jour l'input local (state React) | Aucun | ✅ Fonctionnel | — |
| "Save" | Écrit le `client_id` dans `localStorage`, invalide tous les caches React Query | Aucun | ✅ Fonctionnel | — |
| "Clear" | Efface le `client_id` du `localStorage`, redirige vers `#/nouveau-client` | Aucun | ✅ Fonctionnel | — |

#### Dépendances

- **Lib** : `tenantContext.ts` (lecture/écriture localStorage), `queryClient.ts` (invalidation cache)
- **Bibliothèques** : Shadcn/ui (Input, Button)

#### Bugs à corriger

Aucun bug identifié.

#### Critères d'acceptation (Definition of Done)

- [ ] Saisir un `client_id` et cliquer "Save" met à jour toutes les pages (cache invalidé, données rechargées)
- [ ] "Clear" efface le tenant et redirige vers le wizard d'onboarding
- [ ] L'input affiche le `client_id` courant au chargement
- [ ] Le header `X-Ramy-Client-Id` est correctement injecté dans tous les appels API après sauvegarde

---

---

## 14. Composant partagé — EmptyTenantState

| Élément | Détail |
|---------|--------|
| Route | N/A (composant état vide) |
| Fichier(s) | `client/src/components/EmptyTenantState.tsx` (33 lignes) |
| Rôle | Écran d'état vide affiché quand un tenant est actif (tenant ID défini) mais n'a pas encore de données (pas de verbatims, pas de campagnes, etc.). Affiche un message explicatif et un lien vers `#/nouveau-client` pour lancer l'onboarding. Utilisé par : Dashboard, Explorateur, Campagnes, Watchlists, Alertes, Recommandations. |

#### Données consommées

Aucun appel API.

#### Actions utilisateur

| Action/Bouton | Effet attendu | Endpoint backend | Statut actuel | Action requise |
|---------------|---------------|------------------|---------------|----------------|
| Lien vers `/nouveau-client` | Navigue vers le wizard d'onboarding `#/nouveau-client` | Aucun | ✅ Fonctionnel | — |

#### Dépendances

- **Bibliothèques** : Wouter (`Link`)

#### Bugs à corriger

Aucun bug identifié.

#### Critères d'acceptation (Definition of Done)

- [ ] S'affiche correctement dans chaque page qui l'utilise quand les données API retournent un tableau vide
- [ ] Le lien vers `#/nouveau-client` fonctionne
- [ ] Le message explique clairement pourquoi il n'y a pas de données et comment en obtenir

---

---

## Annexe — Matrice de priorité des corrections

### Bugs HAUTE sévérité (à corriger avant expo)

| # | Page | Bug | Effort estimé |
|---|------|-----|---------------|
| 1 | Dashboard | 3 éléments cliquables sans `onClick` (cartes alertes, cartes actions, bouton CTA) | S (1-2h) |
| 2 | AdminSources | Upload screenshot sans headers d'auth | XS (30min) |
| 3 | Recommandations | Race condition "Tout Archiver" (forEach+mutate) | S (1-2h) |
| 4 | Explorateur | `formatSentimentLabel()` manque `"tres_negatif"` | XS (15min) |
| 5 | Campagnes | Mutation création sans `onError` → échec silencieux | XS (15min) |

### Boutons morts à corriger en priorité

| # | Page | Bouton | Action requise |
|---|------|--------|----------------|
| 1 | Dashboard | "VOIR DETAILS" (×3) | Navigation contextuelle |
| 2 | Explorateur | "Filtrer" | Panneau filtres avancés |
| 3 | Explorateur | "Exporter" | Export CSV client-side |
| 4 | Campagnes | "EXPORTER DATA" | Export CSV client-side |
| 5 | Watchlists | "Voir les détails analytiques" | Navigation Explorateur |
| 6 | AppShell | 4 icônes header | Masquer pour l'expo |
| 7 | AdminSources | 9 liens/boutons nav | Masquer ou désactiver |

### Endpoints backend non utilisés (potentiels futurs boutons)

| Endpoint | Fonctionnalité potentielle |
|----------|---------------------------|
| `GET /api/alerts/{alert_id}` | Page détail alerte isolée |
| `PUT /api/watchlists/{id}` | Formulaire édition watchlist |
| `DELETE /api/campaigns/{id}` | Bouton suppression campagne |
| `PUT /api/campaigns/{id}/status` | Bouton changement statut campagne |
| `POST /api/auth/keys` | Page gestion clés API |
| `POST /api/admin/normalization` | Bouton normalisation manuelle dans Admin |
| `POST /api/admin/runtime/cycle` | Bouton cycle automation complet dans Admin |

---

*Fin des contrats page-par-page RamyPulse — Branche `feat/watch-first-expo-ready`*
