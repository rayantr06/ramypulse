# RamyPulse - Brief Actuel et Prompt pour le Nouveau PRD Post-Wave 4

## Objet
Ce document a 2 buts :

- expliquer clairement l'etat actuel du projet RamyPulse
- fournir un prompt solide a donner a un agent de recherche et de raisonnement avance pour rediger un nouveau PRD post-Wave 4

Ce document sert de passerelle entre :
- le PRD initial
- l'etat reel du code aujourd'hui
- la vision cible discutee pour la version finale du produit

## 1. Etat actuel du projet

### Positionnement actuel
RamyPulse est aujourd'hui un systeme local d'analyse de sentiment ABSA pour dialecte algerien, avec interface Streamlit, pipeline de donnees, module RAG et simulation What-If.

Le coeur actuel du produit couvre :
- ingestion et normalisation de texte
- extraction d'aspects
- classification de sentiment en 5 classes discretes
- calcul de NSS
- simulation What-If
- indexation RAG locale
- dashboard, explorateur, chat et page What-If
- scripts d'execution de la pipeline complete

### Regles structurantes deja etablies
Le projet est cadre par [CLAUDE.md](G:/ramypulse/CLAUDE.md), qui impose notamment :

- 5 classes discretes de sentiment, jamais de score continu
- local-first
- pas de dependance cloud obligatoire pour le coeur du produit
- docstrings en francais
- tests unitaires
- logging, pas de `print()`
- format de donnees standard :
  `text, sentiment_label, channel, aspect, source_url, timestamp, confidence`

### Etat reel du code
Le repo contient aujourd'hui :

- [config.py](G:/ramypulse/config.py)
- [core/ingestion/normalizer.py](G:/ramypulse/core/ingestion/normalizer.py)
- [core/analysis/aspect_extractor.py](G:/ramypulse/core/analysis/aspect_extractor.py)
- [core/analysis/nss_calculator.py](G:/ramypulse/core/analysis/nss_calculator.py)
- [core/analysis/sentiment_classifier.py](G:/ramypulse/core/analysis/sentiment_classifier.py)
- [core/analysis/absa_engine.py](G:/ramypulse/core/analysis/absa_engine.py)
- [core/rag/embedder.py](G:/ramypulse/core/rag/embedder.py)
- [core/rag/vector_store.py](G:/ramypulse/core/rag/vector_store.py)
- [core/rag/retriever.py](G:/ramypulse/core/rag/retriever.py)
- [core/rag/generator.py](G:/ramypulse/core/rag/generator.py)
- [core/whatif/simulator.py](G:/ramypulse/core/whatif/simulator.py)
- [app.py](G:/ramypulse/app.py)
- [pages/01_dashboard.py](G:/ramypulse/pages/01_dashboard.py)
- [pages/02_explorer.py](G:/ramypulse/pages/02_explorer.py)
- [pages/03_chat.py](G:/ramypulse/pages/03_chat.py)
- [pages/04_whatif.py](G:/ramypulse/pages/04_whatif.py)
- [scripts/01_collect_data.py](G:/ramypulse/scripts/01_collect_data.py)
- [scripts/02_process_data.py](G:/ramypulse/scripts/02_process_data.py)
- [scripts/03_classify_sentiment.py](G:/ramypulse/scripts/03_classify_sentiment.py)
- [scripts/04_build_index.py](G:/ramypulse/scripts/04_build_index.py)
- [scripts/05_run_demo.py](G:/ramypulse/scripts/05_run_demo.py)

### Validation actuelle
Le projet a ete valide dans un venv propre avec :

- `309 passed` sur la suite de tests
- pipeline `01 -> 05` executable localement
- dashboard et pages Streamlit demarrables
- index FAISS et BM25 generables

### Ce que le produit sait faire aujourd'hui
- analyser des retours clients multi-canaux normalises
- calculer sentiment, aspect et NSS
- offrir une lecture dashboard / explorer
- repondre a des questions via RAG
- simuler l'impact d'un aspect
- executer une demo locale de bout en bout

### Limites actuelles
Le produit n'est pas encore la version finale visee.

Il manque notamment :
- vraies integrations client multi-sources en production
- registre de sources metier
- dimensions metier enrichies comme `wilaya`, `product`, `campaign`
- watchlists configurables
- moteur d'alerting intelligent
- veille concurrentielle et radar marche
- suivi structure des campagnes / influenceurs / activations
- moteur de recommandations d'action
- modele d'attribution rigoureux pour mesurer l'effet d'une campagne

### Ce que le produit n'est pas encore
RamyPulse n'est pas encore :
- une plateforme complete de social listening entreprise
- une plateforme de competitive intelligence
- une plateforme de campaign intelligence
- un moteur de recommandations marketing mature

Il est aujourd'hui un socle analytique solide, mais pas encore la plateforme finale discutee.

## 2. Sources de contexte post-Wave 4 deja preparees

Les idees post-Wave 4 sont deja documentees dans `docs/` et doivent servir de base obligatoire au nouveau PRD :

- [post-wave4-monitoring-intelligent.md](G:/ramypulse/docs/post-wave4-monitoring-intelligent.md)
- [MODELE_D_INTEGRATION_CLIENT_ET_SOURCES.md](G:/ramypulse/docs/MODELE_D_INTEGRATION_CLIENT_ET_SOURCES.md)
- [VISION_POST_WAVE4_MARKET_INTELLIGENCE.md](G:/ramypulse/docs/VISION_POST_WAVE4_MARKET_INTELLIGENCE.md)

Ces documents couvrent deja :
- watchlists
- surveillance intelligente
- dimensions metier enrichies
- integration client et sources
- veille marche et concurrence
- suivi d'evenements et de campagnes
- suivi influenceurs
- moteur de recommandations
- garde-fous d'attribution

## 3. Ce que doit produire le nouveau PRD post-Wave 4

Le nouveau PRD ne doit pas etre une simple note d'idees.
Il doit etre un vrai document directeur, au niveau du premier PRD technique.

Il doit expliquer :
- ce qu'est RamyPulse aujourd'hui
- ce que RamyPulse doit devenir
- comment passer du produit actuel a la version cible
- dans quel ordre implementer cette transformation
- quels modules sont necessaires
- quels schemas, API, workflows, garde-fous et criteres de qualite doivent etre definis

Le nouveau PRD doit aussi faire des choix.
Il ne doit pas juste lister des options sans arbitrage.

## 4. Cible produit a faire apparaitre dans le nouveau PRD

Le futur RamyPulse doit aller vers une plateforme qui combine :

- analyse ABSA
- dashboard et exploration
- RAG interrogable
- What-If
- watchlists metier
- alerting intelligent
- suivi du marche et des concurrents
- suivi structure des campagnes, activations et influenceurs
- recommandations d'action
- rapports intelligents de fin de campagne

Le document doit clairement separer :

- le coeur local-first du produit
- les integrations clients
- les briques optionnelles ou premium
- les capacites qui peuvent necessiter un LLM externe puissant

## 5. Prompt a donner a un agent de recherche / raisonnement avance

Copier-coller le prompt ci-dessous tel quel.

```text
Tu travailles sur le projet RamyPulse.

Ta mission n'est PAS de coder.
Ta mission est de produire un nouveau PRD post-Wave 4, au niveau de qualite du premier PRD, pour guider la transformation du produit vers sa version finale.

Tu dois travailler comme un excellent product strategist + architecte logiciel senior.
Je veux un document de tres haute qualite, structure, exigeant, exploitable, et sans remplissage.

Avant de rediger, tu dois lire et prendre en compte obligatoirement :

1. Le cadre projet actuel
- CLAUDE.md

2. Le PRD initial
- RamyPulse_PRD_Technique_v1.pdf

3. L'etat reel du projet actuel
- config.py
- app.py
- core/
- pages/
- scripts/
- tests/

4. Les documents post-Wave 4 deja prepares dans docs/
- docs/post-wave4-monitoring-intelligent.md
- docs/MODELE_D_INTEGRATION_CLIENT_ET_SOURCES.md
- docs/VISION_POST_WAVE4_MARKET_INTELLIGENCE.md
- docs/BRIEF_ET_PROMPT_PRD_POST_WAVE4.md

Objectif :
Produire un nouveau PRD complet, coherent et ambitieux, qui decrit comment RamyPulse doit evoluer du produit actuel vers une plateforme finale d'intelligence marketing actionnable.

Le futur produit vise doit couvrir au minimum :
- socle ABSA existant
- dashboard / explorer
- chat RAG
- What-If
- watchlists metier
- alerting intelligent
- intelligence marche et concurrence
- suivi d'evenements, campagnes, activations et influenceurs
- moteur de recommandations d'action
- rapport intelligent de campagne

Tu dois raisonner en te mettant a la place :
- d'un client entreprise
- d'une equipe produit
- d'une equipe engineering
- d'un futur integrateur

Contraintes non negociables du projet :
- jamais de score de sentiment continu, toujours 5 classes discretes
- local-first pour le coeur du produit
- pas de dependance cloud obligatoire pour faire fonctionner le coeur du systeme
- toute proposition de LLM externe puissant doit etre optionnelle, clairement isolee, et justifiee
- compatibilite avec le schema de donnees central existant
- architecture testable et industrialisable
- respect de l'esprit du projet actuel

Important :
Ne propose pas une simple accumulation de features.
Je veux un vrai produit coherent.

Tu dois faire des choix explicites sur :
- le perimetre du coeur produit
- le perimetre des modules optionnels
- le niveau d'integration client attendu
- la place exacte du RAG
- la place exacte des watchlists
- la place exacte du recommendation engine
- la place exacte du campaign tracking
- la separation entre correlation et causalite

Le document final doit etre un vrai PRD, pas une note libre.
Je veux un document comparable en niveau au premier PRD.

Le PRD attendu doit contenir au minimum :

1. Vision produit
2. Probleme business adresse
3. Personas et utilisateurs cibles
4. Positionnement du produit
5. Etat actuel du projet et limites actuelles
6. Vision cible post-Wave 4
7. Modules fonctionnels du produit final
8. Architecture logique cible
9. Modele de donnees cible
10. Registre de sources, entites metier, watchlists, campagnes
11. Moteur d'alertes
12. Moteur de recommandations
13. Campaign intelligence et influencer tracking
14. Place du RAG dans l'ensemble
15. Regles d'attribution et garde-fous
16. Workflows utilisateur majeurs
17. Integrations client et options API / import / scraping
18. Roadmap recommandee en phases
19. Risques, contraintes et arbitrages
20. Criteres de qualite et criteres d'acceptation

Exigences de qualite de redaction :
- structure nette
- ton professionnel
- decisions explicites
- hypothese clairement signalees
- pas de fluff
- pas de contradictions
- pas de promesses vagues
- distinguer MVP, version intermediaire, et vision finale

Sortie attendue :
- un document markdown complet
- titre propose : `RamyPulse_PRD_Post_Wave4_v2.md`

Important :
- ne code rien
- ne modifie pas le repo
- produis uniquement le PRD
- si une hypothese est necessaire, dis-la clairement
- si une idee des docs post-Wave 4 est faible ou dangereuse, challenge-la et propose mieux

Je veux le meilleur niveau de raisonnement possible.
Je prefere un document exigeant et realiste a un document flatteur mais faible.
```

## 6. Position recommandee
Le bon usage de ce document est :

1. donner ce brief + le prompt a un agent de recherche avance
2. lui faire produire un nouveau PRD v2
3. comparer ce PRD v2 avec le PRD initial
4. ensuite seulement lancer une future phase d'implementation

## 7. Resultat attendu
Si le prompt est bien execute, le resultat doit etre :

- un document directeur unique
- plus mature que les notes actuelles
- assez precis pour piloter la future evolution du produit
- assez exigeant pour eviter un glissement flou de scope
