# RamyPulse — PRD Post-Wave 4

**Version :** 6.0  
**Date :** 2026-03-28  
**Statut :** Document directeur de référence  
**Auteur :** Product Strategy & Architecture  
**Classification :** Interne — Diffusion restreinte

---

## Résumé exécutif

RamyPulse dispose aujourd'hui d'un socle réel, testable et déjà utile :

- pipeline locale `01 -> 05`
- normalisation dialecte algérien / Arabizi / français
- extraction d'aspects
- calcul NSS
- RAG local
- dashboard Streamlit
- simulation What-If

Le projet a été revalidé dans un venv dédié le 2026-03-28 avec :

- 53 fichiers Python
- environ 7 946 lignes Python
- 309 tests verts

Mais le produit n'est pas encore au niveau de la version cible.

Le point le plus critique est le suivant :

**Le classifieur de sentiment actuel n'est pas encore opérationnel pour une utilisation de production.**

État honnête du classifieur aujourd'hui :

- le modèle principal n'est pas fine-tuné sur la tâche 5 classes
- il charge les poids pré-entraînés avec adaptation de tête
- les résultats actuels ne doivent pas être considérés comme fiables pour piloter le métier
- une chaîne de fallback existe, dont un fallback heuristique très limité

Conséquence :

- tous les NSS
- toutes les tendances
- toute lecture ABSA
- toute future logique de surveillance

restent fragiles tant que la fiabilisation du cœur ML n'est pas faite.

La décision stratégique de ce PRD est donc double :

1. **continuer sur l'existant**, pas repartir de zéro
2. **transformer le socle actuel vers une plateforme complète d'intelligence marketing actionnable**

La cible finale n'est pas un simple « dashboard amélioré ».
RamyPulse doit devenir une plateforme organisée autour de 5 modules constitutifs :

- **Listen** — Collecter, normaliser, enrichir
- **Understand** — Analyser, comparer, explorer
- **Monitor** — Surveiller, détecter, alerter
- **Recommend** — Transformer les signaux en options d'action
- **Measure** — Mesurer les campagnes, activations et partenariats

Et portée par 4 surfaces produit majeures :

- **Market Radar** — Vue marché globale
- **Watch Center** — Centre de surveillance
- **Campaign Lab** — Pilotage des activations
- **Recommendation Desk** — Aide à la décision

Le cœur analytique doit rester robuste, auditable, explicable et exploitable localement.

La version finale assume aussi une couche d'intelligence avancée pour les synthèses stratégiques, les recommandations complexes, les rapports intelligents et les arbitrages multi-facteurs. Cette couche peut s'appuyer sur des modèles puissants, y compris via API, si cela est justifié par la valeur métier — sans jamais rendre le cœur dépendant.

---

## Table des matières

1. [Résumé exécutif](#résumé-exécutif)
2. [Glossaire](#glossaire)
3. [Décision directrice](#3-décision-directrice)
4. [Vision produit](#4-vision-produit)
5. [Problème business adressé](#5-problème-business-adressé)
6. [Personas et utilisateurs cibles](#6-personas-et-utilisateurs-cibles)
7. [Positionnement du produit](#7-positionnement-du-produit)
8. [État actuel du projet et limites actuelles](#8-état-actuel-du-projet-et-limites-actuelles)
9. [Vision cible post-Wave 4](#9-vision-cible-post-wave-4)
10. [Modules fonctionnels](#10-modules-fonctionnels)
11. [Architecture logique](#11-architecture-logique)
12. [Modèle de données](#12-modèle-de-données)
13. [Registre de sources, entités métier, watchlists, campagnes](#13-registre-de-sources-entités-métier-watchlists-campagnes)
14. [Moteur d'alertes](#14-moteur-dalertes)
15. [Moteur de recommandations](#15-moteur-de-recommandations)
16. [Campaign intelligence et influencer tracking](#16-campaign-intelligence-et-influencer-tracking)
17. [Place du RAG dans l'ensemble](#17-place-du-rag-dans-lensemble)
18. [Règles d'attribution et garde-fous](#18-règles-dattribution-et-garde-fous)
19. [Workflows utilisateur](#19-workflows-utilisateur)
20. [Intégrations client](#20-intégrations-client)
21. [Roadmap en phases](#21-roadmap-en-phases)
22. [Risques, arbitrages et contraintes non négociables](#22-risques-et-arbitrages)
23. [Critères de qualité par module et par phase](#23-critères-de-qualité-par-module-et-par-phase)
24. [Baseline d'audit retenue](#24-baseline-daudit-retenue)

[Annexes](#annexes)

---

## Glossaire

| Terme | Définition |
|-------|-----------:|
| **ABSA** | Aspect-Based Sentiment Analysis — analyse de sentiment liée à des aspects métier spécifiques |
| **NSS** | Net Sentiment Score — (très_positif + positif − négatif − très_négatif) / total × 100. Plage : [-100, +100] |
| **DziriBERT** | Modèle BERT pré-entraîné sur le dialecte algérien (Arabizi + arabe dialectal) |
| **E5** | `intfloat/multilingual-e5-base` — modèle d'embeddings multilingue 768 dims pour la recherche sémantique |
| **FAISS** | Facebook AI Similarity Search — index de vecteurs en local (HNSW, M=32) |
| **RAG** | Retrieval-Augmented Generation — Q&A appuyé sur les documents retrouvés |
| **RRF** | Reciprocal Rank Fusion — fusion dense + sparse (score = Σ 1/(60 + rank)) |
| **Watchlist** | Objet métier configurable définissant un périmètre de surveillance avec seuils et métriques |
| **Wilaya** | Division administrative algérienne (58 wilayas) |
| **SKU** | Stock Keeping Unit — référence produit unique |
| **Part de voix** | Share of Voice — proportion des mentions d'une marque vs total marché |
| **Local-first** | Le cœur analytique fonctionne intégralement sans connexion internet ni service cloud |
| **Mode Enhanced** | Mode optionnel activant un LLM cloud (Claude API, OpenAI, Mistral) pour synthèses et recommandations avancées |
| **Market Radar** | Surface produit : vue d'ensemble marque + concurrents + thèmes marché |
| **Watch Center** | Surface produit : centre de surveillance watchlists + alertes |
| **Campaign Lab** | Surface produit : pilotage des campagnes, activations et influenceurs |
| **Recommendation Desk** | Surface produit : recommandations structurées, priorisées et validables |
| **Signal Engine** | Moteur de calcul : NSS, volumes, variations, anomalies, tendances émergentes |
| **Entity Resolution** | Mapping des mentions vers les entités métier (marque, produit, wilaya, concurrent) |

---

## 3. Décision directrice

### 3.1 Continuer sur l'existant

Le produit doit continuer sur le repo actuel.

Raisons :

- le socle analytique existe déjà (normalisation, ABSA, NSS, What-If, RAG)
- les contrats principaux existent déjà (5 classes, config centralisée, pipeline scripts)
- les surfaces produit de base existent déjà (Dashboard, Explorer, Chat, What-If)
- la couverture de tests existe déjà (309 tests, mocking complet)
- la vision post-Wave 4 prolonge logiquement ce socle

### 3.2 Pourquoi ne pas recoder de zéro

Un rewrite complet détruirait une partie de la valeur déjà acquise :

- expertise dialecte algérien (normalisation tri-script, lexique Arabizi)
- structure ABSA (5 aspects, dictionnaires bilingues)
- logique NSS (formule validée, zero-division safe, weekly trends)
- logique What-If (3 scénarios, immutabilité, saturation)
- logique RAG (FAISS HNSW + BM25 + RRF)
- orchestration scripts (pipeline 01→05)
- conventions projet (docstrings français, logging, config centralisée)
- couverture de tests (309 tests, tous passent sans modèles réels)

Le bon chemin est : « garder le socle utile, corriger le critique, enrichir le produit, puis industrialiser ».

### 3.3 Type de transformation retenue

La transformation retenue est :

- **progressive** — pas de big bang
- **structurée** — 5 modules, 4 surfaces, schéma de données défini
- **phasée** — 5 phases avec critères de sortie
- **guidée par des critères de sortie** — chaque phase validée avant passage à la suivante

Elle se fera en 5 phases :

- Phase 0 : fiabilisation du cœur ML
- Phase 1 : foundation métier (registre, catalogue, entités)
- Phase 2 : monitoring et market intelligence
- Phase 3 : campaign intelligence et recommandation avancée
- Phase 4 : scale et industrialisation

---

## 4. Vision produit

### 1.1 Énoncé de vision

RamyPulse est une plateforme d'intelligence marketing locale pour le marché algérien. Elle transforme les retours consommateurs multi-canaux en dialecte algérien, les signaux de marché et les données d'activation en décisions opérationnelles concrètes.

La trajectoire du produit le positionne comme plateforme de pilotage marketing complète — pas un simple outil de dashboard ou de social listening.

### 1.2 Les 5 modules constitutifs

RamyPulse s'organise autour de 5 modules constitutifs :

| Module | Question adressée | Fonction |
|--------|-------------------|----------|
| **Listen** | « Que se dit-il ? » | Collecte, normalisation, classification multi-sources, registre de sources |
| **Understand** | « Que signifient ces données ? » | ABSA, NSS, exploration, RAG, What-If, segmentation, tendances |
| **Monitor** | « Que faut-il surveiller ? » | Watchlists métier, alertes proactives, anomalies, signaux faibles |
| **Recommend** | « Que devrait-on faire ? » | Détection → qualification → contexte → génération → scoring → validation |
| **Measure** | « Est-ce que ça a marché ? » | Campaign Lab, suivi influenceurs, mesure avant/pendant/après, rapports |

### 1.3 Les 4 surfaces produit

Les 4 surfaces correspondent aux points d'entrée utilisateur au-delà du socle existant (Dashboard, Explorer, RAG Chat, What-If).

| Surface | Module(s) | Fonction | Phase d'arrivée |
|---------|-----------|----------|-----------------|
| **Market Radar** | Listen + Understand + Monitor | Vue marché globale : marque, concurrents, thèmes, buzz, part de voix | Phase 2 |
| **Watch Center** | Monitor | Watchlists actives, alertes récentes, signaux en dégradation/amélioration | Phase 2 |
| **Campaign Lab** | Measure + Recommend | Création de campagne, suivi en cours, B/D/A, suivi influenceurs, rapport | Phase 3 |
| **Recommendation Desk** | Recommend | Priorités d'action, options, justification, export | Phase 2 (règles) → Phase 3 (enhanced) |

### 1.4 Deux modes de fonctionnement

Le local-first s'applique au cœur analytique. Le produit dispose aussi d'un mode enhanced optionnel.

| Dimension | Mode Local (Core) | Mode Enhanced (Optionnel) |
|-----------|--------------------|---------------------------|
| **Classification sentiment** | DziriBERT fine-tuné local | — |
| **Calcul NSS, alertes** | Statistique local (pandas/numpy) | — |
| **Aspect extraction** | Dictionnaires + règles local | — |
| **FAISS + BM25** | Recherche hybride locale | — |
| **What-If** | Simulation locale | — |
| **RAG basique** | Ollama local (llama3.2:3b) | LLM cloud pour synthèses RAG avancées |
| **Recommandations** | Moteur de règles + templates | LLM cloud pour raisonnement multi-facteurs |
| **Résumés de campagne** | Templates structurés | LLM cloud pour résumé narratif |
| **Rapport de campagne** | Métriques + tableaux locaux | LLM cloud pour synthèse exécutive |

**Règle :** Le mode enhanced est activé par configuration (`config.ENHANCED_MODE=True` + `config.CLOUD_LLM_API_KEY`). Il n'est jamais obligatoire. Le cœur complet fonctionne sans internet après le setup initial. Le mode enhanced multiplie la valeur métier — il ne la crée pas.

### 1.5 Ce que RamyPulse n'est pas

- Pas un outil de social listening généraliste mondial.
- Pas un outil de BI générique.
- Pas un CRM, pas un outil de publication, pas un outil de collecte de masse non ciblée.
- Pas un système où le LLM cloud est obligatoire pour obtenir de la valeur.

RamyPulse est une plateforme d'intelligence marketing **spécialisée** sur le marché algérien, avec une expertise linguistique unique sur le dialecte local.

---

## 5. Problème business adressé

### 2.1 Contexte marché

Les entreprises algériennes du secteur agroalimentaire et FMCG sont confrontées à 5 défis structurels :

1. **Opacité du feedback client** — Les retours consommateurs sont éparpillés entre Facebook, Google Maps, YouTube, SAV et terrain. Aucun outil ne les unifie ni ne les analyse automatiquement en dialecte algérien.

2. **Angle mort linguistique** — Le dialecte algérien (Arabizi, arabe dialectal mélangé au français) n'est couvert par aucune solution du marché. Les outils internationaux (Brandwatch, Sprinklr, Talkwalker) ne comprennent pas « haja bnina bzf » ni « ma lgitouch f l'marché ».

3. **Réactivité au lieu de proactivité** — Les équipes marketing découvrent les problèmes quand ils deviennent des crises. Pas de surveillance continue sur les dimensions métier (produit × wilaya × aspect × canal).

4. **Mesure floue des campagnes** — Les activations digitales et terrain sont évaluées subjectivement. Pas de mesure d'impact rigoureuse corrélant perception consommateur et actions marketing.

5. **Absence d'intelligence marché locale** — Pas de vision structurée sur les concurrents, les tendances du marché, les thèmes émergents dans la catégorie. Les décisions se prennent sur l'intuition.

### 2.2 Coût de ne pas résoudre

| Impact | Description |
|--------|-------------|
| Perte de revenus | Problèmes de disponibilité ou de perception non détectés à temps dans une wilaya |
| Gaspillage budget | Campagnes et influenceurs financés sans mesure d'efficacité réelle |
| Retard concurrentiel | Concurrents qui montent en perception non identifiés à temps |
| Érosion de marque | Signaux faibles de dégradation (emballage, fraîcheur, goût) non captés |
| Temps perdu | Heures passées à compiler manuellement des retours terrain |
| Décisions aveugles | Pas de données structurées pour arbitrer entre priorités marketing |

### 2.3 Hypothèse centrale

**Si** une entreprise algérienne dispose d'un système unifié qui collecte, analyse, surveille, recommande et mesure à partir des retours consommateurs multi-canaux en dialecte local, **alors** elle prend de meilleures décisions marketing, détecte les problèmes plus tôt, mesure l'impact réel de ses actions et optimise ses investissements.

---

## 6. Personas et utilisateurs cibles

### 3.1 Persona principal : Directeur Marketing / CMO

**Profil :** Décideur marketing dans une entreprise agroalimentaire algérienne (Ramy, Hamoud, Ifri, NCA Rouiba).

**Besoins :**
- Vue d'ensemble instantanée de la perception marque et produits
- Alertes proactives sur les signaux critiques
- Comparaison avec la concurrence (part de voix, positionnement)
- Mesure d'impact des campagnes et activations
- Recommandations d'action priorisées et traçables

**Surfaces principales :** Dashboard, Market Radar, Recommendation Desk.

**Fréquence :** Quotidien (dashboard, alertes) + hebdomadaire (rapports, recommandations) + ponctuel (analyses de campagne).

**Critère de succès :** « En 5 minutes, je sais ce qui se passe sur ma marque, mes produits et mes concurrents. Je suis alerté quand un signal nécessite une action. J'ai des recommandations concrètes. »

### 3.2 Persona secondaire : Brand Manager / Chef de Produit

**Profil :** Responsable d'une gamme ou d'un produit, en charge du suivi opérationnel.

**Besoins :**
- NSS détaillé par produit, gamme, wilaya
- Suivi de l'impact d'un lancement ou d'une promotion
- Exploration détaillée des retours sur ses produits
- Watchlists ciblées sur sa gamme
- Simulation What-If pour prioriser les actions
- Pilotage complet de ses campagnes dans Campaign Lab

**Surfaces principales :** Dashboard, Explorer, Campaign Lab, What-If.

**Fréquence :** Quotidien.

**Critère de succès :** « Je justifie mes décisions produit par des données consommateurs structurées. Je mesure l'impact réel de mes campagnes. »

### 3.3 Persona tertiaire : Analyste Data / Insights

**Profil :** Profil analytique qui configure le système, crée les watchlists, gère les sources, pilote les campagnes et produit des analyses approfondies.

**Besoins :**
- Configuration des sources et du registre métier
- Création et gestion des watchlists
- Interrogation RAG pour des explorations ad hoc
- Gestion du cycle de vie des campagnes et du suivi influenceurs
- Exportation de données et rapports pour les décideurs

**Surfaces principales :** Toutes les surfaces, avec un focus sur la configuration (Admin Sources, Admin Catalog).

**Fréquence :** Quotidien.

**Critère de succès :** « Je configure le système en quelques minutes, et il surveille, recommande et mesure automatiquement. »

### 3.4 Persona futur : Intégrateur / Partenaire technique

**Profil :** Développeur ou ESN qui déploie RamyPulse chez un client.

**Besoins :**
- Documentation d'installation et de configuration claire
- API documentée pour le branchement de sources
- Schéma de données stable et extensible
- Options de déploiement local et Docker documentées
- Modèle d'onboarding reproductible

**Critère de succès :** « Je déploie le système en une journée et je branche les sources du client en une semaine. »

---

## 7. Positionnement du produit

### 4.1 Catégorie

Plateforme d'intelligence marketing locale pour le marché algérien.

### 4.2 Différenciation

| Dimension | RamyPulse | Solutions internationales (Brandwatch, Sprinklr) | Solutions locales artisanales (Excel, manuel) |
|-----------|-----------|--------------------------------------------------|----------------------------------------------|
| Dialecte algérien | Natif (Arabizi, arabe dialectal, français) | Non supporté | Manuel, non scalable |
| Déploiement | Local-first + mode enhanced optionnel | Cloud-only, cher | Local mais non outillé |
| Granularité géographique | Wilaya, zone de livraison, point de vente | Pays ou région large | Variable, souvent absent |
| ABSA sur aspects métier | 5 aspects natifs, extensibles | Générique | Absent |
| Intelligence marché | Market Radar, veille concurrentielle | Incluse mais non localisée | Absente |
| Mesure campagne | Campaign Lab, before/during/after, influenceurs | Partielle | Absente ou manuelle |
| Recommandations | Moteur structuré (règles + enhanced LLM) | Tableaux de bord passifs | Absentes |
| Coût | Licence locale, pas d'abonnement cloud obligatoire | 500-5000€/mois | Temps humain élevé |
| Conformité données | Données restent en local | Données chez le fournisseur | Données fragmentées |

### 4.3 Proposition de valeur

RamyPulse est le seul système capable :
1. D'analyser automatiquement les retours en dialecte algérien
2. De surveiller proactivement les signaux par produit et par wilaya
3. De mesurer l'impact réel des campagnes marketing et influenceurs
4. De recommander des actions concrètes, priorisées et traçables
5. De comparer le positionnement marque vs concurrence

Le tout en local, avec un mode enhanced optionnel pour les synthèses avancées.

### 4.4 Positionnement concurrentiel

Le marché n'a aucun concurrent direct pour cette combinaison :
- Expertise linguistique dialecte algérien
- Local-first / souveraineté des données
- Granularité géographique algérienne (58 wilayas)
- ABSA métier spécifique agroalimentaire
- Recommandation + mesure de campagne intégrées

---

## 8. État actuel du projet et limites actuelles

### 5.1 Ce qui existe et fonctionne

Le codebase contient 53 fichiers Python, environ 7 946 lignes (production + tests), avec 309 tests unitaires passant à 100%.

| Composant | Statut | Qualité |
|-----------|--------|---------|
| **Normalisation texte** — Arabizi → arabe, tri-script, 27 entrées lexique, digrams, graphèmes | Fonctionnel | Production-ready |
| **Extraction d'aspects** — Dictionnaire bilingue, 5 aspects, ~50 mots-clés, regex compilé | Fonctionnel | Production-ready |
| **Calcul NSS** — Formule correcte, gestion zero-division, NaN, weekly trends | Fonctionnel | Production-ready |
| **Simulation What-If** — 3 scénarios (neutraliser/améliorer/dégrader), immutabilité, saturation | Fonctionnel | Production-ready |
| **Recherche hybride RAG** — FAISS HNSW (M=32) + BM25Okapi + RRF fusion | Fonctionnel | Production-ready |
| **Embedder E5** — multilingual-e5-base (768 dims), lazy-loading singleton, prefixes corrects | Fonctionnel | Production-ready |
| **Dashboard Streamlit** — 4 pages (Dashboard, Explorer, Chat, What-If), filtres, Plotly | Fonctionnel | Production-ready |
| **Pipeline scripts** — 01→05, bout en bout, fallback chain | Fonctionnel | Production-ready |
| **Config centralisée** — config.py, env vars, constantes, paths auto-créés | Fonctionnel | Production-ready |
| **Suite de tests** — 309 tests, mocking complet, exécutable sans modèles | Fonctionnel | Excellent |

### 5.2 Ce qui existe mais est partiel ou défaillant

| Composant | Problème | Impact |
|-----------|----------|--------|
| **Classification sentiment (DziriBERT)** | Le modèle n'est PAS fine-tuné. Charge les poids pré-entraînés avec `ignore_mismatched_sizes=True`. Classification essentiellement aléatoire. Fallback heuristique : 19 mots-clés. | **CRITIQUE** — Tout NSS, tendance, ABSA repose sur un classifieur non entraîné |
| **Génération RAG (Ollama)** | Garde-fous anti-hallucination faibles : prompt-only, pas de validation factuelle, JSON parsing fragile (ne gère pas le markdown-wrapped) | **MAJEUR** — Le chat peut inventer des réponses non fondées |
| **FAISS vector store** | Reconstruction COMPLÈTE de l'index HNSW à chaque `add()` | **MAJEUR** — Ne scale pas au-delà de ~50k vecteurs |
| **Embedder E5** | Pas de batching (OOM sur gros corpus), dépendance sentence-transformers fragile | **MODÉRÉ** — Limite la taille du corpus indexable |
| **ABSA Engine** | Pas d'error handling, pas de validation input, pas de logging, pas de batching | **MODÉRÉ** — Fragilité en conditions réelles |

### 5.3 Ce qui n'existe pas du tout

| Composant manquant | Impact |
|--------------------|--------|
| Scrapers / collecteurs (Facebook, Google Maps, YouTube) | Pas d'ingestion automatique |
| Pipeline audio (Whisper) | Canal audio non exploitable |
| Registre de sources | Pas de gestion structurée des sources |
| Dimensions métier enrichies (wilaya, produit, gamme, concurrent, campagne) | Schéma Parquet limité à 7 colonnes |
| Watchlists configurables | Pas de surveillance proactive |
| Moteur d'alertes | Pas de détection d'anomalies |
| Veille concurrentielle / Market Radar | Pas de suivi des concurrents |
| Suivi de campagnes / Campaign Lab | Pas de mesure d'activation |
| Moteur de recommandations / Recommendation Desk | Pas de suggestion d'action |
| Suivi influenceurs | Pas de mesure des partenariats |
| Framework d'évaluation ML | Aucune métrique qualité (accuracy, F1) |
| CI/CD, Docker, monitoring | Pas d'industrialisation |

### 5.4 Évaluation globale (issue de l'audit)

| Catégorie | Score | Commentaire |
|-----------|-------|-------------|
| Qualité de code | 7/10 | Architecture propre, bonne séparation, docstrings français |
| Couverture de tests | 8/10 | Mocking complet, 309 tests, tous passent sans modèles réels |
| Fonctionnalité | 5/10 | Le cœur ML (sentiment) est du scaffolding ; collecteurs absents |
| Prêt pour la production | 3/10 | Pas de modèle fine-tuné, pas d'ingestion, pas de CI/CD |
| Architecture | 7/10 | Pipeline propre, bons fallbacks, mais patterns de scale manquants |

### 5.5 Diagnostic

Le projet est un prototype bien architecturé avec une infrastructure solide. Le cœur de la proposition de valeur — la classification de sentiment en dialecte algérien — n'est pas fonctionnel en production. Le système tourne grâce aux fallbacks et données mock.

**Conséquence :** La Phase 0 consolide le socle **en même temps** qu'elle pose les fondations de la plateforme cible. On ne stabilise pas d'abord pour empiler ensuite — on fait les deux en parallèle.

---

## 9. Vision cible post-Wave 4

### 6.1 Transformation visée

**Aujourd'hui :** Un prototype local d'analyse ABSA avec dashboard, RAG et What-If, fonctionnant sur données mock.

**Cible :** Une plateforme d'intelligence marketing locale et opérationnelle, organisée en 5 modules (Listen, Understand, Monitor, Recommend, Measure), exposée via 4 nouvelles surfaces (Market Radar, Watch Center, Campaign Lab, Recommendation Desk), avec un cœur local-first et un mode enhanced optionnel.

### 6.2 Les 5 modules — Vue complète

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MODULES RAMYPULSE                          │
│                                                                     │
│  ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐  ┌────────┐│
│  │ LISTEN  │→ │ UNDERSTAND│→ │ MONITOR │→ │RECOMMEND │  │MEASURE ││
│  │         │  │           │  │         │  │          │  │        ││
│  │Collecte │  │ABSA       │  │Watchlist│  │Détection │  │Campaign││
│  │Normalis.│  │NSS        │  │Alertes  │  │Qualific. │  │Lab     ││
│  │Classif. │  │Explorer   │  │Watch    │  │Contexte  │  │Influen.││
│  │Registre │  │RAG        │  │Center   │  │Génération│  │B/D/A   ││
│  │Sources  │  │What-If    │  │Market   │  │Scoring   │  │Rapport ││
│  │Entity   │  │Tendances  │  │Radar    │  │Validation│  │Attrib. ││
│  │Resolut. │  │Segment.   │  │         │  │Reco Desk │  │        ││
│  └─────────┘  └───────────┘  └─────────┘  └──────────┘  └────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 Les 6 couches d'architecture

Conformément au document de vision, enrichi par la séparation Listen Pipeline / Business Catalog :

| Couche | Rôle | Composants |
|--------|------|------------|
| **1. Listen Pipeline** | Collecte, normalisation, classification multi-sources | Normalizer, Sentiment Classifier, Import Engine, API Connectors, Audio Pipeline |
| **2. Source Registry** | Inventaire des sources : pages, comptes, fiches, vidéos, datasets importés, comptes influenceurs | Table source_registry, sync scheduler |
| **3. Business Catalog & Entity Resolution** | Catalogue métier (produits, wilayas, concurrents) + mapping vers entités métier | Dictionnaires, règles, fuzzy matching, métadonnées source |
| **4. Signal Engine** | Calculs : NSS, volumes, variations, anomalies, événements émergents | Stats locales (pandas/numpy), z-score, moving average |
| **5. Retrieval Context Layer** | Contexte pour RAG et recommandations : extraits source, top preuves, signaux récents, historique, contexte campagne | FAISS + BM25, metadata enrichi |
| **6. Recommendation Layer** | Fusion : règles + analytics + retrieval + LLM (optionnel) | Moteur de règles local + LLM enhanced optionnel |

### 6.4 Les 4 surfaces produit cibles

1. **Market Radar** — Vue globale : marque, concurrents, thèmes marché, nouveaux produits, buzz en cours, part de voix. Surface d'intelligence marché complète.

2. **Watch Center** — Centre de surveillance : watchlists actives, alertes récentes, signaux en dégradation et en amélioration. Le point d'entrée proactif du produit.

3. **Campaign Lab** — Pilotage des activations : création d'un événement, suivi en cours, comparaison avant/pendant/après, suivi influenceurs, rapport final. La surface de mesure d'impact.

4. **Recommendation Desk** — Boîte à recommandations : priorités d'action, options proposées, justification avec preuves, export rapport. La surface d'aide à la décision.

### 6.5 Principes de conception

1. **Stabiliser le socle ET construire la plateforme cible.** Les deux en parallèle, pas séquentiellement.
2. **Chaque module a une valeur autonome.** Monitor apporte de la valeur sans Recommend. Measure apporte de la valeur sans Monitor.
3. **Local-first pour le cœur, enhanced pour les synthèses.** Le mode enhanced est un multiplicateur de valeur, pas un pré-requis.
4. **Data-in avant features-out.** L'ingestion de données réelles est un pré-requis transversal.
5. **Évolutivité du schéma.** Les nouvelles dimensions s'ajoutent sans casser le cœur existant.
6. **Les 5 modules sont tous dans la cible.**

### 6.6 Arbitrages stratégiques

| Question | Décision | Justification |
|----------|----------|---------------|
| Recommend Engine : quand ? | **Phase 2 (règles), Phase 3 (enhanced LLM)** | Le moteur de règles est local-first et apporte de la valeur dès que Monitor détecte des signaux. Le LLM enhanced arrive ensuite. |
| Influencer tracking : core ou premium ? | **Core du module Measure, arrivant Phase 3** | Fait partie intégrante du Campaign Lab. Le suivi influenceurs est une mesure d'activation marketing, pas un luxe. Simplifié en Phase 3 (import), automatisé en Phase 4 (APIs). |
| Market Radar : surface complète ou enrichissement dashboard ? | **Surface produit complète, Phase 2** | L'intelligence marché est un module constitutif, pas un filtre ajouté au dashboard existant. |
| Local-first : plafond absolu ou principe de base ? | **Principe de base avec mode enhanced optionnel** | Le cœur (classification, NSS, alertes, FAISS, What-If) est 100% local. Le mode enhanced (LLM cloud pour synthèses, recommandations, rapports) est un multiplicateur activable par config. Jamais obligatoire. |
| Recommendation Desk dans le MVP ? | **Version règles en Phase 2, version enhanced en Phase 3** | Les recommandations par règles attachées aux alertes sont immédiatement utiles. Pas besoin d'attendre un LLM pour apporter de la valeur. |
| Tonalité produit ? | **On stabilise le socle ET on construit la plateforme cible** | Pas « on stabilise d'abord ». Le fine-tuning DziriBERT et la construction de l'infrastructure (registre, catalogue, entités) se font en parallèle. |
| Fine-tuning DziriBERT : bloquant ? | **Oui pour la qualité, non pour l'infrastructure** | Phase 0 lance le fine-tuning en priorité. Mais l'infrastructure (source registry, catalogue, schéma) avance en parallèle — elle ne dépend pas du classifieur. |

---

## 10. Modules fonctionnels

### 7.1 Module Listen — Collecte, normalisation, registre de sources

**Objectif :** Collecter, normaliser, classifier et résoudre les entités des retours consommateurs multi-sources en continu.

#### 7.1.1 Sous-composants

| Composant | Description | Statut |
|-----------|-------------|--------|
| **Normalizer** | Normalisation tri-script (Arabizi, arabe, français). Dual-script, 27 entrées, digrams, graphèmes. | ✅ Existant, production-ready |
| **Aspect Extractor** | Extraction bilingue par dictionnaires (~50 mots-clés, 5 aspects). Regex compilé, word boundaries. | ✅ Existant, à enrichir (~150 mots-clés cible) |
| **Sentiment Classifier** | DziriBERT fine-tuné sur 5 classes. Chaîne de fallback : DziriBERT → Ollama → heuristique. | ⚠️ Existant mais NON fine-tuné — PRIORITÉ #1 |
| **Source Registry** | Table SQLite des sources surveillées. CRUD, sync tracking, owner_type. | ❌ À construire Phase 1 |
| **Import Engine** | Ingestion CSV/Parquet/Excel avec validation, normalisation, déduplication. | ❌ À construire Phase 1 |
| **API Connectors** | Meta Pages, Instagram Business, Google Business Profile, YouTube Data API. | ❌ À construire Phase 3-4 |
| **Public Signal Collector** | Collecte publique ciblée pour veille concurrentielle. | ❌ À construire Phase 4 |
| **Audio Pipeline** | Transcription Whisper pour contenus audio/vidéo. | ❌ À construire Phase 3 |
| **Entity Resolver** | Attribution marque/produit/gamme/wilaya/concurrent à chaque mention. | ❌ À construire Phase 1 |

#### 7.1.2 Fine-tuning DziriBERT — Plan d'action

Le fine-tuning est la priorité #1 de Phase 0.

1. **Dataset d'entraînement** — Minimum 3 000 exemples annotés manuellement en 5 classes, représentatifs du dialecte algérien. Répartition équilibrée. Sources : Facebook, Google Maps, forums, SAV.

2. **Procédure** — Fine-tuning supervisé (classification head 5 classes). Local, pas de cloud. Les hyper-paramètres de référence sont documentés dans le document technique séparé (`docs/FINETUNING_DZIRIBERT_TECHNIQUE.md`).

3. **Évaluation** — Split test 20%. Métriques : F1 macro ≥ 0.70 (MVP), accuracy, F1 par classe, matrice de confusion. Inter-annotator agreement ≥ 0.65 (Cohen's kappa).

4. **Fallback conservé** — La chaîne DziriBERT → Ollama → heuristique reste. Mais DziriBERT fine-tuné doit être le chemin principal.

5. **Itération** — Enrichissement continu par active learning sur les données de production.

**Alternatives si DziriBERT ne converge pas :** CAMeLBERT, MarBERT, ArabBERT. Augmenter le dataset.

**Effort estimé :** 2-3 semaines (annotation 1 sem, fine-tuning + évaluation 1 sem, intégration 1 sem).

#### 7.1.3 Entity Resolution — Approche par étapes

**Phase 1 — Dictionnaires et règles (Foundation)**
- Liste des 58 wilayas + variantes Arabizi/dialectales
- Catalogue produits client (marques, gammes, SKU) avec variantes dialectales
- Matching exact + fuzzy (Levenshtein, phonétique)
- Enrichissement par métadonnées source (fiche Google Maps → wilaya, page Facebook → marque)
- Priorité : marque > gamme > produit > SKU (du plus fiable au plus granulaire)

**Phase 2 — Extraction contextuelle**
- Heuristiques contextuelles par type de source
- Enrichissement cross-source (même auteur, même thread)

**Phase 3+ — NER fine-tuné (optionnel)**
- Justifié uniquement si dictionnaires insuffisants
- Fine-tuning sur entités algériennes spécifiques

**Règle :** On ne bloque PAS l'infrastructure sur le NER. Les dictionnaires + métadonnées couvrent 80% des cas.

### 7.2 Module Understand — ABSA, NSS, exploration, RAG, What-If

**Objectif :** Fournir une compréhension approfondie des retours consommateurs via analyse, segmentation, exploration et interrogation.

#### 7.2.1 Sous-composants

| Composant | Description | Statut |
|-----------|-------------|--------|
| **ABSA Engine** | Pipeline sentiment + aspect. Sentence-level. | ✅ Existant, à fiabiliser |
| **NSS Calculator** | NSS global et par dimensions. Zero-division safe, NaN handling, weekly trends. | ✅ Existant, production-ready |
| **Dashboard** | KPIs globaux, heatmap, tendances Plotly. | ✅ Existant, à enrichir (filtres métier, Market Radar) |
| **Explorer** | Exploration détaillée avec filtres, pagination, badges. | ✅ Existant, à enrichir (colonnes métier) |
| **RAG Chat** | Q&A hybride FAISS+BM25+RRF, Ollama/demo, citations. | ✅ Existant, garde-fous à renforcer |
| **What-If Simulator** | 3 scénarios, immutabilité, saturation, structured output. | ✅ Existant, production-ready |
| **Segmentation** | Croisement produit × wilaya × canal × aspect × période. | ❌ Phase 2 |
| **Comparaison concurrentielle** | NSS marque vs concurrents, part de voix. | ❌ Phase 2 (Market Radar) |
| **Trend Detection** | Tendances émergentes, signaux faibles, nouveaux thèmes. | ❌ Phase 2 |

#### 7.2.2 Enrichissement Dashboard et Market Radar

Le dashboard existant évolue vers deux surfaces complémentaires :

**Dashboard enrichi (Phase 1-2) :**
- Filtres métier : produit, gamme, wilaya, canal, campagne, concurrent
- Vue temporelle avancée : annotations campagne sur les courbes
- Cartes géographiques NSS par wilaya (si données disponibles)

**Market Radar (Phase 2) — Surface produit complète :**
- Vue marque : NSS global, tendances, top signaux
- Vue concurrents : NSS comparé, part de voix, thèmes émergents
- Vue marché : thèmes dominants, buzz en cours, nouveaux produits
- Vue géographique : heatmap par wilaya, comparaison régionale
- KPIs clés : part de voix, part de voix positive, vitesse de propagation des signaux

#### 7.2.3 Renforcement RAG

| Amélioration | Phase | Description |
|-------------|-------|-------------|
| JSON parsing robuste | Phase 0 | Gérer markdown-wrapped JSON (`\`\`\`json {...}\`\`\``) |
| Retry logic | Phase 0 | Retry avec backoff si Ollama temporairement indisponible |
| Validation factuelle | Phase 1 | Overlap sémantique entre réponse et chunks retrouvés |
| Confidence calibrée | Phase 1 | Score basé sur similarité des chunks, pas self-confidence LLM |
| Context window | Phase 1 | Limiter et tronquer proprement le contexte injecté |
| Metadata enrichi | Phase 2 | Chunks avec wilaya, produit, campagne pour filtrage post-retrieval |
| RAG conversationnel | Phase 3 | Historique de conversation multi-tours |
| RAG + Monitor | Phase 2 | Réponse contextualisée avec alertes et watchlists |
| RAG + Campaign | Phase 3 | Réponse sur les résultats de campagne |
| Mode Enhanced | Phase 2 | LLM cloud optionnel pour synthèses RAG avancées |

### 7.3 Module Monitor — Watchlists, alertes, Watch Center

**Objectif :** Détecter proactivement les signaux nécessitant une attention, sans attendre qu'un utilisateur pose la question.

#### 7.3.1 Sous-composants

| Composant | Description | Phase |
|-----------|-------------|-------|
| **Watchlist Engine** | Création, gestion, évaluation de watchlists configurables | Phase 2 |
| **Alert Engine** | Moteur de règles + détection statistique d'anomalies | Phase 2 |
| **Watch Center** (UI) | Surface Streamlit : watchlists actives, alertes, signaux | Phase 2 |
| **Market Radar** (UI) | Surface Streamlit : marque vs concurrents, thèmes marché | Phase 2 |
| **Notification Engine** | Delivery : in-app, email optionnel, webhook optionnel | Phase 2 (in-app), Phase 3 (email/webhook) |
| **Pattern Detector** | Anomalies temporelles, concentration géo, divergence canaux, thèmes émergents | Phase 3 |

**Détail en section 11.**

### 7.4 Module Recommend — Recommandations d'action

**Objectif :** Transformer les signaux détectés en propositions d'action concrètes, priorisées et traçables.

**Position stratégique :** Le Recommend Engine est une brique constitutive. Il arrive dès Phase 2 en mode règles, et s'enrichit en Phase 3 avec le mode enhanced.

#### 7.4.1 Pipeline en 6 étapes

```
1. Détection       → Un signal est identifié (alerte, anomalie, tendance)
2. Qualification   → Le signal est évalué : volume, delta, confiance
3. Contexte        → Retrieval du contexte pertinent : historique, campagnes, signaux adjacents
4. Génération      → Production de pistes d'action (règles locales OU règles + LLM)
5. Scoring         → Priorité, urgence, confiance calculés
6. Validation      → L'humain valide, rejette ou ajuste
```

#### 7.4.2 Sous-composants

| Composant | Description | Phase |
|-----------|-------------|-------|
| **Rule-based Recommender** | Recommandations structurées par règles métier explicites | Phase 2 |
| **Context Assembler** | Assemblage du contexte (signaux, historique, campagnes actives) | Phase 2 |
| **Recommendation Desk** (UI) — version règles | Interface de visualisation et validation des recommandations | Phase 2 |
| **LLM Recommender** (enhanced) | Enrichissement via LLM cloud : résumé narratif, actions nuancées, raisonnement multi-facteurs | Phase 3 |
| **Recommendation Desk** (UI) — version enhanced | Interface enrichie avec synthèses LLM, comparaisons, export rapport | Phase 3 |

**Détail en section 12.**

### 7.5 Module Measure — Campaign Lab, influenceurs, mesure d'impact

**Objectif :** Mesurer l'impact des actions marketing (campagnes, activations, influenceurs) sur la perception consommateur.

**Position stratégique :** Le Campaign Lab et le suivi influenceurs sont des briques constitutives. L'influencer tracking fait partie du module Measure.

#### 7.5.1 Sous-composants

| Composant | Description | Phase |
|-----------|-------------|-------|
| **Campaign Registry** | Objet Campaign/Event avec métadonnées (dates, produits, wilayas, hashtags, influenceurs) | Phase 3 |
| **Before/During/After Engine** | Calcul automatique des métriques sur 3 fenêtres temporelles | Phase 3 |
| **Campaign Lab** (UI) | Création, suivi en cours, analyse B/D/A, comparaison de campagnes | Phase 3 |
| **Influencer Tracker** | Profils créateurs, posts suivis, hashtags, métriques d'engagement | Phase 3 (import) → Phase 4 (automatisé) |
| **Campaign Report Generator** | Rapport structuré : résumé, métriques, graphiques, top mentions, disclaimer | Phase 3 (template) → Phase 3 (enhanced LLM) |
| **Attribution Engine** | Niveaux de confiance, facteurs confondants, garde-fous corrélation/causalité | Phase 3 |

**Détail en section 13.**

---

## 11. Architecture logique

### 8.1 Vue d'ensemble — 5 couches

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        COUCHE PRÉSENTATION                              │
│  Dashboard │ Explorer │ RAG Chat │ What-If │ Watch Center │             │
│  Market Radar │ Campaign Lab │ Recommendation Desk │                    │
│  Admin Sources │ Admin Catalog                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                       COUCHE APPLICATION                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │  Listen   │ │Understand│ │ Monitor  │ │Recommend │ │ Measure  │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
├─────────────────────────────────────────────────────────────────────────┤
│                  COUCHE 5 — RECOMMENDATION LAYER                        │
│  Rule Engine │ Context Assembler │ LLM Recommender (enhanced) │         │
│  Scoring │ Attribution Engine                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                  COUCHE 4 — RETRIEVAL CONTEXT LAYER                     │
│  FAISS Index │ BM25 Index │ Metadata Store │ Chunk Manager │            │
│  RAG Generator (Ollama local / LLM enhanced)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                  COUCHE 3 — SIGNAL ENGINE                               │
│  NSS Calculator │ Trend Detector │ Anomaly Detector │ Volume Tracker │  │
│  Alert Engine │ Watchlist Evaluator │ Pattern Detector                   │
├─────────────────────────────────────────────────────────────────────────┤
│                  COUCHE 2 — ENTITY RESOLUTION                           │
│  Business Catalog (products, wilayas, competitors) │                    │
│  Dictionary Matcher │ Fuzzy Matcher │ Source Metadata Enricher           │
├─────────────────────────────────────────────────────────────────────────┤
│                  COUCHE 1 — SOURCE REGISTRY                             │
│  Source Registry │ Import Engine │ API Connectors │                      │
│  Public Signal Collector │ Audio Pipeline │ Sync Scheduler               │
├─────────────────────────────────────────────────────────────────────────┤
│                  COUCHE STOCKAGE                                         │
│  Parquet (mentions enrichies) │ SQLite (objets métier, config) │        │
│  FAISS Binary │ BM25 Pickle │ JSON/YAML Config                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Choix de stockage

| Besoin | Solution | Justification |
|--------|----------|---------------|
| Données analytiques (mentions, sentiments) | **Parquet** (maintenu) | Standard du projet, compatible pandas, efficient pour agrégations |
| Index sémantique | **FAISS** (maintenu, fix du rebuild) | En place, performant en local, HNSW M=32 |
| Index lexical | **BM25** (maintenu) | Complémentaire à FAISS pour le RAG hybride (RRF) |
| Objets métier (sources, watchlists, campagnes, recommandations) | **SQLite** (nouveau) | Léger, local, transactionnel, CRUD métier, fichier unique |
| Configuration statique | **JSON / YAML** | Catalogue produits, liste wilayas, règles de recommandation |
| Logs et audit | **SQLite** (table dédiée) | Traçabilité alertes, notifications, actions |

**Pourquoi SQLite pour les objets métier ?** Parquet est pour les lectures analytiques massives. Les watchlists, campagnes et recommandations nécessitent du CRUD transactionnel, des requêtes par clé et des relations. SQLite est local, léger, transactionnel — cohérent avec le local-first.

### 8.3 Flux de données principal

```
Sources (API / import / collecte publique)
    │
    ▼
Normalizer → Sentiment Classifier → Aspect Extractor → Entity Resolver
    │
    ▼
Parquet enrichi (text, sentiment_label, channel, aspect, confidence,
                  brand, product, product_line, wilaya, competitor,
                  source_registry_id, campaign_id, creator_id, ...)
    │
    ├──▶ Signal Engine ──▶ Alert Engine ──▶ Recommendation Engine
    │                           │                    │
    │                           ▼                    ▼
    │                      Watch Center        Recommendation Desk
    │
    ├──▶ Dashboard / Explorer / What-If / Market Radar
    │
    ├──▶ Embedder → FAISS + BM25 → RAG Chat
    │
    └──▶ Campaign Engine (before/during/after) → Campaign Lab → Report
```

### 8.4 Isolation Mode Local vs Mode Enhanced

| Composant | Mode Local (Core) | Mode Enhanced (optionnel) | Config flag |
|-----------|-------------------|---------------------------|-------------|
| Sentiment Classifier | DziriBERT fine-tuné local | — | — |
| NSS + Stats | pandas/numpy local | — | — |
| Aspect Extraction | Dictionnaires + regex local | — | — |
| FAISS + BM25 | Local (434MB model E5) | — | — |
| What-If | Simulation locale | — | — |
| RAG Generator | Ollama (llama3.2:3b) | LLM cloud (Claude, GPT-4, Mistral) | `ENHANCED_RAG=True` |
| Recommender | Règles + templates | LLM cloud multi-facteurs | `ENHANCED_RECOMMEND=True` |
| Report Generator | Templates + métriques | LLM cloud synthèse narrative | `ENHANCED_REPORTS=True` |
| Notifications | In-app | Email (SMTP), webhook | `EMAIL_ENABLED`, `WEBHOOK_ENABLED` |
| API Connectors | Import fichier | Meta, Google, YouTube APIs | `API_CONNECTORS_ENABLED=True` |

**Règle fondamentale :** Tout composant marqué « Core » fonctionne sans aucune connexion internet après le setup initial. Le mode enhanced est un multiplicateur activable par configuration, jamais un pré-requis.

---

## 12. Modèle de données

### 9.1 Schéma actuel (Wave 4)

```
mentions (Parquet)
├── text: str                  # Texte normalisé
├── sentiment_label: str       # {très_positif, positif, neutre, négatif, très_négatif}
├── channel: str               # {facebook, google_maps, youtube, sav}
├── aspect: str                # {goût, emballage, prix, disponibilité, fraîcheur}
├── source_url: str            # URL d'origine
├── timestamp: datetime        # Date de la mention
└── confidence: float          # Score de confiance du classifieur
```

### 9.2 Schéma cible — Parquet enrichi

Enrichissement par **ajout** de colonnes, sans modification des existantes. Rétro-compatibilité garantie.

```
mentions (Parquet enrichi)
├── text: str                       # Texte normalisé [existant]
├── text_original: str              # Texte brut avant normalisation [nouveau]
├── sentiment_label: str            # 5 classes discrètes [existant]
├── channel: str                    # Canal source [existant]
├── aspect: str | list[str]         # Aspect(s) détecté(s) [existant, type évolue]
├── aspect_sentiments: dict         # Sentiment par aspect {aspect: label} [nouveau]
├── source_url: str                 # URL d'origine [existant]
├── timestamp: datetime             # Date de la mention [existant]
├── confidence: float               # Score de confiance [existant]
├── script_detected: str            # {arabizi, arabic, french, mixed} [nouveau]
├── language: str                   # Langue détectée [nouveau]
├── source_registry_id: str         # FK vers source_registry [nouveau]
├── brand: str                      # Marque identifiée [nouveau]
├── competitor: str                 # Concurrent identifié [nouveau]
├── product: str                    # Produit identifié [nouveau]
├── product_line: str               # Gamme [nouveau]
├── sku: str                        # SKU si identifiable [nouveau]
├── wilaya: str                     # Wilaya attribuée [nouveau]
├── delivery_zone: str              # Zone de livraison [nouveau]
├── store_type: str                 # Type de point de vente [nouveau]
├── campaign_id: str                # FK vers campaign [nouveau]
├── event_id: str                   # FK vers event [nouveau]
├── creator_id: str                 # FK vers creator/influencer [nouveau]
├── market_segment: str             # Segment de marché [nouveau]
└── ingestion_batch_id: str         # ID du lot d'ingestion [nouveau]
```

### 9.3 Schéma cible — Tables SQLite

#### 9.3.1 source_registry

```sql
CREATE TABLE source_registry (
    source_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,           -- facebook, instagram, google_maps, youtube, sav, import
    source_type TEXT NOT NULL,        -- facebook_page, instagram_business, google_business_location,
                                     -- youtube_channel, youtube_video, imported_dataset,
                                     -- internal_export, public_page
    display_name TEXT NOT NULL,
    external_id TEXT,                 -- ID sur la plateforme externe
    url TEXT,
    owner_type TEXT NOT NULL,         -- owned, competitor, market
    auth_mode TEXT,                   -- oauth, api_key, import, public
    brand TEXT,                       -- Marque associée
    is_active BOOLEAN DEFAULT TRUE,
    sync_frequency TEXT,              -- daily, weekly, on_demand
    last_sync_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);
```

#### 9.3.2 products

```sql
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    product_line TEXT,
    product_name TEXT NOT NULL,
    sku TEXT,
    category TEXT,                    -- jus, eau, lait, soda
    keywords_ar TEXT,                 -- Mots-clés arabe (JSON array)
    keywords_arabizi TEXT,            -- Mots-clés Arabizi (JSON array)
    keywords_fr TEXT,                 -- Mots-clés français (JSON array)
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 9.3.3 wilayas

```sql
CREATE TABLE wilayas (
    wilaya_code TEXT PRIMARY KEY,     -- Code officiel (01-58)
    wilaya_name_fr TEXT NOT NULL,
    wilaya_name_ar TEXT NOT NULL,
    keywords_arabizi TEXT,            -- Variantes Arabizi (JSON array)
    region TEXT                       -- Est, Ouest, Centre, Sud
);
```

#### 9.3.4 competitors

```sql
CREATE TABLE competitors (
    competitor_id TEXT PRIMARY KEY,
    brand_name TEXT NOT NULL,
    category TEXT,
    keywords_ar TEXT,                 -- JSON array
    keywords_arabizi TEXT,            -- JSON array
    keywords_fr TEXT,                 -- JSON array
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 9.3.5 watchlists

```sql
CREATE TABLE watchlists (
    watchlist_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    scope_type TEXT NOT NULL,         -- brand, product, competitor, market, geographic
    products TEXT,                    -- JSON array of product_ids
    competitors TEXT,                 -- JSON array of competitor_ids
    wilayas TEXT,                     -- JSON array of wilaya_codes
    channels TEXT,                    -- JSON array of channels
    aspects TEXT,                     -- JSON array of aspects
    keywords TEXT,                    -- JSON array de mots-clés additionnels
    source_registry_ids TEXT,         -- JSON array de source_ids
    metric_type TEXT NOT NULL,        -- nss, volume, negative_ratio, positive_ratio, share_of_voice
    baseline_window INTEGER DEFAULT 30, -- Jours pour la baseline
    alert_threshold REAL,            -- Seuil de déclenchement
    alert_direction TEXT,            -- drop, rise, both
    owner TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);
```

#### 9.3.6 campaigns

```sql
CREATE TABLE campaigns (
    campaign_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    event_type TEXT NOT NULL,         -- campaign, activation, launch, sponsoring, promotion
    brand TEXT NOT NULL,
    products TEXT,                    -- JSON array of product_ids
    wilayas TEXT,                     -- JSON array of wilaya_codes
    channels TEXT,                    -- JSON array
    start_at DATETIME NOT NULL,
    end_at DATETIME,
    goal TEXT,
    budget REAL,
    hashtags TEXT,                    -- JSON array
    keywords TEXT,                    -- JSON array
    tracked_accounts TEXT,            -- JSON array
    tracked_posts TEXT,               -- JSON array
    tracked_urls TEXT,                -- JSON array
    creator_profiles TEXT,            -- JSON array of creator_ids
    before_window INTEGER DEFAULT 30, -- Jours avant start_at pour la baseline
    after_window INTEGER DEFAULT 14,  -- Jours après end_at pour le suivi retombées
    status TEXT DEFAULT 'draft',      -- draft, active, completed, cancelled
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);
```

#### 9.3.7 alerts

```sql
CREATE TABLE alerts (
    alert_id TEXT PRIMARY KEY,
    watchlist_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,         -- threshold_breach, anomaly, trend_change, volume_spike,
                                     -- channel_divergence, geographic_concentration, emerging_theme
    severity TEXT NOT NULL,           -- critical, warning, info
    title TEXT NOT NULL,
    description TEXT,
    metric_name TEXT,
    metric_value REAL,
    baseline_value REAL,
    delta REAL,
    evidence TEXT,                    -- JSON: top mentions, preuves
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by TEXT,
    acknowledged_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(watchlist_id)
);
```

#### 9.3.8 recommendations

```sql
CREATE TABLE recommendations (
    recommendation_id TEXT PRIMARY KEY,
    alert_id TEXT,                     -- FK vers l'alerte source (peut être NULL pour reco proactive)
    signal_type TEXT NOT NULL,         -- alert, anomaly, trend, campaign_result
    problem TEXT NOT NULL,             -- Problème observé, en une phrase
    evidence_summary TEXT,             -- Preuves résumées
    urgency TEXT NOT NULL,             -- high, medium, low
    actions TEXT NOT NULL,             -- JSON array d'options d'action
    assumptions TEXT,                  -- JSON array d'hypothèses
    risks TEXT,                        -- JSON array de risques
    confidence TEXT NOT NULL,          -- high, medium, low
    generation_mode TEXT NOT NULL,     -- rules, enhanced
    requires_human_validation BOOLEAN DEFAULT TRUE,
    is_validated BOOLEAN DEFAULT FALSE,
    validated_by TEXT,
    validated_at DATETIME,
    feedback TEXT,                     -- Feedback utilisateur post-validation
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 9.3.9 creator_profiles

```sql
CREATE TABLE creator_profiles (
    creator_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    platform TEXT NOT NULL,           -- instagram, youtube, facebook, tiktok
    external_id TEXT,
    profile_url TEXT,
    category TEXT,                    -- food, lifestyle, family, humor
    estimated_reach TEXT,             -- micro (<10k), mid (10-100k), macro (100k-1M), mega (>1M)
    contact_info TEXT,                -- JSON (optionnel)
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 9.3.10 notifications

```sql
CREATE TABLE notifications (
    notification_id TEXT PRIMARY KEY,
    alert_id TEXT,
    recommendation_id TEXT,
    channel TEXT NOT NULL,            -- in_app, email, webhook
    recipient TEXT,
    title TEXT NOT NULL,
    body TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    delivered_at DATETIME,
    read_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 9.3.11 audit_log

```sql
CREATE TABLE audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,         -- sync, import, alert, recommendation, config_change,
                                     -- campaign_status_change, watchlist_evaluation
    source TEXT,
    details TEXT,                     -- JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 9.4 Migration

Migration en 3 étapes non-destructives :

1. **Ajout de colonnes** au Parquet existant (NULL pour les nouvelles colonnes sur données historiques)
2. **Création des tables SQLite** (ramypulse.db, créé au premier lancement)
3. **Rétro-enrichissement** optionnel des données historiques via Entity Resolver

**Garantie :** Le pipeline existant (01→05) continue de fonctionner sans modification sur les anciennes données.

---

## 13. Registre de sources, entités métier, watchlists, campagnes

### 10.1 Registre de sources

#### 10.1.1 Principes

Le registre de sources est la table de vérité de ce que le système surveille. Chaque source est un objet identifié, typé et suivi.

**Règle fondamentale :** Aucune donnée n'entre dans le système sans être rattachée à une source enregistrée. Traçabilité et filtrage garantis.

#### 10.1.2 Types de sources

| Type | Plateforme | Mode de connexion | Exemple |
|------|-----------|-------------------|---------| 
| `facebook_page` | Facebook | OAuth (Meta Business) ou import | Page Facebook Ramy |
| `instagram_business` | Instagram | OAuth (Meta Business) | Compte pro Ramy |
| `google_business_location` | Google Maps | OAuth (GBP API) ou import | Fiche GBP Ramy Bejaia |
| `youtube_channel` | YouTube | API publique (quotas) | Chaîne YouTube Ramy |
| `youtube_video` | YouTube | API publique | Vidéo spécifique |
| `imported_dataset` | Import | Fichier CSV/Parquet/Excel | Export SAV Q1 2026 |
| `internal_export` | Import | Fichier structuré | Export CRM, logistique |
| `public_page` | Web | Collecte publique ciblée | Page publique concurrent |

#### 10.1.3 Cycle de vie

```
Création → Configuration → Première sync → Sync récurrente → Désactivation (optionnel)
```

Chaque sync est horodatée (`last_sync_at`). Une source inactive arrête la collecte, mais ses données historiques restent disponibles.

#### 10.1.4 Champs détaillés

| Champ | Type | Description |
|-------|------|-------------|
| `source_id` | TEXT PK | Identifiant unique (UUID) |
| `platform` | TEXT | facebook, instagram, google_maps, youtube, sav, import |
| `source_type` | TEXT | facebook_page, instagram_business, etc. |
| `display_name` | TEXT | Nom affiché : « Page Facebook Ramy » |
| `external_id` | TEXT | ID sur la plateforme (page_id, location_id, channel_id) |
| `url` | TEXT | URL publique de la source |
| `owner_type` | TEXT | owned, competitor, market — distingue les sources propres des sources de veille |
| `auth_mode` | TEXT | oauth, api_key, import, public |
| `brand` | TEXT | Marque associée (Ramy, Hamoud...) |
| `is_active` | BOOLEAN | Active/inactive |
| `sync_frequency` | TEXT | daily, weekly, on_demand |
| `last_sync_at` | DATETIME | Dernière synchronisation réussie |

### 10.2 Catalogue métier

#### 10.2.1 Entités métier

| Entité | Rôle | Table SQLite | Exemple |
|--------|------|-------------|---------|
| **Marque** (brand) | Marque propre ou concurrente | Dans products + competitors | Ramy, Hamoud, Ifri |
| **Gamme** (product_line) | Ligne de produits | products.product_line | Jus, Eau, Premium |
| **Produit** (product) | Produit spécifique | products | Jus Citron Ramy, Eau Guedila |
| **SKU** | Référence unitaire | products.sku | Jus Citron 1L, Jus Citron 25cl |
| **Concurrent** (competitor) | Marque concurrente | competitors | Hamoud, Ngaous, Ifri |
| **Wilaya** | Division géographique | wilayas | Alger (16), Oran (31), Bejaia (06) |
| **Point de vente** | Type de distribution | dans mentions.store_type | Supermarché, épicerie, grossiste |

#### 10.2.2 Alimentation du catalogue

1. Le client fournit sa nomenclature produits (marques, gammes, produits, SKU).
2. L'analyste configure les variantes dialectales (mots-clés Arabizi, arabe, français pour chaque entité).
3. La liste des 58 wilayas est pré-chargée avec variantes dialectales.
4. Les concurrents sont ajoutés au fil du temps.

**Le catalogue est une couche de configuration alimentée à l'onboarding.** L'Entity Resolver l'utilise comme référence.

### 10.3 Watchlists — Détail

#### 10.3.1 Définition

Une watchlist n'est PAS un simple mot-clé. C'est un objet métier configurable combinant :
- Un périmètre (produits, wilayas, canaux, aspects, sources)
- Une métrique (NSS, volume, ratio négatif, part de voix)
- Une baseline (fenêtre de référence)
- Un seuil d'alerte (variation déclenchant l'alerte)

#### 10.3.2 Exemples concrets

| Watchlist | Scope | Métrique | Seuil |
|-----------|-------|----------|-------|
| « Livraison Bejaia » | wilaya=Bejaia, aspect=disponibilité | NSS | Drop > 15 pts |
| « Goût nouvelle gamme » | product_line=Premium, aspect=goût | NSS | Drop > 10 pts |
| « Emballage Facebook » | channel=facebook, aspect=emballage | Volume négatif | Rise > 50% |
| « Concurrent Hamoud » | competitor=Hamoud | Part de voix | Rise > 20% |
| « Disponibilité Alger » | wilaya=Alger, aspect=disponibilité | Ratio négatif | Rise > 30% |
| « Fraîcheur Google Maps » | channel=google_maps, aspect=fraîcheur | NSS | Drop > 12 pts |
| « Perception nouveau produit » | product=Jus Citron Vert, aspect=goût | Volume + NSS | Volume > 20 et NSS < -10 |

#### 10.3.3 Évaluation d'une watchlist

À chaque cycle de rafraîchissement :

1. **Filtrer** les mentions par le scope (produits, wilayas, canaux, aspects, période)
2. **Calculer** la métrique courante
3. **Calculer** la baseline (même métrique sur la fenêtre de référence)
4. **Calculer** le delta
5. **Comparer** au seuil → déclencher une alerte si dépassement
6. **Générer** une recommandation attachée (si module Recommend actif)

#### 10.3.4 Sorties d'une watchlist

Pour chaque watchlist active :
- Score courant
- Variation 7j / 30j
- Volume associé
- Top signaux explicatifs (mentions les plus représentatives)
- Canaux contributifs
- Wilayas contributives (si applicable)
- Résumé LLM optionnel (mode enhanced)
- Recommandation attachée (si seuil franchi)

### 10.4 Campagnes — Détail

#### 10.4.1 Types d'événements

| Type | Exemple |
|------|---------|
| `campaign` | Campagne digitale Facebook/Instagram |
| `activation` | Activation terrain (plage, événement sportif) |
| `launch` | Lancement nouveau produit |
| `sponsoring` | Partenariat influenceur |
| `promotion` | Promotion prix / distribution |

#### 10.4.2 Champs clés

| Champ | Type | Description |
|-------|------|-------------|
| `campaign_id` | TEXT PK | Identifiant unique |
| `name` | TEXT | Nom descriptif : « Lancement Jus Citron Mars 2026 » |
| `event_type` | TEXT | campaign, activation, launch, sponsoring, promotion |
| `brand` | TEXT | Marque concernée |
| `products` | JSON | Liste de product_ids |
| `wilayas` | JSON | Liste de wilaya_codes (portée géographique) |
| `channels` | JSON | Canaux surveillés |
| `start_at` / `end_at` | DATETIME | Fenêtre temporelle de la campagne |
| `goal` | TEXT | Objectif qualitatif |
| `budget` | REAL | Budget alloué |
| `hashtags` | JSON | Hashtags à suivre |
| `tracked_accounts` | JSON | Comptes à suivre (influenceurs, partenaires) |
| `creator_profiles` | JSON | Profils créateurs associés |
| `before_window` | INTEGER | Jours de baseline avant (défaut: 30) |
| `after_window` | INTEGER | Jours de suivi après (défaut: 14) |
| `status` | TEXT | draft → active → completed → cancelled |

#### 10.4.3 Cycle de vie

```
draft ──▶ active ──▶ completed ──▶ (analysé / rapporté)
                          │
                          └──▶ cancelled
```

Le passage à `active` déclenche le suivi automatique. Le passage à `completed` déclenche le calcul du rapport B/D/A.

---

## 14. Moteur d'alertes

### 11.1 Architecture

Le moteur d'alertes fonctionne en 3 couches :

```
Couche 1 : Règles déterministes (seuils configurés dans les watchlists)
    │
    ▼
Couche 2 : Détection statistique (z-score, moving average, régression linéaire)
    │
    ▼
Couche 3 : Pattern detection avancée (concentration géo, divergence canaux, thèmes émergents)
```

### 11.2 Types d'alertes (7 types)

| Type | Mécanisme | Phase |
|------|-----------|-------|
| **Threshold breach** | NSS ou volume franchit le seuil d'une watchlist | Phase 2 |
| **Trend change** | Changement de tendance sur fenêtre glissante | Phase 2 |
| **Volume spike** | Augmentation anormale du volume (positive ou négative) | Phase 2 |
| **Anomaly** | Valeur statistiquement aberrante (z-score > 2) | Phase 2 |
| **Channel divergence** | Un canal diverge significativement des autres pour une même entité | Phase 3 |
| **Geographic concentration** | Signal négatif concentré dans une wilaya | Phase 3 |
| **Emerging theme** | Nouveau sujet ou mot-clé apparaissant en volume | Phase 3 |

### 11.3 Sévérité

| Niveau | Critère | Exemple |
|--------|---------|---------|
| **Critical** | Seuil franchi de > 2× le threshold, ou volume spike > 200% | NSS livraison Oran : +20 → -30 en 1 semaine |
| **Warning** | Seuil franchi ou tendance claire | NSS goût Premium en baisse de 12 pts sur 2 semaines |
| **Info** | Signal intéressant, pas d'urgence | Part de voix Hamoud en hausse de 8% ce mois |

### 11.4 Détection statistique

#### Phase 2 — Méthodes MVP

- **Moving average comparison :** Métrique semaine courante vs moyenne mobile 4 semaines précédentes
- **Z-score simple :** Écart à la moyenne > 2σ → anomalie
- **Pente de régression linéaire :** Sur 4 semaines, pente significativement négative/positive → trend change

Ces méthodes sont calculables localement (pandas + numpy), déterministes, reproductibles, et compréhensibles.

#### Phase 3+ — Méthodes avancées

- Détection de changepoint (CUSUM, PELT)
- Isolation Forest pour anomalies multivariées
- Clustering temporel pour identifier les événements

**Arbitrage :** Statistique simple d'abord. ML pour les anomalies plus tard, si le volume de données le justifie.

### 11.5 Notification et delivery multi-canal

| Canal | Phase 2 | Phase 3+ |
|-------|---------|----------|
| In-app (centre de notifications) | ✅ | ✅ |
| Digest quotidien (page récap) | ✅ | ✅ |
| Email (SMTP configurable) | ❌ | ✅ (optionnel) |
| Webhook (intégration SI client) | ❌ | ✅ (optionnel) |

### 11.6 Fréquence d'évaluation

| Type de watchlist | Fréquence |
|-------------------|-----------|
| Standard | Quotidienne (après chaque sync de données) |
| Campagne active | Toutes les 6 heures (si données temps réel) |
| Critique | Quotidienne minimum, après chaque import |

**Implémentation :** Scheduler local (cron/script planifié). Pas de service dédié au MVP.

### 11.7 Connexion avec le moteur de recommandations

Chaque alerte de sévérité **critical** ou **warning** déclenche automatiquement le pipeline de recommandation :

```
Alerte détectée → Qualification du signal → Context assembler → Rule engine
    → Recommandation générée → Notification utilisateur (alerte + reco)
```

C'est cette connexion qui fait que Recommend arrive en Phase 2 avec Monitor, pas en Phase 4.

---

## 15. Moteur de recommandations

### 12.1 Position stratégique

Le moteur de recommandations est une **brique cible constitutive** de RamyPulse. Il n'est PAS un « nice-to-have Phase 4 lointaine ».

**Séquence de déploiement :**
- **Phase 2 :** Recommandations par règles, attachées aux alertes → Recommendation Desk v1
- **Phase 3 :** Enrichissement LLM enhanced → Recommendation Desk v2 avec synthèses et raisonnement multi-facteurs

**Justification :** Une alerte seule ne suffit pas. Le client veut une proposition d'action intelligible et exploitable. Les règles métier sont locales, déterministes, testables, et apportent de la valeur immédiate.

### 12.2 Architecture en 6 étapes

```
Étape 1 — DÉTECTION
    Signal identifié : alerte, anomalie, tendance, résultat de campagne
    │
    ▼
Étape 2 — QUALIFICATION
    Volume : suffisant ? (> 10 mentions)
    Delta : significatif ? (> seuil configuré)
    Confiance : forte, modérée, faible ?
    │
    ▼
Étape 3 — CONTEXTE
    Retrieval du contexte pertinent :
    - Historique de la watchlist (4 dernières semaines)
    - Campagnes actives sur le même périmètre
    - Signaux adjacents (mêmes produits, mêmes wilayas)
    - Top mentions explicatives (preuves)
    │
    ▼
Étape 4 — GÉNÉRATION
    ┌─ Mode Local (Core) ─────────────────────────────┐
    │ Moteur de règles métier → templates structurés   │
    │ Exemple : « Si NSS disponibilité < -20           │
    │ dans une wilaya → Vérifier distribution locale » │
    └──────────────────────────────────────────────────┘
    ┌─ Mode Enhanced (Optionnel) ─────────────────────┐
    │ Règles + LLM cloud → recommandations narratives, │
    │ raisonnement multi-facteurs, croisement campagne │
    └──────────────────────────────────────────────────┘
    │
    ▼
Étape 5 — SCORING
    Priorité : haute / moyenne / basse
    Urgence : immédiate / cette semaine / ce mois
    Confiance : haute / modérée / faible (basée sur volume + delta + clarté du signal)
    │
    ▼
Étape 6 — VALIDATION
    L'humain valide, rejette ou ajuste la recommandation.
    Feedback stocké pour améliorer les futures recommandations.
```

### 12.3 Exemples de règles métier (Phase 2)

| Signal détecté | Recommandation | Priorité |
|----------------|----------------|----------|
| NSS disponibilité < -20 dans une wilaya | « Vérifier la distribution dans [wilaya]. Contacter le distributeur local. » | Haute |
| Volume plaintes emballage > +100% | « Problème d'emballage récurrent. Escalader à la production. » | Haute |
| NSS goût en baisse sur un produit | « Vérifier la qualité du lot récent de [produit]. Planifier un audit qualité. » | Moyenne |
| Concurrent en hausse de part de voix > 20% | « Le concurrent [X] gagne en visibilité. Analyser sa stratégie récente. » | Moyenne |
| NSS global stable mais un aspect en chute | « L'aspect [X] est en dégradation. Prioriser une action ciblée. » | Moyenne |
| Campagne sans effet mesurable | « La campagne [X] n'a pas eu d'impact détectable. Revoir le ciblage ou le canal. » | Basse |
| Volume mentions positives en hausse spontanée | « Opportunité : hausse organique de [aspect] dans [wilaya]. Capitaliser avec une activation. » | Basse |
| Nouveau thème émergent détecté | « Nouveau sujet en émergence : [thème]. Surveiller l'évolution et évaluer une réponse. » | Basse |

### 12.4 Format d'une recommandation

```json
{
    "recommendation_id": "rec_20260415_001",
    "alert_id": "alert_20260415_nss_drop_oran",
    "signal_type": "threshold_breach",
    "problem": "Le NSS disponibilité Oran a chuté de 18 points en 1 semaine.",
    "evidence_summary": "32 mentions négatives sur la disponibilité à Oran cette semaine, contre 8 en moyenne. Sources principales : Facebook (60%), Google Maps (30%).",
    "urgency": "high",
    "actions": [
        "Contacter le distributeur Oran pour vérifier les niveaux de stock.",
        "Vérifier s'il y a un problème logistique spécifique à la région.",
        "Planifier une activation disponibilité sur Oran si le problème persiste > 2 semaines."
    ],
    "assumptions": [
        "Le volume de données (32 mentions) est suffisant pour un signal fiable.",
        "La baisse est spécifique à Oran, pas nationale."
    ],
    "risks": [
        "Le problème peut être temporaire (rupture ponctuelle).",
        "Le signal peut être amplifié par un seul post viral."
    ],
    "confidence": "high",
    "generation_mode": "rules",
    "requires_human_validation": true
}
```

### 12.5 Mode Local vs Mode Enhanced

| Dimension | Mode Local (Phase 2) | Mode Enhanced (Phase 3) |
|-----------|----------------------|--------------------------|
| Génération | Templates structurés remplis par les données du signal | LLM cloud génère un résumé narratif + actions nuancées |
| Raisonnement | Règles déterministes (if/then) | Raisonnement multi-facteurs (croisement signaux, campagnes, historique) |
| Contextualisation | Top mentions + métriques | RAG + historique complet + contexte campagne |
| Qualité de texte | Correct mais formulaire | Naturel et actionnable |
| Dépendance | 100% local | API cloud (Claude, GPT-4, Mistral) |
| Config | Par défaut | `ENHANCED_RECOMMEND=True` |

### 12.6 Garde-fous du moteur de recommandations

1. **Traçabilité :** Chaque recommandation pointe vers le signal source et les preuves.
2. **Formulation :** Toujours « suggestion », jamais « décision ».
3. **Validation humaine :** Les recommandations critiques nécessitent un acquittement.
4. **Confiance basée sur les données :** Volume + delta + clarté du signal, pas auto-évaluation LLM.
5. **Minimum de données :** Pas de recommandation si < 10 mentions dans le scope.
6. **Feedback loop :** Les validations/rejets utilisateur sont stockés pour calibrer les règles.

### 12.7 Recommendation Desk — Interface

**Phase 2 (règles) :**
- Liste des recommandations actives, triées par urgence
- Détail de chaque reco : problème, preuves, actions, confiance
- Boutons : valider, rejeter, ajuster
- Filtres : par module, par produit, par wilaya, par urgence

**Phase 3 (enhanced) :**
- Synthèse narrative par LLM
- Comparaison avec recommandations historiques similaires
- Rapport exportable (PDF, markdown)
- Intégration avec Campaign Lab (recommandations post-campagne)

---

## 16. Campaign intelligence et influencer tracking

### 13.1 Campaign Lab — Vue d'ensemble

Le Campaign Lab est la surface produit pour le pilotage des activations marketing. Il couvre le cycle complet :

```
Création → Suivi en cours → Analyse B/D/A → Rapport → Recommandation
```

### 13.2 Métriques de campagne

| Métrique | Calcul | Interprétation |
|----------|--------|----------------|
| **NSS delta** | NSS(during) − NSS(before) | Variation du sentiment pendant la campagne |
| **Volume delta** | Volume(during) / Volume(before) | Facteur d'amplification |
| **Aspect shift** | Distribution aspects(during) vs aspects(before) | Quels aspects ont bougé |
| **Sentiment shift** | Distribution sentiment(during) vs sentiment(before) | La perception s'est-elle améliorée ? |
| **Geographic impact** | NSS par wilaya(during) vs par wilaya(before) | Impact géographique |
| **Channel impact** | NSS par canal(during) vs canal(before) | Quel canal a le plus réagi ? |
| **Decay rate** | NSS(after) vs NSS(during) | L'effet a-t-il duré ? |
| **Share of Voice delta** | SoV(during) vs SoV(before) | Gain de visibilité marque |

### 13.3 Fenêtres temporelles

| Fenêtre | Définition | Configurable |
|---------|-----------|--------------|
| Before | 30 jours avant `start_at` (défaut) | Oui (`before_window`) |
| During | De `start_at` à `end_at` | Non (bornes de la campagne) |
| After | 14 jours après `end_at` (défaut) | Oui (`after_window`) |

### 13.4 Interface Campaign Lab

1. **Création** — Formulaire : nom, type, dates, produits, wilayas, hashtags, influenceurs, budget, objectif
2. **Vue suivi** — Dashboard temps réel pendant la campagne : métriques daily, volume, sentiment
3. **Rapport B/D/A** — Analyse before/during/after avec graphiques et métriques comparatives
4. **Comparaison** — Comparer l'efficacité de plusieurs campagnes côte à côte
5. **Rapport final** — Export structuré avec disclaimer corrélation/causalité

### 13.5 Influencer Tracking

**Position V3 :** Le suivi influenceurs fait partie intégrante du module Measure (Campaign Lab). Ce n'est PAS un « premium Phase 4 » — c'est une mesure d'activation marketing qui arrive dès Phase 3.

#### 13.5.1 Phase 3 — Suivi import (simplifié)

- Enregistrement du créateur dans `creator_profiles`
- Association à une campagne via `campaigns.creator_profiles`
- Hashtags et mots-clés associés pour filtrer les mentions
- Import manuel des données de l'influenceur (posts, engagements)
- Métriques : volume de mentions liées, sentiment des réactions

#### 13.5.2 Phase 4 — Suivi automatisé

- Connexion aux APIs (Meta Business, YouTube Data API)
- Tracking automatique des posts/reels/stories de l'influenceur
- Collecte des commentaires publics
- Métriques d'engagement observées (volume, sentiment, reach estimé)
- Corrélation temporelle entre publication et changement de sentiment

#### 13.5.3 Ce que le système mesure vs ce qu'il ne peut pas affirmer

| Le système PEUT mesurer | Le système ne peut PAS affirmer |
|-------------------------|---------------------------------|
| Volume de mentions liées à l'influenceur pendant la collaboration | L'influenceur a « causé » un changement de sentiment |
| Sentiment des réactions autour des contenus de l'influenceur | Le ROI exact de la collaboration |
| Corrélation temporelle publication → changement de perception | L'impact sur les ventes (sauf données vente fournies) |
| Comparaison avec/sans influenceur (si données suffisantes) | Que le budget influenceur est bien alloué |

### 13.6 Rapport de fin de campagne

Structure du rapport exportable :

1. **Résumé exécutif** (1 paragraphe — template local ou synthèse LLM enhanced)
2. **Métriques clés** (tableau comparatif B/D/A)
3. **Graphiques de tendance** (NSS, volume, aspect distribution)
4. **Top mentions positives et négatives** (extraits texte avec source)
5. **Impact par canal** (tableau + graphique)
6. **Impact par wilaya** (tableau + carte si données disponibles)
7. **Impact influenceur** (si applicable : métriques par créateur)
8. **Facteurs confondants** (événements externes enregistrés)
9. **Recommandations post-campagne** (si module Recommend actif)
10. **Disclaimer** : « Les corrélations présentées ne constituent pas des preuves de causalité. Les variations observées peuvent être influencées par des facteurs non mesurés. »

---

## 17. Place du RAG dans l'ensemble

### 14.1 Rôle spécifique

| Brique | Rôle | Interaction |
|--------|------|-------------|
| **Dashboard** | Lecture globale des KPIs | L'utilisateur observe |
| **Explorer** | Exploration avec filtres | L'utilisateur filtre et navigue |
| **What-If** | Simulation d'impact | L'utilisateur projette |
| **Monitor** | Surveillance proactive | Le système alerte |
| **Recommend** | Aide à la décision | Le système propose |
| **Measure** | Mesure d'impact | Le système mesure |
| **RAG** | **Interrogation libre** | L'utilisateur questionne |

Le RAG est le mode d'interaction le plus flexible : l'utilisateur pose une question en français ou dialecte, le système répond en s'appuyant sur les données réelles.

### 14.2 Ce que le RAG doit faire

- Répondre sur les données consommateurs : « Que pensent les clients de l'emballage Ramy ? »
- Résumer les signaux : « Quel est le sentiment sur la disponibilité à Oran ? »
- Comparer des dimensions : « Comment se compare Ramy vs Hamoud sur le goût ? »
- Expliquer un signal : « Pourquoi le NSS livraison Bejaia a-t-il chuté ? »
- Contextualiser avec les campagnes : « Quel a été l'impact du lancement Jus Citron ? »
- Investiguer les alertes : « Détaille l'alerte sur l'emballage Facebook cette semaine. »

### 14.3 Ce que le RAG ne doit PAS faire

- Générer des recommandations stratégiques (rôle de Recommend)
- Prédire l'avenir (What-If pour les simulations)
- Affirmer des causalités (il cite des données, il ne conclut pas)
- Répondre hors périmètre des données indexées

### 14.4 Évolution post-Wave 4

| Amélioration | Phase | Description |
|-------------|-------|-------------|
| Garde-fous anti-hallucination | Phase 0-1 | Validation factuelle, confidence calibrée, retry, JSON robuste |
| Contextualisation enrichie | Phase 2 | Metadata dans les chunks (wilaya, produit, campagne) |
| RAG + Monitor | Phase 2 | Contexte watchlists et alertes dans les réponses |
| Mode Enhanced RAG | Phase 2 | LLM cloud optionnel pour synthèses avancées |
| RAG conversationnel | Phase 3 | Historique multi-tours |
| RAG + Campaign | Phase 3 | Réponses sur les résultats de campagne |
| Multi-index | Phase 3 | Index séparés si > 100k chunks (mentions, alertes, rapports) |

### 14.5 Index unifié vs multi-index

**Décision :** Un seul index unifié au départ avec métadonnées de filtrage enrichies. Post-retrieval filtering sur brand, product, wilaya, channel, campaign_id.

En Phase 3, si volume > 100k chunks, envisager la séparation par domaine.

---

## 18. Règles d'attribution et garde-fous

### 15.1 Le problème fondamental

L'attribution est le point le plus dangereux du produit :

> Le système observe une corrélation temporelle entre une campagne et une variation de sentiment, et l'utilisateur conclut à une causalité.

Risques : sur-évaluer l'efficacité d'un influenceur, continuer à investir dans des actions sans effet, prendre des décisions sur des bases erronées.

### 15.2 Règle produit fondamentale

**RamyPulse observe et corrèle. Il n'affirme JAMAIS une causalité.**

Cette règle s'applique à TOUS les modules :
- Monitor : « hausse observée » ≠ « hausse causée par »
- Measure : « variation pendant la campagne » ≠ « variation causée par la campagne »
- Recommend : « action suggérée suite à une corrélation » ≠ « action garantie efficace »

### 15.3 Formulations imposées dans l'interface

| ❌ Interdit | ✅ Requis |
|------------|----------|
| « La campagne a causé +18 points » | « Hausse de +18 pts observée pendant la fenêtre de campagne » |
| « Cet influenceur a généré la hausse » | « Corrélation positive entre l'activation et la hausse des mentions positives » |
| « Le produit X a échoué à cause de l'emballage » | « Corrélation forte entre mentions emballage et sentiment négatif sur le produit X » |
| « ROI campagne : +23% » | « Variation observée : +23%. Effet probable, à confirmer avec données vente » |

### 15.4 Niveaux de confiance d'attribution

| Niveau | Conditions | Formulation |
|--------|-----------|-------------|
| **Fort** | Volume > 100 mentions, delta > 20 pts, pas d'événement confondant | « Corrélation forte et isolée » |
| **Modéré** | Volume > 30 mentions, delta > 10 pts | « Corrélation notable » |
| **Faible** | Volume < 30, ou delta < 10, ou événement concurrent | « Signal observé, à confirmer » |
| **Non mesurable** | Volume < 10 ou période trop courte | « Données insuffisantes pour conclure » |

### 15.5 Événements confondants

Le système permet d'enregistrer des événements externes pouvant expliquer une variation :
- Fête nationale / Ramadan / période de chaleur
- Action concurrentielle simultanée
- Problème de production / rappel produit
- Événement médiatique

Ces événements sont annotés manuellement par l'analyste. Le rapport de campagne les mentionne comme facteurs confondants potentiels.

### 15.6 Garde-fous techniques

1. **Minimum de données :** Aucune métrique d'impact si volume total (before + during) < 20 mentions.
2. **Baseline obligatoire :** Pas de rapport d'impact sans période before suffisante (minimum 14 jours avec > 10 mentions).
3. **Disclaimer systématique :** Tout rapport de campagne contient un avertissement standardisé.
4. **Facteurs confondants affichés :** Si des événements externes sont dans la même période, ils sont affichés en contexte.
5. **Score de confiance basé sur les données :** Volume + delta + isolement, pas auto-évaluation LLM.

---

## 19. Workflows utilisateur

### 16.1 Workflow 1 — Onboarding client

**Persona :** Analyste Data / Intégrateur

1. **Installation** — Cloner le repo, créer le venv, installer les dépendances, télécharger DziriBERT fine-tuné + E5.
2. **Configuration des sources** — Enregistrer les sources dans le source_registry (pages Facebook, fiches Google Maps, exports SAV).
3. **Configuration du catalogue** — Charger nomenclature produits, wilayas, concurrents.
4. **Premier import** — Importer les données existantes (CSV/Parquet), lancer le pipeline.
5. **Validation** — Vérifier le dashboard, explorer les données, tester le RAG.
6. **Configuration watchlists** — Créer les premières watchlists sur les priorités business.
7. **Mode enhanced** (optionnel) — Configurer l'API key LLM cloud si souhaité.

**Durée cible :** 1 jour (installation) + 1-2 jours (configuration et premier import).

### 16.2 Workflow 2 — Consultation quotidienne

**Persona :** Directeur Marketing / Brand Manager

1. **Dashboard** — KPIs globaux (NSS global, par produit, par wilaya).
2. **Watch Center** — Alertes récentes, watchlists en dégradation.
3. **Recommendation Desk** — Recommandations actives, priorisées par urgence.
4. **Approfondir** — Cliquer sur une alerte, explorer les mentions dans l'Explorer.
5. **RAG** — « Pourquoi le NSS livraison Oran a-t-il baissé cette semaine ? »
6. **Acquitter** — Marquer les alertes comme vues / traitées, valider ou rejeter les recommandations.

**Durée cible :** 5-10 minutes par jour.

### 16.3 Workflow 3 — Lancement et suivi de campagne

**Persona :** Brand Manager + Analyste Data

1. **Créer la campagne** dans Campaign Lab : nom, dates, produits, wilayas, hashtags, influenceurs.
2. **Vérifier la baseline** — S'assurer qu'il y a assez de données sur la période before.
3. **Lancer** — Passer le statut à `active`.
4. **Suivi quotidien** — Métriques daily dans Campaign Lab pendant la campagne.
5. **Clôturer** — Passer à `completed`.
6. **Analyser** — Lire le rapport B/D/A. Examiner les recommandations post-campagne.
7. **Exporter** — Rapport final pour la direction.

**Durée cible :** 15 min (création) + 5 min/jour (suivi) + 30 min (analyse finale).

### 16.4 Workflow 4 — Veille concurrentielle

**Persona :** Directeur Marketing

1. **Market Radar** — Vue marque vs concurrents, part de voix.
2. **Comparer NSS** — NSS marque vs chaque concurrent par aspect.
3. **Thèmes émergents** — Quels sujets montent chez la concurrence ?
4. **Créer une watchlist** — Si un concurrent monte, créer une watchlist dédiée.
5. **Questionner via RAG** — « Comment se compare Ramy vs Hamoud sur le goût cette semaine ? »

**Durée cible :** 15-20 minutes par semaine.

### 16.5 Workflow 5 — Simulation et arbitrage

**Persona :** Brand Manager

1. **Identifier un problème** — Via dashboard ou alerte.
2. **What-If** — Simuler l'impact de neutraliser ou améliorer un aspect.
3. **Évaluer le delta** — Quel gain NSS si on résout le problème ?
4. **Comparer** — Simuler plusieurs aspects pour prioriser.
5. **Documenter** — Exporter les résultats comme justification.

**Durée cible :** 10-15 minutes par simulation.

### 16.6 Workflow 6 — Configuration d'une watchlist

**Persona :** Analyste Data

1. **Définir le besoin** — « Je veux suivre la disponibilité du jus citron à Alger. »
2. **Créer** dans Watch Center : nom, produit, wilaya, aspect, métrique, baseline, seuil.
3. **Activer** — La watchlist est évaluée à chaque cycle.
4. **Ajuster** — Si trop de faux positifs, ajuster le seuil.

**Durée cible :** 5 minutes par watchlist.

### 16.7 Workflow 7 — Suivi influenceur

**Persona :** Brand Manager + Analyste Data

1. **Enregistrer le créateur** dans `creator_profiles` : nom, plateforme, catégorie, reach.
2. **Associer à une campagne** — Ajouter le creator_id dans la campagne.
3. **Configurer les hashtags/mots-clés** — Ce qu'il faut suivre autour de l'influenceur.
4. **Importer les données** (Phase 3) ou laisser l'API collecter (Phase 4).
5. **Analyser** — Métriques volume + sentiment liées à l'influenceur vs baseline.
6. **Rapport** — Inclus dans le rapport de fin de campagne.

**Durée cible :** 10 min (setup) + intégré au suivi campagne.

### 16.8 Workflow 8 — Exploration ad hoc via RAG

**Persona :** Analyste Data / Brand Manager

1. **Ouvrir RAG Chat** — Poser une question libre.
2. **Exemples de questions :**
   - « Quels sont les problèmes les plus mentionnés cette semaine ? »
   - « Résume le sentiment sur la gamme Premium à Constantine. »
   - « Compare la perception prix Ramy vs Ifri. »
   - « Qu'est-ce qui a changé sur l'emballage depuis le mois dernier ? »
3. **Examiner les sources** — Citations et chunks retrouvés.
4. **Approfondir** — Si la réponse est intéressante, créer une watchlist ou lancer un What-If.

**Durée cible :** 5-10 minutes par investigation.

---

## 20. Intégrations client

### 17.1 Modèle d'intégration — Hybride progressif

**Principe :** Commencer simple, monter en maturité. Le modèle hybride (import + API + collecte publique ciblée) est le plus crédible en entreprise.

| Phase | Mode | Description |
|-------|------|-------------|
| **Phase 0-1** | Import fichier | CSV/Parquet/Excel. Le plus simple et rapide pour le POC. |
| **Phase 3** | Import + API officielle | Connexion Meta (Pages, Instagram), Google Business Profile, YouTube. Sources owned du client. |
| **Phase 4** | Hybride complet | API + import + collecte publique ciblée pour veille concurrentielle. |

### 17.2 Import fichier (Phase 0-1)

#### 17.2.1 Formats

| Format | Obligatoire | Notes |
|--------|------------|-------|
| CSV (UTF-8) | Oui | Le plus universel |
| Parquet | Oui | Standard du projet |
| Excel (.xlsx) | Oui | Format courant chez les clients |
| JSON | Optionnel | Pour les exports d'API bruts |

#### 17.2.2 Schéma d'import minimal

| Colonne | Type | Obligatoire | Description |
|---------|------|-------------|-------------|
| `text` | str | Oui | Le texte du retour client |
| `channel` | str | Non (défaut: « import ») | Canal d'origine |
| `source_url` | str | Non | URL de la source |
| `timestamp` | datetime | Non (défaut: date d'import) | Date du retour |

Colonnes optionnelles : `product`, `wilaya`, `brand`, `campaign_id`.

Le pipeline gère les colonnes absentes : valeurs par défaut + Entity Resolution automatique sur le texte.

#### 17.2.3 Processus d'import

```
Fichier client → Validation schéma → Normalisation → Classification → Entity Resolution → Parquet enrichi
```

L'import est idempotent : même fichier importé 2 fois = pas de doublons (déduplication par hash texte + source + timestamp).

### 17.3 API officielles (Phase 3)

| Plateforme | API | Données accessibles | Pré-requis |
|-----------|-----|---------------------|-----------|
| **Facebook Pages** | Meta Graph API | Commentaires posts des pages gérées | OAuth, Page Access Token |
| **Instagram Business** | Meta Instagram API | Commentaires posts du compte pro | OAuth, lié à Facebook Page |
| **Google Business Profile** | GBP API | Avis clients fiches d'établissement | OAuth, accès approuvé |
| **YouTube** | YouTube Data API v3 | Commentaires vidéos | API Key (quota 10k/jour) |

**Modèle d'authentification :** OAuth 2.0 pour tous sauf YouTube (API key). Tokens stockés localement, chiffrés au repos.

**Important :** Ce modèle donne accès aux « actifs owned » du client (ses pages, ses fiches). Ce n'est pas de la surveillance libre de toute la plateforme.

### 17.4 Collecte publique ciblée (Phase 4)

Périmètre strict :
- Pages publiques de concurrents (données publiquement accessibles)
- Forums et sites d'avis publics
- Commentaires publics YouTube

**La collecte publique n'est JAMAIS la fondation.** C'est un complément pour la veille concurrentielle.

Règles :
1. Seules les sources enregistrées dans le source_registry sont collectées.
2. Pas de collecte en masse non ciblée.
3. Respect des conditions d'utilisation.
4. Rate limiting et backoff.
5. Journalisation pour auditabilité.

### 17.5 Options d'onboarding

| Option | Profil client | Temps | Couverture |
|--------|--------------|-------|-----------|
| **A — Import léger** | POC rapide | 1-2 jours | Données historiques + imports manuels |
| **B — API owned** | Client avec accès Meta + Google | 1-2 semaines | Sources owned, sync automatique |
| **C — Hybride complet** | Client mature | 2-4 semaines | Owned + concurrent + marché |

**Recommandation :** Toujours démarrer par l'option A, puis monter progressivement.

---

## 21. Roadmap en phases

### 18.1 Vue d'ensemble

```
Phase 0 (3-5 sem)     Phase 1 (5-7 sem)     Phase 2 (7-9 sem)       Phase 3 (7-9 sem)       Phase 4 (6-10 sem)
CONSOLIDATION          FOUNDATION             INTELLIGENCE            ACTIVATION              SCALE
──────────────────── ──────────────────── ────────────────────── ────────────────────── ──────────────────────
Fine-tuning DziriBERT  Source Registry        Watch Center            Campaign Lab            API officielles Meta/GBP
Fix FAISS rebuild      Catalogue métier       Alert Engine            Influencer Tracker      Collecte publique ciblée
Garde-fous RAG         Entity Resolution v1   Market Radar            (import)                Influencer automatisé
Évaluation framework   Import Engine          Reco Engine (règles)    B/D/A Engine            (APIs)
Env stabilisé          Schéma enrichi         Recommendation Desk v1  Campaign Report         Multi-tenant
Enrichissement lexique Dashboard enrichi      Notification in-app     Reco Desk v2 (LLM)     Docker / CI-CD
Première ingestion     Explorer enrichi       Stat detection          Email/webhook notif     Cartes géographiques
                       Segmentation           Filtres métier avancés  Attribution Engine      Export avancé (PDF/PPTX)
                                              Digest quotidien        RAG conversationnel     Pattern detector avancé
```

### 18.2 Phase 0 — Consolidation (3-5 semaines)

**Objectif :** Rendre le cœur ML fiable ET préparer l'infrastructure.

| Tâche | Priorité | Effort | Dépendances |
|-------|----------|--------|-------------|
| Constitution dataset d'entraînement (3000+ exemples annotés) | P0 | 1-2 sem | Accès données brutes |
| Fine-tuning DziriBERT sur 5 classes | P0 | 1 sem | Dataset prêt |
| Évaluation classifieur (F1 ≥ 0.70) | P0 | 2-3 jours | Modèle fine-tuné |
| Fix FAISS vector store (ajout incrémental) | P0 | 3-5 jours | — |
| Renforcement garde-fous RAG (JSON, retry, confidence) | P0 | 3-5 jours | — |
| Stabilisation environnement ML (venv, requirements verrouillé) | P0 | 1-2 jours | — |
| Framework d'évaluation continue (accuracy, F1, matrice confusion) | P0 | 3-5 jours | Modèle fine-tuné |
| Enrichissement lexique Arabizi (normalizer + aspect extractor) | P1 | 1 sem | Corpus de données |
| Première ingestion de données réelles (import fichier) | P0 | 2-3 jours | Données fournies par le client |

**Critère de sortie :**
- DziriBERT fine-tuné, F1 macro ≥ 0.70
- FAISS accepte ajouts incrémentaux
- RAG ne hallucine plus de façon flagrante
- Dashboard affiche des données réelles

**Livrable :** RamyPulse opérationnel sur données réelles avec classifieur fiable.

### 18.3 Phase 1 — Foundation (5-7 semaines)

**Objectif :** Construire l'infrastructure métier : registre, catalogue, entités, schéma enrichi.

| Tâche | Priorité | Effort | Dépendances |
|-------|----------|--------|-------------|
| Source Registry (SQLite, CRUD complet) | P0 | 1 sem | — |
| Catalogue métier (products, wilayas, competitors) | P0 | 1 sem | Nomenclature client |
| Entity Resolution v1 (dictionnaires + métadonnées source) | P0 | 2 sem | Catalogue métier |
| Import Engine (CSV/Parquet/Excel, validation, dédup) | P0 | 1 sem | Source Registry |
| Enrichissement du schéma Parquet (ajout colonnes métier) | P0 | 3-5 jours | Entity Resolution |
| Création base SQLite (ramypulse.db, toutes tables) | P0 | 3-5 jours | — |
| Dashboard enrichi (filtres produit/wilaya/canal) | P1 | 1-2 sem | Schéma enrichi |
| Explorer enrichi (colonnes métier visibles et filtrables) | P1 | 1 sem | Schéma enrichi |
| Segmentation croisée (produit × wilaya × aspect × canal) | P1 | 1 sem | Dashboard enrichi |
| Admin Sources (page Streamlit de gestion des sources) | P1 | 1 sem | Source Registry |
| Admin Catalog (page Streamlit de gestion du catalogue) | P1 | 1 sem | Catalogue métier |

**Critère de sortie :**
- Données enrichies avec brand/product/wilaya pour ≥ 60% des mentions
- Dashboard filtre par dimensions métier
- Source registry et import engine opérationnels
- Entity Resolution précision ≥ 0.85 sur échantillon

**Livrable :** RamyPulse avec dimensions métier, import structuré, exploration enrichie.

### 18.4 Phase 2 — Intelligence (7-9 semaines)

**Objectif :** Monitor + Market Radar + début Recommend avec règles.

| Tâche | Priorité | Effort | Dépendances |
|-------|----------|--------|-------------|
| Watchlist Engine (CRUD, évaluation, scoring) | P0 | 2 sem | Phase 1 |
| Alert Engine (threshold + trend + volume + anomaly) | P0 | 2 sem | Watchlist Engine |
| Watch Center (page Streamlit) | P0 | 1-2 sem | Alert Engine |
| Market Radar v1 (part de voix, NSS comparé, thèmes) | P0 | 2 sem | Phase 1 concurrents |
| Recommendation Engine v1 (règles métier, 8+ règles) | P0 | 2 sem | Alert Engine |
| Recommendation Desk v1 (liste, détail, validation) | P1 | 1-2 sem | Reco Engine v1 |
| Notification in-app (centre de notifications) | P0 | 1 sem | Alert Engine |
| Détection statistique (z-score, moving average) | P1 | 1-2 sem | Alert Engine |
| Digest quotidien (page récap) | P1 | 1 sem | Alert Engine |
| Scheduler de watchlists (cron/script planifié) | P1 | 3-5 jours | Watchlist Engine |
| RAG enrichi (metadata, contexte watchlists/alertes) | P1 | 1 sem | Phase 1 + Watch Center |

**Critère de sortie :**
- Watchlists configurables et fonctionnelles
- Alertes se déclenchent correctement (faux positifs < 20%)
- Market Radar affiche part de voix et NSS comparé
- Recommandations par règles attachées aux alertes critiques/warning
- Watch Center et Recommendation Desk v1 opérationnels

**Livrable :** RamyPulse avec surveillance proactive, Market Radar, alertes et recommandations par règles.

### 18.5 Phase 3 — Activation (7-9 semaines)

**Objectif :** Campaign Lab + Influencer + Recommend avec LLM enhanced.

| Tâche | Priorité | Effort | Dépendances |
|-------|----------|--------|-------------|
| Campaign Registry (CRUD campagnes/événements) | P0 | 1 sem | Phase 2 |
| Before/During/After Engine | P0 | 2 sem | Campaign Registry |
| Campaign Lab v1 (création, suivi, rapport B/D/A) | P0 | 2 sem | B/D/A Engine |
| Influencer Tracker (import, profils, association campagne) | P0 | 1-2 sem | Campaign Registry |
| Campaign Report Generator (template + enhanced LLM) | P1 | 1-2 sem | B/D/A Engine |
| Attribution Engine (niveaux de confiance, confounding events) | P1 | 1-2 sem | Campaign Lab |
| Recommendation Desk v2 (enrichi LLM enhanced) | P1 | 2 sem | Reco Engine v1 + LLM API |
| API Meta (Facebook Pages) | P1 | 2 sem | OAuth flow |
| API Google Business Profile | P1 | 2 sem | OAuth flow |
| Email notifications (SMTP configurable) | P2 | 1 sem | Alert Engine |
| Webhook notifications | P2 | 1 sem | Alert Engine |
| RAG conversationnel (historique multi-tours) | P2 | 1 sem | RAG existant |
| Audio Pipeline Whisper | P2 | 1-2 sem | — |

**Critère de sortie :**
- Campagnes : cycle complet draft → active → completed → rapport
- Métriques B/D/A calculées correctement
- Influenceurs : profils créés, associés aux campagnes, métriques calculées
- Recommendation Desk v2 avec synthèses LLM enhanced
- APIs Meta et Google connectées (au moins un client test)

**Livrable :** RamyPulse avec Campaign Lab, influencer tracking, recommandations enrichies, APIs.

### 18.6 Phase 4 — Scale (6-10 semaines)

**Objectif :** Industrialisation, automatisation, multi-tenant.

| Tâche | Priorité | Effort | Dépendances |
|-------|----------|--------|-------------|
| Influencer Tracker automatisé (APIs Meta, YouTube) | P1 | 3 sem | Campaign Lab + APIs |
| Collecte publique ciblée (concurrents, marché) | P1 | 2 sem | Source Registry |
| Pattern Detector avancé (changepoint, concentration géo) | P1 | 2 sem | Alert Engine |
| Docker + CI/CD | P1 | 1-2 sem | — |
| Multi-tenant (isolation données client) | P1 | 2-3 sem | — |
| Cartes géographiques NSS par wilaya | P2 | 1-2 sem | Données wilaya |
| Export avancé (PDF, PPTX) | P2 | 1-2 sem | — |
| Documentation API d'intégration | P1 | 1-2 sem | — |
| Tests de charge et optimisation | P1 | 1-2 sem | — |
| API YouTube Data (collecte commentaires) | P2 | 1 sem | Source Registry |

**Critère de sortie :**
- Influencer tracking automatisé via APIs
- Docker image buildable et exécutable
- Documentation complète pour intégrateurs
- Système prêt pour le multi-tenant

**Livrable :** RamyPulse industrialisé, prêt pour déploiement multi-client.

### 18.7 Timeline estimée

| Phase | Durée | Date estimée (si démarrage avril 2026) |
|-------|-------|---------------------------------------|
| Phase 0 — Consolidation | 3-5 semaines | Avril — Mai 2026 |
| Phase 1 — Foundation | 5-7 semaines | Mai — Juillet 2026 |
| Phase 2 — Intelligence | 7-9 semaines | Juillet — Septembre 2026 |
| Phase 3 — Activation | 7-9 semaines | Octobre — Décembre 2026 |
| Phase 4 — Scale | 6-10 semaines | Janvier — Mars 2027 |

**Total estimé :** 10-13 mois pour la vision complète. Produit utilisable dès fin Phase 1 (~2-3 mois). Produit différenciant dès fin Phase 2 (~5-6 mois).

**Hypothèse :** Équipe de 1-2 développeurs + 1 annotateur (Phase 0). Ces estimations sont en effort net.

---

## 22. Risques et arbitrages

### 19.1 Risques techniques

| Risque | Probabilité | Impact | Mitigation |
|--------|------------|--------|------------|
| **DziriBERT ne converge pas** | Moyenne | Critique | Tester CAMeLBERT, MarBERT, ArabBERT. Augmenter dataset. Ce n'est PAS un risque éliminatoire. |
| **Dataset insuffisant ou biaisé** | Moyenne | Élevé | Viser 3000+ exemples. Inter-annotator agreement. Augmenter si F1 < 0.70. |
| **APIs Meta/Google refusent l'accès** | Moyenne | Modéré | Import fichier toujours disponible en fallback. Ne jamais dépendre d'une seule API. |
| **Ollama insuffisant pour RAG** | Faible | Modéré | Mode enhanced avec LLM cloud en option. |
| **Volume données insuffisant pour stats** | Élevée (au début) | Modéré | Seuils minimaux (>20 mentions NSS, >10 mentions alerte). Afficher « données insuffisantes ». |
| **Entity resolution trop bruitée** | Moyenne | Modéré | Dictionnaires stricts. Précision > rappel (ne pas attribuer plutôt qu'attribuer faux). |
| **Incompatibilités Python/torch/transformers** | Observée | Modéré | venv documenté, requirements verrouillé. Docker en Phase 4. |
| **FAISS ne scale pas après fix** | Faible | Modéré | Ajout incrémental. Si > 500k vecteurs, migrer vers IVF-Flat. |

### 19.2 Risques produit

| Risque | Probabilité | Impact | Mitigation |
|--------|------------|--------|------------|
| **Fatigue d'alerte** | Élevée | Élevé | Seuils conservateurs par défaut. Priorités (critical > warning > info). Digest groupé. Réglage utilisateur. |
| **Recommandations trop génériques** | Élevée (au début) | Modéré | Règles simples et spécifiques d'abord. Feedback loop. Enhanced LLM pour nuance. |
| **Sur-interprétation causalité** | Élevée | Élevé | Garde-fous section 15 systématiques. Formation utilisateur. Disclaimer. |
| **Adoption faible (setup complexe)** | Moyenne | Élevé | Mode import léger pour POC. Données démo. Script onboarding. |
| **Scope creep** | Élevée | Élevé | Critères de sortie stricts par phase. Pas de Phase N+1 sans validation Phase N. |
| **LLM enhanced trop coûteux** | Moyenne | Faible | Optionnel. Le core fonctionne sans. Client choisit. |

### 19.3 Contraintes non négociables

Les règles suivantes font partie du PRD et gouvernent les décisions de produit et d'implémentation.

1. **Toujours 5 classes discrètes de sentiment.**  
   Pas de score continu pour le cœur ABSA. très_positif, positif, neutre, négatif, très_négatif.

2. **Le cœur analytique doit rester exploitable localement.**  
   Le produit ne peut pas devenir inutilisable sans service externe. SQLite pas PostgreSQL. FAISS pas Pinecone. Ollama pas OpenAI pour le core.

3. **Le mode enhanced n'est jamais obligatoire.**  
   Les fonctions avancées enrichissent, elles ne rendent pas le cœur inutilisable. Flag de config. Fallback local toujours disponible.

4. **Tout composant enhanced doit avoir une politique explicite de fallback.**

5. **Les sorties du produit doivent rester traçables.**  
   Preuves, sources et niveau de confiance visibles. Recommandation → signal → données.

6. **Corrélation n'est jamais égalée à causalité.**  
   Garde-fous systématiques dans les modules Recommend, Measure et Campaign Lab.

7. **Le format analytique standard reste centré sur les mentions enrichies.**  
   Parquet pour l'analytique, SQLite pour le CRUD métier.

8. **La configuration structurante doit rester centralisée et gouvernable.**  
   Toutes constantes dans config.py.

9. **Le code et l'architecture doivent rester testables.**  
   Chaque module testé. Couverture ≥ 80%. Pas de print(), logging module uniquement.

10. **Le produit doit rester focalisé sur la valeur métier, pas sur la sophistication technique pour elle-même.**  
    Docstrings français. Interface en français.

#### Règle formelle sur le mode enhanced

Le mode enhanced suit les règles suivantes :

- il est activé par configuration (`config.ENHANCED_MODE=True` + `config.CLOUD_LLM_API_KEY`)
- il est désactivable sans casser le cœur
- il n'est jamais requis pour obtenir une valeur de base
- il ne remplace pas l'auditabilité du cœur
- il doit toujours être borné par des garde-fous métier et UX
- cette couche peut s'appuyer sur des modèles puissants, y compris via API, si la valeur métier le justifie — le LLM cloud multiplie la valeur, il ne la crée pas

### 19.4 Arbitrages résumés

| Question | Décision | Raison |
|----------|-------------|--------|
| Fine-tuning d'abord ou features d'abord ? | **Les deux en parallèle.** Fine-tuning en P0, infrastructure en P0-P1. | L'infrastructure ne dépend pas du classifieur. |
| Recommend : quand ? | **Phase 2 (règles), Phase 3 (enhanced).** | Constitutif du produit, pas un nice-to-have. |
| Influencer : quand ? | **Phase 3 (import), Phase 4 (automatisé).** | Partie du module Measure, pas du premium. |
| Market Radar : quand ? | **Phase 2.** Surface complète. | Intelligence marché = module constitutif. |
| Local-first : plafond ? | **Non. Principe de base + mode enhanced.** | Core local, enhanced optionnel. |
| SQLite ou PostgreSQL ? | **SQLite.** | Local-first, fichier unique, suffisant. |
| Un index RAG ou plusieurs ? | **Un seul + metadata au début. Multi si > 100k.** | Simplicité d'abord. |
| Détection anomalies : ML ou stats ? | **Stats (z-score, MA) Phase 2. ML Phase 4 optionnel.** | Plus interprétable, fiable avec peu de données. |
| Docker au MVP ? | **Non. Phase 4.** | venv suffit pour les premiers déploiements. |

---

## 23. Critères de qualité par module et par phase

### 20.1 Module Listen — Classification sentiment

| Métrique | Phase 0 (MVP) | Phase 2+ (cible) |
|----------|---------------|-------------------|
| F1 macro (5 classes) | ≥ 0.70 | ≥ 0.80 |
| F1 par classe | ≥ 0.60 chaque classe | ≥ 0.70 chaque classe |
| Accuracy | ≥ 0.65 | ≥ 0.75 |
| Confusion adjacente | Acceptée (positif ↔ très_positif) | Réduite |
| Dataset test | ≥ 600 exemples | ≥ 1000 exemples |
| Inter-annotator agreement | ≥ 0.65 (Cohen's kappa) | ≥ 0.75 |

### 20.2 Module Listen — Entity Resolution

| Métrique | Phase 1 (MVP) | Phase 3+ (cible) |
|----------|---------------|-------------------|
| Précision (attributions correctes / totales) | ≥ 0.85 | ≥ 0.92 |
| Rappel (entités trouvées / présentes) | ≥ 0.60 | ≥ 0.80 |
| Faux positifs wilaya | < 10% | < 5% |
| Faux positifs produit | < 15% | < 8% |

### 20.3 Module Understand — RAG

| Métrique | Phase 1 (MVP) | Phase 3+ (cible) |
|----------|---------------|-------------------|
| Faithfulness (réponse fondée dans les chunks) | ≥ 80% | ≥ 90% |
| Relevance (chunks pertinents dans top-3) | ≥ 70% | ≥ 80% |
| Refus hors périmètre (« je ne sais pas ») | ≥ 80% | ≥ 95% |
| Latence de réponse | < 10s | < 5s |

### 20.4 Module Monitor — Alertes

| Métrique | Phase 2 (MVP) | Phase 3+ (cible) |
|----------|---------------|-------------------|
| Faux positifs | < 20% | < 10% |
| Faux négatifs | < 30% | < 15% |
| Latence de détection | < 24h après ingestion | < 6h |
| Alertes/jour (éviter fatigue) | < 10 standard | < 5 critical + 10 warning |

### 20.5 Module Recommend — Recommandations

| Métrique | Phase 2 (règles) | Phase 3 (enhanced) |
|----------|-------------------|---------------------|
| Taux de validation utilisateur | > 50% | > 70% |
| Pertinence perçue (feedback utilisateur) | > 60% « utile » | > 75% « utile » |
| Couverture (% alertes avec reco) | > 80% (critical + warning) | > 90% |
| Traçabilité (reco → signal → preuves) | 100% | 100% |
| Minimum données respecté | 100% (pas de reco < 10 mentions) | 100% |

### 20.6 Module Measure — Campagnes

| Métrique | Phase 3 (MVP) | Phase 4 (cible) |
|----------|---------------|------------------|
| Métriques B/D/A calculées correctement | 100% | 100% |
| Disclaimer systématique dans rapports | 100% | 100% |
| Rapport exportable | Oui (markdown) | Oui (PDF + markdown) |
| Influenceur intégré au rapport | Oui (si associé) | Oui |
| Confiance d'attribution calculée | Oui | Oui, avec confounding events |

### 20.7 Critères d'acceptation par phase

#### Phase 0 — Consolidation

| Critère | Vérification |
|---------|-------------|
| DziriBERT fine-tuné, F1 macro ≥ 0.70 | Matrice de confusion sur dataset test |
| FAISS ajout incrémental sans rebuild | Test unitaire 3 ajouts successifs |
| RAG JSON robuste (markdown-wrapped) | Test avec 3 formats connus |
| RAG retry si Ollama indisponible | Test mock d'indisponibilité |
| Dashboard données réelles | Test E2E avec annotated.parquet réel |
| Framework évaluation opérationnel | Script exécutable, rapport lisible |
| venv reproductible | Installation machine vierge réussit |

#### Phase 1 — Foundation

| Critère | Vérification |
|---------|-------------|
| Source Registry CRUD complet | Tests unitaires |
| Catalogue : ≥ 10 produits, ≥ 10 concurrents, 58 wilayas | Données chargées |
| Entity Resolution précision ≥ 0.85 | Évaluation sur 200 mentions |
| Import Engine : CSV, Parquet, Excel | Test avec 3 fichiers types |
| Dashboard filtres produit/wilaya/canal | Test UX données réelles |
| Parquet enrichi : brand/product/wilaya ≥ 60% mentions | Vérification statistique |
| Admin Sources et Admin Catalog fonctionnels | Test UX |

#### Phase 2 — Intelligence

| Critère | Vérification |
|---------|-------------|
| Watchlist : création, évaluation automatique | Tests + vérification fonctionnelle |
| Alert Engine : threshold breach dans scénario test | Test données synthétiques |
| Watch Center affiche watchlists + alertes | Test UX |
| Market Radar : part de voix, NSS comparé | Test avec données concurrents |
| Recommendation Engine v1 : ≥ 8 règles implémentées | Tests unitaires |
| Recommendation Desk v1 : liste + détail + validation | Test UX |
| Notification in-app fonctionnelle | Test UX |
| Faux positifs alertes < 20% premier mois | Revue mensuelle |

#### Phase 3 — Activation

| Critère | Vérification |
|---------|-------------|
| Campagne cycle complet : draft → active → completed → rapport | Test fonctionnel |
| B/D/A métriques correctes sur cas test | Test données contrôlées |
| Rapport campagne export complet avec disclaimer | Test export |
| Influencer : profil créé, associé, métriques calculées | Test fonctionnel |
| Reco Desk v2 enhanced avec synthèses LLM | Test avec LLM configuré |
| API Meta : OAuth + collecte commentaires | Test page test |
| Attribution Engine : niveaux de confiance corrects | Tests unitaires |

#### Phase 4 — Scale

| Critère | Vérification |
|---------|-------------|
| Influencer automatisé via APIs | Test fonctionnel multi-plateforme |
| Docker image buildée et démarrable | Test build + lancement |
| Documentation intégrateur complète | Review par un tiers |
| LLM enhanced activable/désactivable par config | Test flag on/off |
| Tests de charge OK (10k mentions/import, 100 watchlists) | Test de performance |

### 20.8 Critères transversaux

| Dimension | Standard |
|-----------|---------|
| **Tests unitaires** | Couverture ≥ 80% tout nouveau code. Passent sans modèles/services réels. |
| **Performance** | Dashboard < 3s. RAG < 10s. Import 10k lignes < 60s. |
| **Documentation** | Chaque module a un README. APIs internes documentées. Guide d'installation. |
| **Langue** | Interface français. Docstrings français. Messages d'erreur français. |
| **Sécurité** | Tokens OAuth chiffrés au repos. Pas de credentials en clair. .env pour les secrets. |
| **Logging** | logging module uniquement. Niveaux : DEBUG, INFO, WARNING, ERROR. |
| **Idempotence** | Imports idempotents. Évaluations watchlist reproductibles. |

---

## Annexes

### Annexe A — Surfaces produit (pages Streamlit cibles)

#### Pages existantes (Wave 4)

| Page | Fonction | Évolution |
|------|----------|-----------|
| 01_dashboard.py | KPIs globaux, heatmap, tendances | À enrichir : filtres métier (Phase 1-2) |
| 02_explorer.py | Exploration détaillée des mentions | À enrichir : colonnes métier (Phase 1) |
| 03_chat.py | RAG Q&A | À améliorer : garde-fous (Phase 0-1), enhanced (Phase 2) |
| 04_whatif.py | Simulation What-If | Stable |

#### Pages nouvelles (post-Wave 4)

| Page | Module | Phase |
|------|--------|-------|
| 05_watch_center.py | Monitor | Phase 2 |
| 06_market_radar.py | Monitor + Understand | Phase 2 |
| 07_campaign_lab.py | Measure | Phase 3 |
| 08_recommendation_desk.py | Recommend | Phase 2 (v1 règles) → Phase 3 (v2 enhanced) |
| 09_admin_sources.py | Listen (configuration) | Phase 1 |
| 10_admin_catalog.py | Listen (catalogue métier) | Phase 1 |

---

### Annexe B — Matrice de dépendances entre modules

```
Listen ─────────▶ Understand ─────────▶ Monitor ─────────▶ Recommend
                       │                     │                    │
                       │                     │                    │
                       ▼                     ▼                    ▼
                   Dashboard            Watch Center       Recommendation Desk
                   Explorer             Market Radar
                   RAG Chat
                   What-If

Listen ─────────▶ Measure ◀──── enrichi par ──── Recommend
                       │
                       ▼
                  Campaign Lab
                  Report Generator
                  Influencer Tracker

Dépendances strictes :
  - Understand nécessite Listen (données + classifieur)
  - Monitor nécessite Understand (NSS + dimensions métier)
  - Recommend nécessite Monitor (signaux + alertes)
  - Measure nécessite Listen (données branchées)

Dépendances souples (enrichissement) :
  - Recommend est enrichi par Measure (contexte campagne)
  - Market Radar est enrichi par Monitor (alertes concurrentielles)
  - Campaign Lab est enrichi par Recommend (recommandations post-campagne)
  - RAG est enrichi par Monitor + Measure (contexte alertes + campagnes)
```

---

### Annexe C — Schéma complet de la base SQLite

```sql
-- Fichier: ramypulse.db (créé au premier lancement)

-- ═══════════════════════════════════════════════
-- COUCHE 1 — SOURCE REGISTRY
-- ═══════════════════════════════════════════════

CREATE TABLE source_registry (
    source_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    source_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    external_id TEXT,
    url TEXT,
    owner_type TEXT NOT NULL,       -- owned, competitor, market
    auth_mode TEXT,                 -- oauth, api_key, import, public
    brand TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    sync_frequency TEXT,
    last_sync_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- ═══════════════════════════════════════════════
-- COUCHE 2 — BUSINESS CATALOG
-- ═══════════════════════════════════════════════

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    product_line TEXT,
    product_name TEXT NOT NULL,
    sku TEXT,
    category TEXT,
    keywords_ar TEXT,
    keywords_arabizi TEXT,
    keywords_fr TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wilayas (
    wilaya_code TEXT PRIMARY KEY,
    wilaya_name_fr TEXT NOT NULL,
    wilaya_name_ar TEXT NOT NULL,
    keywords_arabizi TEXT,
    region TEXT
);

CREATE TABLE competitors (
    competitor_id TEXT PRIMARY KEY,
    brand_name TEXT NOT NULL,
    category TEXT,
    keywords_ar TEXT,
    keywords_arabizi TEXT,
    keywords_fr TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════
-- COUCHE 3 — MONITORING
-- ═══════════════════════════════════════════════

CREATE TABLE watchlists (
    watchlist_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    scope_type TEXT NOT NULL,
    products TEXT,                  -- JSON array
    competitors TEXT,               -- JSON array
    wilayas TEXT,                   -- JSON array
    channels TEXT,                  -- JSON array
    aspects TEXT,                   -- JSON array
    keywords TEXT,                  -- JSON array
    source_registry_ids TEXT,       -- JSON array
    metric_type TEXT NOT NULL,
    baseline_window INTEGER DEFAULT 30,
    alert_threshold REAL,
    alert_direction TEXT,
    owner TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE alerts (
    alert_id TEXT PRIMARY KEY,
    watchlist_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    metric_name TEXT,
    metric_value REAL,
    baseline_value REAL,
    delta REAL,
    evidence TEXT,                  -- JSON
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by TEXT,
    acknowledged_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(watchlist_id)
);

-- ═══════════════════════════════════════════════
-- COUCHE 5 — RECOMMENDATIONS
-- ═══════════════════════════════════════════════

CREATE TABLE recommendations (
    recommendation_id TEXT PRIMARY KEY,
    alert_id TEXT,
    signal_type TEXT NOT NULL,
    problem TEXT NOT NULL,
    evidence_summary TEXT,
    urgency TEXT NOT NULL,
    actions TEXT NOT NULL,          -- JSON array
    assumptions TEXT,               -- JSON array
    risks TEXT,                     -- JSON array
    confidence TEXT NOT NULL,
    generation_mode TEXT NOT NULL,  -- rules, enhanced
    requires_human_validation BOOLEAN DEFAULT TRUE,
    is_validated BOOLEAN DEFAULT FALSE,
    validated_by TEXT,
    validated_at DATETIME,
    feedback TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════
-- CAMPAIGN INTELLIGENCE
-- ═══════════════════════════════════════════════

CREATE TABLE campaigns (
    campaign_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    brand TEXT NOT NULL,
    products TEXT,                  -- JSON array
    wilayas TEXT,                   -- JSON array
    channels TEXT,                  -- JSON array
    start_at DATETIME NOT NULL,
    end_at DATETIME,
    goal TEXT,
    budget REAL,
    hashtags TEXT,                  -- JSON array
    keywords TEXT,                  -- JSON array
    tracked_accounts TEXT,          -- JSON array
    tracked_posts TEXT,             -- JSON array
    tracked_urls TEXT,              -- JSON array
    creator_profiles TEXT,          -- JSON array
    before_window INTEGER DEFAULT 30,
    after_window INTEGER DEFAULT 14,
    status TEXT DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE creator_profiles (
    creator_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    external_id TEXT,
    profile_url TEXT,
    category TEXT,
    estimated_reach TEXT,
    contact_info TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════
-- NOTIFICATIONS & AUDIT
-- ═══════════════════════════════════════════════

CREATE TABLE notifications (
    notification_id TEXT PRIMARY KEY,
    alert_id TEXT,
    recommendation_id TEXT,
    channel TEXT NOT NULL,
    recipient TEXT,
    title TEXT NOT NULL,
    body TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    delivered_at DATETIME,
    read_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    source TEXT,
    details TEXT,                   -- JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════
-- CONFOUNDING EVENTS (pour l'attribution)
-- ═══════════════════════════════════════════════

CREATE TABLE confounding_events (
    event_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    event_type TEXT NOT NULL,       -- holiday, competitor_action, production_issue, media_event, seasonal
    description TEXT,
    start_at DATETIME NOT NULL,
    end_at DATETIME,
    wilayas TEXT,                   -- JSON array (si applicable)
    products TEXT,                  -- JSON array (si applicable)
    created_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

### Annexe D — Dictionnaire d'aspects (état actuel et cible)

#### État actuel (~50 mots-clés, 5 aspects)

| Aspect | Mots-clés existants |
|--------|---------------------|
| **goût** | ta3m, طعم, goût, saveur, madha9, bnin, ldid, mli7, doux, amer, sucré (11) |
| **emballage** | تغليف, 9ar3a, bouteille, plastique, emballage, packaging, 3olba, couvercle, bouchon, fuite (10) |
| **prix** | سعر, ghali, rkhis, prix, cher, pas_cher, prix_abordable, t7ayol, promotions (9) |
| **disponibilité** | متوفر, nlgah, ma_kaynch, disponible, rupture, yla9awh, ma_lgitouch (7) |
| **fraîcheur** | طازج, bared, skhoun, frais, froid, chaud, périmé, fraîcheur, date, expiration (10) |

#### Cible Phase 1 (~150 mots-clés)

| Aspect | Mots-clés à explorer |
|--------|---------------------|
| goût | 7lou, m3afn, merr, mouss, bzf bnin, ma bnin ch, ta3m ghalat, ta3m ktir hlow |
| emballage | msarb, ytsarrab, m9lob, carton, plastic, tetrapak, 3olbet, ka7la |
| prix | promotion, solde, tkhfid, ghla, rkhs, ma yswach, prix fort |
| disponibilité | mafamech, ylgawh, manlogouch, f toute les wilayas, fi superette, fi gros |
| fraîcheur | bared bzf, skhoun, date expire, nouveau lot, stock 9dim |

#### Aspects candidats Phase 2+

| Aspect | Justification | Décision |
|--------|--------------|----------|
| livraison / distribution | Fréquemment mentionné, distinct de disponibilité | Évaluer sur corpus réel |
| service client / SAV | Feedback sur le support | P2 si volume suffisant |
| publicité / marketing | Réaction aux campagnes | P2, lié à Measure |

**Règle :** Pas de multiplication prématurée. Valider sur corpus réel que le volume justifie un aspect séparé.

#### Méthodologie d'enrichissement

1. Extraire les mots les plus fréquents du corpus réel
2. Identifier les mots non couverts
3. Catégoriser par un locuteur natif
4. Ajouter dans `config.ASPECT_KEYWORDS`
5. Évaluer précision et rappel sur échantillon

---

### Annexe E — Hypothèses documentées

| # | Hypothèse | Sections impactées | Risque si faux |
|---|----------|-------------------|----------------|
| H1 | DziriBERT fine-tunable à F1 ≥ 0.70 avec 3000 exemples | Phase 0, §7.1, §20.1 | Modéré — alternatives (CAMeLBERT, MarBERT) |
| H2 | Données client disponibles en volume suffisant (>1000 mentions/mois) | Toutes phases | Élevé — ajuster seuils, réduire scope watchlists |
| H3 | APIs Meta/Google restent accessibles et stables | Phase 3, §17.3 | Modéré — fallback import fichier |
| H4 | Client peut fournir catalogue produit et mapping wilaya | Phase 1, §10.2 | Élevé — entity resolution très limitée |
| H5 | Ollama + llama3.2:3b suffisant pour RAG basique | §7.2, §14 | Faible — mode enhanced en backup |
| H6 | Locuteur natif disponible pour annotation | Phase 0, §20.1 | Élevé — annotation biaisée sans |
| H7 | Wilayas identifiables dans le texte ou métadonnées | Phase 1-2 | Modéré — certaines mentions non géolocalisables |
| H8 | Données concurrent accessibles publiquement | Phase 2, Market Radar | Modéré — Market Radar limité aux imports |
| H9 | Administrateur technique disponible côté client | §16.1, §17 | Faible — mode import léger minimise le besoin |
| H10 | LLM cloud (Claude/GPT-4) disponible et abordable pour enhanced | Phase 3, §12.5 | Faible — mode rules toujours disponible |
| H11 | L'équipe peut paralléliser fine-tuning et infrastructure | Phase 0-1, §18 | Modéré — allonger la timeline si séquentiel |

---

### Annexe F — Questions ouvertes

| # | Question | Impact | Bloquant ? |
|---|---------|--------|------------|
| Q1 | Volume réel de données chez le premier client cible ? | Dimensionnement seuils et stats | Non (estimation conservatrice) |
| Q2 | Client prêt à fournir des annotateurs ? | Phase 0 timeline | Bloquant pour Phase 0 |
| Q3 | Budget LLM cloud pour le mode enhanced ? | Phase 3 scope | Non (optionnel) |
| Q4 | Infrastructure Docker existante chez le client ? | Phase 4 industrialisation | Non |
| Q5 | Données de vente disponibles pour corrélation campagne/ventes ? | Profondeur attribution | Non |
| Q6 | Concurrents cibles identifiés et nomenclature disponible ? | Phase 1-2, catalogue | Non (ajout progressif) |
| Q7 | Support TikTok comme canal ? | Architecture ingestion | Non (ajout futur) |
| Q8 | Schéma Parquet 7 colonnes utilisé par outils tiers ? | Migration schéma | Potentiellement bloquant |
| Q9 | Quel LLM cloud privilégier (Claude, GPT-4, Mistral) ? | Config enhanced | Non (configurable) |
| Q10 | Fréquence de rafraîchissement acceptable pour le client ? | Dimensionnement scheduler | Non (configurable) |

---

## 24. Baseline d'audit retenue

Baseline documentaire retenue pour cette version :

- repo de référence autour du commit `5274350`
- état fonctionnel revalidé localement le 2026-03-28
- 53 fichiers Python
- environ 7 946 lignes Python
- 309 tests verts dans le venv projet

Cette baseline doit être mise à jour à chaque révision majeure du PRD.

---

*Document généré le 2026-03-28. Ce PRD est un document vivant qui doit être mis à jour à chaque fin de phase.*
