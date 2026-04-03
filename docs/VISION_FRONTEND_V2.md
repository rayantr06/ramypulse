# RamyPulse — Vision Frontend v2

## Contexte

Le backend Wave 5 est solide : campaigns, alerts, watchlists, recommendations, ABSA engine, entity resolver, RAG. Mais le frontend Streamlit actuel est un tableau de bord d'ingénieur, pas un outil de décision. L'UX ne guide pas l'action.

Ce document définit l'architecture cible du frontend et la couche API qui le sépare du backend.

---

## 1. Diagnostic de l'existant

### Ce qui fonctionne (backend)
- `core/campaigns/` — CRUD + impact 3 fenêtres + attribution
- `core/alerts/` — détection 5 règles + déduplication + cycle de vie
- `core/watchlists/` — CRUD + snapshots métriques
- `core/recommendation/` — multi-provider (Gemini, Claude, GPT, Ollama) + prompt v1.1 grounded
- `core/analysis/` — ABSA, NSS, sentiment, aspects
- `core/rag/` — embedder + retriever hybride FAISS/BM25
- 593+ tests automatisés

### Ce qui ne fonctionne pas (frontend)
- **Dashboard** : affiche des chiffres bruts sans contexte ni guidance
- **What-If** : simulateur redondant avec l'agent de recommandation
- **Chat RAG** : page isolée, devrait être intégré dans l'exploration
- **Métriques** : NSS, volumes, graphiques — un data scientist comprend, pas un directeur marketing
- **Pas de couche API** : les pages Streamlit appellent directement `core/`, impossible de brancher un autre frontend

---

## 2. Architecture cible

### Pages à conserver (6 pages, refondues)

| # | Page | Rôle | Contenu clé |
|---|------|------|-------------|
| 1 | **Dashboard décisionnel** | Vue d'ensemble pour la prise de décision | Score santé marque, tendance, 3 alertes critiques, top 3 actions recommandées, résumé LLM en langage naturel |
| 2 | **Campagnes** | Créer et mesurer l'impact marketing | Liste avec uplift visible, création guidée, vue détail timeline + KPIs + heatmap ABSA, comparaison multi-campagnes |
| 3 | **Centre d'alertes** | Alertes + watchlists fusionnées | Alertes triées par sévérité, cycle de vie (new → acknowledged → resolved), watchlists avec métriques live, lien direct vers recommandations |
| 4 | **Recommandations** | Agent IA : analyse + actions concrètes | Choix provider/modèle, prévisualisation contexte, génération, cartes recommandation expandables, historique, lien "créer campagne" |
| 5 | **Explorer** | Recherche dans les verbatims clients | Recherche RAG intégrée, filtres (canal, wilaya, aspect, sentiment, période), verbatims en contexte avec sentiment et source |
| 6 | **Admin** | Configuration système | Sources de données, catalogue produits/wilayas/concurrents, config agent IA, gestion clés API |

### Pages supprimées

| Page | Raison |
|------|--------|
| **What-If** (`04_whatif.py`) | Redondant avec l'agent de recommandation. Simuler manuellement des scénarios n'a plus de sens quand l'IA analyse les vraies données et propose des actions concrètes. |
| **Chat RAG séparé** (`03_chat.py`) | Fusionné dans Explorer. Une page de chat isolée sans contexte visuel n'aide pas. La recherche RAG est plus utile intégrée dans l'exploration des verbatims. |

---

## 3. Dashboard décisionnel — Spécification

Le dashboard est la page la plus critique. Il doit répondre à une seule question : **"Comment va ma marque et que dois-je faire ?"**

### Sections (de haut en bas)

#### 3.1 Score santé marque
- Un seul chiffre de 0 à 100 (dérivé du NSS normalisé + volume + tendance)
- Couleur : vert (> 70), orange (40-70), rouge (< 40)
- Tendance : flèche haut/bas avec delta vs semaine précédente
- Phrase résumé en français : "Votre marque est en bonne santé. Le NSS a progressé de +8 pts cette semaine, porté par le sentiment positif sur Instagram."

#### 3.2 Alertes critiques (max 3)
- Cartes compactes : icône sévérité + titre + depuis quand
- Clic → Centre d'alertes
- Si aucune alerte : "Aucune alerte critique. Tout est sous contrôle."

#### 3.3 Actions recommandées (top 3)
- Depuis la dernière génération de recommandations
- Priorité + titre + plateforme cible
- Clic → Recommandations
- Si aucune reco : bouton "Générer des recommandations"

#### 3.4 Tendances rapides
- NSS par aspect (5 barres horizontales, triées du pire au meilleur)
- Volume par canal (donut chart)
- Évolution NSS 30 jours (sparkline simple)

#### 3.5 Résumé intelligent (optionnel, si LLM disponible)
- Résumé généré automatiquement de la situation en 3-4 phrases
- Basé sur le contexte client complet (le même que l'agent de reco)
- Rafraîchi 1x/jour ou à la demande

---

## 4. Couche API — FastAPI

### Pourquoi
- Séparer le backend du frontend
- Permettre n'importe quel frontend (React, mobile, Stitch) de consommer les données
- Garder Streamlit comme admin panel interne pendant la transition

### Endpoints cibles

```
GET  /api/health                          → statut système

# Dashboard
GET  /api/dashboard/summary               → score santé, tendances, résumé
GET  /api/dashboard/alerts-critical       → top 3 alertes critiques
GET  /api/dashboard/top-actions           → top 3 recommandations actives

# Campagnes
GET  /api/campaigns                       → liste (filtres: status, platform)
POST /api/campaigns                       → créer
GET  /api/campaigns/{id}                  → détail
PUT  /api/campaigns/{id}/status           → changer statut
GET  /api/campaigns/{id}/impact           → calcul impact 3 fenêtres
DEL  /api/campaigns/{id}                  → supprimer

# Alertes & Watchlists
GET  /api/alerts                          → liste (filtres: status, severity)
PUT  /api/alerts/{id}/status              → changer statut
GET  /api/watchlists                      → liste
POST /api/watchlists                      → créer
GET  /api/watchlists/{id}/metrics         → métriques courantes

# Recommandations
POST /api/recommendations/generate        → générer (provider, model, trigger)
GET  /api/recommendations                 → historique
GET  /api/recommendations/{id}            → détail
PUT  /api/recommendations/{id}/status     → archiver/rejeter
GET  /api/recommendations/context-preview → prévisualisation du contexte

# Explorer
GET  /api/explorer/search                 → recherche RAG (query, filtres)
GET  /api/explorer/verbatims              → liste paginée avec filtres

# Admin
GET  /api/admin/config                    → config agent
PUT  /api/admin/config                    → sauvegarder config
GET  /api/admin/sources                   → sources de données
GET  /api/admin/catalog/products          → catalogue produits
```

### Stack technique
- FastAPI + Uvicorn
- Appelle directement les modules `core/` existants
- CORS activé pour le frontend React
- Pas d'ORM — SQLite via les managers existants
- Auth : bearer token simple pour le PoC (mono-client)

---

## 5. Frontend React — Architecture

### Stack recommandée
- **Vite + React 18** (ou React 19)
- **TailwindCSS** pour le design system
- **Recharts** ou **Plotly.js** pour les graphiques
- **TanStack Query** pour le data fetching et le cache
- **React Router** pour la navigation

### Design system
- Palette : bleu foncé (#1e293b) + accent orange (#f97316) + vert/rouge pour les indicateurs
- Mode sombre par défaut (décisionnel = souvent consulté le soir/matin)
- Cards avec glassmorphism subtil, pas de surcharge
- Typographie : Inter ou Geist, grands chiffres lisibles
- Mobile-first : le directeur marketing consulte depuis son téléphone

### Utilisation de Google Stitch
- Prototyper les 6 écrans principaux dans Stitch
- Exporter le JSX/CSS généré
- Adapter pour brancher sur les endpoints FastAPI
- Stitch accélère le prototypage, le code final est maintenu manuellement

---

## 6. Plan d'exécution

| Phase | Contenu | Prérequis |
|-------|---------|-----------|
| **Phase 1** | Couche FastAPI — tous les endpoints ci-dessus | Backend existant |
| **Phase 2** | Prototypage Stitch — 6 écrans | Aucun |
| **Phase 3** | Frontend React — Dashboard + Campagnes | Phases 1 + 2 |
| **Phase 4** | Frontend React — Alertes + Recommandations + Explorer | Phase 3 |
| **Phase 5** | Frontend React — Admin + polish + mobile | Phase 4 |
| **Phase 6** | Supprimer Streamlit (ou le garder comme admin interne) | Phase 5 |

---

## 7. Principe directeur

**Chaque pixel à l'écran doit aider à prendre une décision ou à lancer une action.**

- Pas de chiffre sans contexte ("NSS = 42" → "NSS = 42, en hausse de +8 pts, au-dessus de la moyenne sectorielle")
- Pas de graphique sans insight ("Volume par jour" → "Pic de volume mardi, corrélé à la campagne Oran")
- Pas de page sans call-to-action (le dashboard dit quoi faire, pas juste comment ça va)
- Pas de donnée technique exposée à l'utilisateur final (pas de UUID, pas de JSON brut, pas de code d'erreur SQLite)

---

*Version 1.0 — 2 avril 2026*
*Ce document est la source de vérité pour le redesign frontend RamyPulse.*
