# RamyPulse — Prompts d'Implémentation pour Agents de Codage
## Plan de Parallélisation Multi-Agents

---

## PRINCIPE

```text
4 vagues, 3 agents en parallèle

Vague 1 (Jours 1-2) → 3 agents simultanés, 0 dépendance
Vague 2 (Jours 3-4) → 3 agents simultanés, dépend de Vague 1
Vague 3 (Jours 5-6) → 3 agents simultanés, dépend de Vague 2
Vague 4 (Jours 7-8) → 1 agent, intégration + soumission
```

## WORKFLOW CONCRET

Ouvre 3 terminaux/fenêtres dans Antigravity.

- Terminal 1 = Claude Code
- Terminal 2 = Codex
- Terminal 3 = Copilot / Gemini CLI

Ne fais pas simplement `git checkout -b` dans 3 terminaux sur le même dossier.
Chaque agent doit travailler dans son propre `git worktree` et sur sa propre branche.

### Préparation de la vague

```bash
git checkout main
git pull

# Vague 1
git worktree add ../ramypulse-claude -b feat/config-normalizer
git worktree add ../ramypulse-codex -b feat/aspect-nss
git worktree add ../ramypulse-copilot -b feat/whatif-simulator
```

Ensuite :

- Terminal 1 travaille dans `../ramypulse-claude`
- Terminal 2 travaille dans `../ramypulse-codex`
- Terminal 3 travaille dans `../ramypulse-copilot`

Copie-colle le prompt correspondant dans chaque agent.

### Règle critique

Chaque agent travaille dans son propre `git worktree` ET sur sa propre branche Git.
C'est ce qui empêche réellement les conflits de checkout, d'index et de fichiers.
Les agents ne touchent jamais les mêmes fichiers dans la même vague.

### Superpowers

Chaque agent doit :

1. Vérifier au démarrage si `Superpowers` est disponible dans son environnement
2. Si `Superpowers` n'est pas disponible, l'installer via le mécanisme natif de l'outil avant de commencer
3. Utiliser `Superpowers` pour structurer le travail TDD, la décomposition des tâches et la discipline d'exécution quand l'environnement le supporte

Important :

- `Superpowers` peut aider un agent individuellement
- L'orchestration globale entre Claude Code, Codex et Copilot/Gemini reste manuelle
- Le chef d'orchestre global, c'est toi

### Merge

Ne merge pas dans `main` dès qu'un agent finit.

Workflow recommandé :

1. L'agent termine sa branche
2. Les tests ciblés de la branche passent
3. Revue rapide du résultat
4. Merge dans `integration/wave-N`
5. Quand les 3 branches de la vague sont intégrées, exécuter les tests de vague
6. Seulement ensuite merge dans `main`

Exemple Vague 1 :

```bash
git checkout main
git pull
git checkout -b integration/wave-1

git merge feat/config-normalizer
git merge feat/aspect-nss
git merge feat/whatif-simulator

# lancer les tests de la vague

git checkout main
git merge integration/wave-1
```

---

## RÈGLES AVANT DE COMMENCER

1. Chaque agent travaille dans son propre `git worktree` et sa propre branche
2. Merge dans `main` uniquement après validation complète de la vague
3. Tous les agents lisent le `CLAUDE.md` et respectent les standards
4. Le PRD (`RamyPulse_PRD_Technique_v1.pdf`) est dans le repo — chaque agent doit le consulter
5. Avant chaque vague, figer les contrats d'interface des modules partagés
6. Si une dépendance n'est pas prête, le mock doit respecter exactement le contrat cible
7. TDD obligatoire : écrire les tests avant l'implémentation
8. Périmètre strict : ne pas modifier de fichiers hors scope
9. Une branche n'est terminée que si les tests ciblés passent et si un court résumé des hypothèses / mocks est fourni

### Contrats à figer avant chaque vague

- Inputs / outputs des fonctions publiques
- Colonnes des DataFrames
- Formats des dicts retournés
- Chemins des artifacts produits
- Comportement en cas d'entrée vide / erreur

---

## VAGUE 1 — FONDATIONS (0 dépendance entre eux)
> Lancer les 3 agents EN MÊME TEMPS

### AGENT A — Claude Code (branche: feat/config-normalizer)

```text
Tu travailles dans ton propre worktree et sur la branche feat/config-normalizer.

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Claude Code
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton TDD et ta séquence de travail
4. Lis le CLAUDE.md à la racine
5. Consulte le PRD pour lever les ambiguïtés

Tu dois implémenter 2 fichiers pour le projet RamyPulse.

FICHIER 1: config.py
- Fichier central de configuration, aucune logique métier
- Contenu: BASE_DIR, DATA_DIR, MODELS_DIR, DZIRIBERT_MODEL_PATH, WHISPER_MODEL_SIZE, OLLAMA_MODEL (llama3.2:3b), OLLAMA_BASE_URL, FAISS_INDEX_PATH, EMBEDDING_MODEL (multilingual-e5-base), EMBEDDING_DIM (768), SENTIMENT_LABELS = ["très_positif", "positif", "neutre", "négatif", "très_négatif"], ASPECT_LIST = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"], CHANNELS = ["facebook", "google_maps", "audio", "youtube"], NSS formula documentée inline, APIFY_API_KEY optionnel
- Dépendances: python-dotenv, pathlib, os
- Les chemins doivent créer les dossiers automatiquement s'ils n'existent pas
- Test: config.py est importable sans erreur, tous les chemins existent

FICHIER 2: core/ingestion/normalizer.py
- Module de nettoyage et normalisation textuelle dual-script
- Input: texte brut (str) — Arabizi, Arabe, Français, ou mélange
- Output: dict {"normalized": str, "original": str, "script_detected": "arabic"|"latin"|"mixed", "language": "darija"|"french"|"mixed"}
- Algorithme:
  1) Détection script: compter caractères arabes vs latins
  2) Si Arabizi: table substitution phonétique: 7→ح, 3→ع, 9→ق, 5→خ, 2→ء, 8→غ, 6→ط, ch→ش, gh→غ, kh→خ, th→ث, dh→ذ, sh→ش
  3) Unification graphèmes arabes: normaliser alef (أإآ→ا), ta marbuta (ة→ه), ya (ى→ي)
  4) Supprimer tatweel (ـ) et diacritiques
  5) Lowercase pour partie latine
  6) Nettoyer: URLs, mentions @, hashtags, emojis excessifs, espaces multiples
- Dépendances: re, unicodedata (stdlib uniquement)
- ÉCRIS LES TESTS D'ABORD dans tests/test_normalizer.py:
  - "ramy m3andhoumch ta3m" → texte arabe normalisé
  - "le jus Ramy c'est bon" → conservé en français, lowercase
  - "7aja mli7a bzaf" → conversion Arabizi complète
  - Texte mixte arabe/français
  - Texte vide, texte avec emojis, texte avec URLs
- Objectif cible: 50+ exemples de test, transformation cohérente

Commence par les tests, puis implémente. Vérifie que tous les tests passent.
Ne touche à aucun autre fichier hors scope.
```

### AGENT B — Codex (branche: feat/aspect-nss)

```text
Tu travailles dans ton propre worktree et sur la branche feat/aspect-nss.

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Codex
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton TDD et ta séquence de travail
4. Lis le CLAUDE.md à la racine
5. Consulte le PRD pour lever les ambiguïtés

Tu dois implémenter 2 fichiers pour le projet RamyPulse.

FICHIER 1: core/analysis/aspect_extractor.py
- Extracteur d'aspects basé sur dictionnaire bilingue prédéfini
- Input: texte nettoyé (str)
- Output: liste de dict [{"aspect": str, "mention": str, "start": int, "end": int}]
- Dépendances: re, config (pour ASPECT_LIST)
- Dictionnaire bilingue ASPECT_KEYWORDS:
  goût: [ta3m, طعم, goût, saveur, madha9, bnin, ldid, mli7, doux, amer, sucré]
  emballage: [bouteille, plastique, تغليف, 9ar3a, emballage, packaging, 3olba, couvercle, bouchon, fuite]
  prix: [ghali, rkhis, سعر, prix, cher, pas_cher, prix_abordable, t7ayol, promotions]
  disponibilité: [nlgah, ma_kaynch, متوفر, disponible, rupture, yla9awh, ma_lgitouch]
  fraîcheur: [bared, skhoun, طازج, frais, froid, chaud, périmé, fraîcheur, date, expiration]
- Algorithme: pour chaque aspect → compiler regex (word boundary, case-insensitive) → scanner texte → enregistrer matches avec positions
- ÉCRIS LES TESTS D'ABORD dans tests/test_aspect_extractor.py:
  - "l'emballage ytl3 kol mra" → aspect=emballage
  - "le goût est bon mais ghali bzaf" → aspects=[goût, prix]
  - "ramy disponible partout" → aspect=disponibilité
  - Texte sans aucun aspect → liste vide
  - Texte avec multiple aspects → tous détectés
  - Positions start/end correctes
- Objectif cible: bon recall sur les cas de test représentatifs

FICHIER 2: core/analysis/nss_calculator.py
- Calcul du Net Sentiment Score multi-dimensionnel
- Input: DataFrame pandas avec colonnes [text, sentiment_label, channel, aspect, source_url, timestamp]
- Output: dict {"nss_global": float, "nss_by_channel": dict, "nss_by_aspect": dict, "trends": DataFrame, "volume_total": int, "distribution": dict}
- Formule: NSS = (nb_très_positif + nb_positif - nb_négatif - nb_très_négatif) / total × 100
- Plage: [-100, +100]
- Algorithme:
  1) Compter distribution des 5 classes
  2) Appliquer formule NSS (positifs = très_positif + positif, négatifs = négatif + très_négatif)
  3) Grouper par canal → NSS par canal
  4) Grouper par aspect → NSS par aspect
  5) Grouper par période (semaine) → tendance temporelle
- GÉRER: division par zéro si volume=0
- Dépendances: pandas, config
- ÉCRIS LES TESTS D'ABORD dans tests/test_nss_calculator.py:
  - 100% positif → NSS = +100
  - 100% négatif → NSS = -100
  - 50/50 → NSS = 0
  - Avec neutres → vérifier formule exacte
  - DataFrame vide → gérer sans crash
  - NSS par canal: chaque canal a son propre score
  - NSS par aspect: chaque aspect a son propre score
  - Trends: groupby semaine fonctionne
- Critère: résultats cohérents avec comptage manuel

Commence par les tests, puis implémente. Vérifie que tous les tests passent.
Ne touche à aucun autre fichier hors scope.
```

### AGENT C — Copilot / Gemini CLI (branche: feat/whatif-simulator)

```text
Tu travailles dans ton propre worktree et sur la branche feat/whatif-simulator.

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Copilot / Gemini CLI
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton TDD et ta séquence de travail
4. Lis le CLAUDE.md à la racine
5. Consulte le PRD pour lever les ambiguïtés

Tu dois implémenter 2 fichiers pour le projet RamyPulse.

FICHIER 1: core/whatif/simulator.py
- Moteur de simulation What-If pour recalculer le NSS
- Input: aspect (str), scénario ("neutraliser"|"améliorer"|"dégrader"), DataFrame ABSA complète
- Output: dict {"nss_actuel": float, "nss_simule": float, "delta": float, "interpretation": str, "affected_count": int, "nss_by_channel_simulated": dict}
- Algorithme:
  1) COPIER le DataFrame (ne jamais modifier l'original)
  2) Identifier les enregistrements de l'aspect ciblé
  3) Selon scénario:
     - Neutraliser: supprimer ces enregistrements du calcul
     - Améliorer: remapper très_négatif→négatif, négatif→neutre, neutre→positif, positif→très_positif
     - Dégrader: remapper inversement
  4) Recalculer NSS sur DataFrame modifié
  5) delta = nss_simulé - nss_actuel
  6) Générer interprétation: "L'amélioration de {aspect} augmenterait le NSS de {delta} points"
- Dépendances: pandas, core.analysis.nss_calculator (IMPORTE-LE)
- ÉCRIS LES TESTS D'ABORD dans tests/test_simulator.py:
  - Neutraliser l'emballage quand tout est négatif → NSS monte
  - Améliorer le goût → NSS augmente
  - Dégrader le prix → NSS diminue
  - DataFrame original NON modifié (vérifier avec .copy())
  - Aspect inexistant → affected_count=0, delta=0
  - Interprétation cohérente avec le signe du delta
- Critère: delta vérifié manuellement sur petit dataset

FICHIER 2: scripts/01_collect_data.py
- Script de collecte batch avec fallback dataset
- Doit tenter la collecte locale (sources déjà présentes) puis fallback local dataset 45K si échec
- Pour le PoC: le script doit DIRECTEMENT charger le fallback local (on ajoutera les scrapers plus tard)
- Algorithme:
  1) Tenter de charger data/raw/facebook_raw.parquet (si existe)
  2) Tenter de charger data/raw/google_raw.parquet (si existe)
  3) Si rien n'existe: charger le dataset fallback Algerian Dialect 45K depuis un artifact local du repo (ex: data/demo/)
  4) Sauver dans data/raw/ au format Parquet
  5) Logger le résumé: sources, volume
- Dépendances: pandas, requests, logging, config
- ÉCRIS LES TESTS D'ABORD dans tests/test_collect_data.py:
  - Le script produit au moins un fichier dans data/raw/
  - Le Parquet a les colonnes attendues
  - Log de résumé présent
  - Le script ne dépend pas d'un service cloud pour fonctionner
- Critère: le script ne crash jamais, fallback local toujours fonctionnel

Commence par les tests, puis implémente. Vérifie que tous les tests passent.
Ne touche à aucun autre fichier hors scope.
```

---

## VAGUE 2 — MOTEUR IA (dépend de la Vague 1)
> Attendre que la Vague 1 soit mergée dans `main`, puis lancer 3 agents

### AGENT A — Claude Code (branche: feat/sentiment-classifier)

```text
git checkout main && git pull && git worktree add ../ramypulse-wave2-claude -b feat/sentiment-classifier

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Claude Code
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton TDD et ta séquence de travail
4. Lis le CLAUDE.md et le PRD pour le contexte complet

Implémente core/analysis/sentiment_classifier.py pour le projet RamyPulse.

- Classifieur de sentiment basé sur DziriBERT (alger-ia/dziribert)
- Input: texte nettoyé (str) ou liste de textes (list[str])
- Output: dict {"label": "très_positif"|"positif"|"neutre"|"négatif"|"très_négatif", "confidence": float, "logits": list[float]}
- Modèle: alger-ia/dziribert + classification head (5 classes) fine-tunée
- Fine-tuning spec:
  Dataset: charger depuis data/demo/ (dataset Algerian Dialect 45K)
  Split: 80/10/10 (train/val/test)
  Epochs: 3-5, LR: 2e-5, Batch: 16, Optimizer: AdamW, Max seq length: 128
- Algorithme inférence:
  1) Tokenizer DziriBERT encoder le texte
  2) Forward pass → logits (5 classes)
  3) Softmax → probabilités
  4) Argmax → label
  5) Retourner label, confidence, logits
- Mode batch: DataLoader batch_size=32 → résultats en Parquet
- FALLBACK si fine-tuning trop long: utiliser le modèle pré-entraîné avec classification head random initialisée (on fine-tunera séparément)
- TESTS dans tests/test_sentiment_classifier.py:
  - Le modèle charge sans erreur
  - Inférence unitaire retourne le bon format
  - Batch inférence fonctionne
  - Confidence est entre 0 et 1
  - Labels sont dans la liste attendue
  - Texte vide géré proprement
- Objectif cible: accuracy > 75% sur test set après fine-tuning

Commence par les tests, puis implémente. Vérifie que les tests passent.
Ne touche à aucun autre fichier hors scope.
```

### AGENT B — Codex (branche: feat/absa-engine)

```text
git checkout main && git pull && git worktree add ../ramypulse-wave2-codex -b feat/absa-engine

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Codex
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton TDD et ta séquence de travail
4. Lis le CLAUDE.md et le PRD

Implémente core/analysis/absa_engine.py pour le projet RamyPulse.

Ce fichier dépend de aspect_extractor.py et du contrat de sentiment_classifier.py.
Si sentiment_classifier.py n'est pas encore mergé, mocke son interface dans les tests et continue.

- Orchestre le pipeline ABSA complet: aspect extraction + sentiment classification
- Input: DataFrame avec colonnes [text, channel, source_url, timestamp]
- Output: DataFrame enrichi avec colonnes ajoutées [sentiment_label, confidence, aspects (list), aspect_sentiments (list of dict)]
- Algorithme:
  1) Pour chaque texte:
     a) Classifier sentiment global via sentiment_classifier
     b) Extraire aspects via aspect_extractor
     c) Pour chaque aspect: extraire la phrase contenant la mention, classifier le sentiment de cette phrase
     d) Stocker aspect_sentiments = [{aspect, mention, sentiment, confidence}]
  2) Si aucun aspect: aspect_sentiments = [] (sentiment global reste)
  3) Sauver en data/processed/annotated.parquet
- Dépendances: pandas, core.analysis.sentiment_classifier, core.analysis.aspect_extractor
- TESTS dans tests/test_absa_engine.py:
  - DataFrame de sortie a toutes les colonnes requises
  - Texte avec 1 aspect → 1 aspect_sentiment
  - Texte avec 3 aspects → 3 aspect_sentiments
  - Texte sans aspect → aspect_sentiments vide, sentiment global présent
  - Sauvegarde Parquet fonctionne
- Critère: traitement 100 textes sans crash

Commence par les tests (mock sentiment_classifier et aspect_extractor si besoin), puis implémente.
Ne touche à aucun autre fichier hors scope.
```

### AGENT C — Copilot / Gemini CLI (branche: feat/rag-pipeline)

```text
git checkout main && git pull && git worktree add ../ramypulse-wave2-copilot -b feat/rag-pipeline

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Copilot / Gemini CLI
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton TDD et ta séquence de travail
4. Lis le CLAUDE.md et le PRD

Implémente 4 fichiers du module RAG pour le projet RamyPulse.

FICHIER 1: core/rag/embedder.py
- Génère des embeddings via multilingual-e5-base
- Input: str ou list[str]
- Output: numpy array (n, 768)
- IMPORTANT: préfixer "query: " pour les questions, "passage: " pour les documents (requis par e5)
- Normaliser L2

FICHIER 2: core/rag/vector_store.py
- Index FAISS HNSW + metadata JSON
- Création: IndexHNSWFlat(768, 32), ajouter vecteurs, sauver index + metadata JSON
- Recherche: charger index, encoder query, faiss.search(vec, k) → distances, indices → récupérer metadata
- Sauvegarde/chargement sur disque

FICHIER 3: core/rag/retriever.py
- Recherche hybride dense (FAISS) + sparse (BM25), fusion par Reciprocal Rank Fusion
- Input: question (str), top_k=5
- Output: [{"text": str, "channel": str, "url": str, "timestamp": str, "score": float}]
- RRF: score = sum(1/(60+rank_i)) pour chaque méthode

FICHIER 4: core/rag/generator.py
- Génération via Ollama (llama3.2:3b)
- Input: question + top_k chunks
- Output: {"answer": str, "sources": [...], "confidence": "high"|"medium"|"low"}
- Prompt système: "Tu es un analyste de sentiment pour la marque Ramy. Réponds UNIQUEMENT à partir des extraits fournis. Cite les sources entre crochets [Source N]. Si pas assez d'info, dis-le. Réponds en français. Format JSON."
- VÉRIFIER que les sources citées existent dans les chunks

TESTS dans tests/test_rag/:
- test_embedder.py: vecteurs dim 768, batch fonctionne
- test_vector_store.py: save/load, recherche fonctionnelle
- test_retriever.py: hybride retourne résultats, chaque résultat a une source
- test_generator.py: réponse contient source, "je ne sais pas" si chunks vides (MOCK ollama pour les tests)
- Objectif cible: pipeline complet query → réponse fonctionne

Commence par les tests de chaque fichier, puis implémente un par un dans l'ordre.
Ne touche à aucun autre fichier hors scope.
```

---

## VAGUE 3 — INTERFACE STREAMLIT (dépend de Vagues 1+2)
> Attendre que tout soit mergé, puis lancer 3 agents

### AGENT A — Claude Code (branche: feat/dashboard-explorer)

```text
git checkout main && git pull && git worktree add ../ramypulse-wave3-claude -b feat/dashboard-explorer

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Claude Code
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton travail
4. Lis le CLAUDE.md

Implémente 3 fichiers Streamlit pour RamyPulse.

FICHIER 1: app.py
- Point d'entrée: streamlit run app.py
- st.set_page_config(page_title="RamyPulse", layout="wide", page_icon="📊")
- Sidebar avec titre "RamyPulse" et navigation vers les 4 pages
- Utilise la structure pages/ de Streamlit (multi-page app)

FICHIER 2: pages/01_dashboard.py
- Page d'accueil: KPIs + matrice ABSA + trends
- Charge data/processed/annotated.parquet
- Row de 4 KPI cards: NSS global (avec couleur vert/rouge), volume total, nb canaux, période
- Heatmap Plotly: matrice 5 aspects × 5 sentiments (colorscale RdYlGn divergent)
- Bar chart horizontal: NSS par canal
- Line chart: évolution NSS par semaine
- Filtres sidebar: période (date_input), canal (multiselect), aspect (multiselect)
- Design: couleurs professionnelles, pas d'emojis excessifs, layout responsive

FICHIER 3: pages/02_explorer.py
- Explorateur de données avec filtres avancés
- Filtres multiselect: canal, aspect, sentiment, période
- Donut chart: répartition des sentiments (filtré)
- Tableau st.dataframe paginé: texte (tronqué 100 chars), sentiment, aspect, canal, date, source
- Expander sur chaque ligne: texte complet + lien source cliquable
- Counter affiché: "X résultats sur Y total"

CRITÈRE: les 3 fichiers fonctionnent ensemble. streamlit run app.py affiche le dashboard sans erreur. Les filtres mettent à jour toutes les visualisations.

NOTE: si data/processed/annotated.parquet n'existe pas encore, crée un MOCK DataFrame de 500 lignes avec des données réalistes pour pouvoir développer l'interface.

Teste manuellement en lançant streamlit run app.py.
Ne touche à aucun autre fichier hors scope.
```

### AGENT B — Codex (branche: feat/chat-rag)

```text
git checkout main && git pull && git worktree add ../ramypulse-wave3-codex -b feat/chat-rag

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Codex
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton travail
4. Lis le CLAUDE.md

Implémente pages/03_chat.py — Interface Q&A RAG avec provenance pour RamyPulse.

- Interface de chat Streamlit pour poser des questions en langage naturel
- Utilise core.rag.retriever et core.rag.generator
- Algorithme:
  1) st.chat_input("Posez votre question sur les avis clients Ramy...")
  2) Historique de conversation dans st.session_state
  3) Quand question reçue: afficher dans st.chat_message("user")
  4) Appeler retriever.search(question, top_k=5)
  5) Appeler generator.generate(question, chunks)
  6) Afficher réponse dans st.chat_message("assistant")
  7) Sous la réponse: st.expander pour chaque source
     - Texte du chunk
     - Canal (avec badge coloré)
     - URL cliquable ou timestamp audio
     - Score de pertinence
  8) Badge de confiance: 🟢 haute / 🟡 moyenne / 🔴 basse

- Exemples de questions à supporter:
  "Que pensent les clients de l'emballage Ramy?"
  "Quels sont les principaux problèmes remontés?"
  "Comment est perçu le prix du jus Ramy Premium?"

- Si le RAG n'est pas encore fonctionnel: créer un MODE DEMO qui retourne des réponses mockées réalistes

CRITÈRE: l'interface est fluide, chaque réponse a des sources, pas d'erreur visible.
Ne touche à aucun autre fichier hors scope.
```

### AGENT C — Copilot / Gemini CLI (branche: feat/whatif-page)

```text
git checkout main && git pull && git worktree add ../ramypulse-wave3-copilot -b feat/whatif-page

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Copilot / Gemini CLI
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton travail
4. Lis le CLAUDE.md

Implémente pages/04_whatif.py — Page de simulation What-If pour RamyPulse.

- Outil de simulation: "Si on améliore l'emballage, quel impact sur le NSS?"
- Utilise core.whatif.simulator
- Interface:
  1) st.selectbox: choisir l'aspect (goût, emballage, prix, disponibilité, fraîcheur)
  2) st.radio: scénario (Neutraliser, Améliorer, Dégrader) avec explication de chaque option
  3) Bouton "Simuler"
  4) Résultat:
     - 3 metric cards en row: NSS actuel | NSS simulé | Delta (avec flèche ↑↓)
     - Bar chart Plotly comparatif avant/après par canal
     - Texte d'interprétation généré (ex: "Améliorer l'emballage augmenterait le NSS de +15 points, passant de 32 à 47. Cela placerait Ramy au-dessus du seuil 'Bon' (>20).")
  5) Section "Détails" en expander: nombre de commentaires affectés, répartition avant/après

- Design: utiliser des couleurs vert pour amélioration, rouge pour dégradation, gris pour neutralisation
- Si simulator.py pas encore disponible: mode MOCK avec données fictives

CRITÈRE: la simulation est visuellement claire, le delta est correct, l'interprétation est cohérente.
Ne touche à aucun autre fichier hors scope.
```

---

## VAGUE 4 — SCRIPTS + POLISH (après merge de tout)
> Un seul agent suffit

### AGENT A — Claude Code (branche: feat/scripts-polish)

```text
git checkout main && git pull && git worktree add ../ramypulse-wave4-claude -b feat/scripts-polish

Avant de commencer :
1. Vérifie si Superpowers est disponible dans ton environnement Claude Code
2. Si ce n'est pas le cas, installe-le via le mécanisme natif de ton outil
3. Utilise-le pour structurer ton travail final d'intégration
4. Lis le CLAUDE.md et le PRD

Implémente les scripts d'intégration et la démo finale pour RamyPulse.

FICHIER 1: scripts/02_process_data.py
- Charge data/raw/*.parquet → applique normalizer.normalize() sur chaque texte → unifie schéma → filtre (<3 mots ou >500 mots) → déduplique → sauve data/processed/clean.parquet

FICHIER 2: scripts/03_classify_sentiment.py
- Charge data/processed/clean.parquet → applique absa_engine sur tout le DataFrame → sauve data/processed/annotated.parquet
- Affiche progression avec tqdm
- Log le résumé: volume, distribution sentiments, aspects détectés

FICHIER 3: scripts/04_build_index.py
- Charge data/processed/annotated.parquet → encode via embedder → construit index FAISS → sauve dans data/embeddings/
- Initialise aussi le BM25 index

FICHIER 4: scripts/05_run_demo.py
- Script one-click qui:
  1) Vérifie que tous les prérequis sont OK (Ollama running, modèles chargés, data présente)
  2) Lance streamlit run app.py avec les bons paramètres
  3) Affiche un résumé de l'état du système

FICHIER 5: requirements.txt (vérifier que tout est correct et installable)

TEST FINAL: exécuter scripts/05_run_demo.py → le dashboard s'ouvre, toutes les pages fonctionnent, le Q&A répond avec sources.
Ne touche à aucun autre fichier hors scope.
```

---

## RÉSUMÉ — TIMELINE DE PARALLÉLISATION

```text
JOUR 1-2:
┌──────────────────────────────────────────────────┐
│ VAGUE 1 — 3 agents en parallèle                  │
│ Agent A: config.py + normalizer.py               │
│ Agent B: aspect_extractor.py + nss_calculator.py │
│ Agent C: simulator.py + collect_data.py          │
└──────────────────────────────────────────────────┘
         ↓ merge dans integration/wave-1 ↓
         ↓ validation ↓
         ↓ merge dans main ↓

JOUR 3-4:
┌──────────────────────────────────────────────────┐
│ VAGUE 2 — 3 agents en parallèle                  │
│ Agent A: sentiment_classifier.py                 │
│ Agent B: absa_engine.py                          │
│ Agent C: embedder + vector_store + retriever +   │
│          generator (4 fichiers RAG)              │
└──────────────────────────────────────────────────┘
         ↓ merge dans integration/wave-2 ↓
         ↓ validation ↓
         ↓ merge dans main ↓

JOUR 5-6:
┌──────────────────────────────────────────────────┐
│ VAGUE 3 — 3 agents en parallèle                  │
│ Agent A: app.py + dashboard + explorer           │
│ Agent B: chat RAG page                           │
│ Agent C: what-if page                            │
└──────────────────────────────────────────────────┘
         ↓ merge dans integration/wave-3 ↓
         ↓ validation ↓
         ↓ merge dans main ↓

JOUR 7-8:
┌──────────────────────────────────────────────────┐
│ VAGUE 4 — 1 agent                                │
│ Scripts d'intégration + test final + soumission  │
└──────────────────────────────────────────────────┘
```

---

## NOTES IMPORTANTES

### Comment gérer les dépendances entre agents

- Vague 1: AUCUNE dépendance → les 3 agents sont totalement indépendants
- Vague 2: dépend de config.py et normalizer.py → merger Vague 1 d'abord
- Agent B Vague 2 (`absa_engine`) dépend de `sentiment_classifier` et `aspect_extractor` → si `sentiment_classifier` n'est pas fini, mocker son interface dans les tests
- Vague 3: dépend de tout le `core/` → merger Vague 2 d'abord, mais les pages peuvent MOCK les données manquantes

### Comment merger

```bash
# Après la fin de la vague 1 :
git checkout main
git pull
git checkout -b integration/wave-1
git merge feat/config-normalizer
git merge feat/aspect-nss
git merge feat/whatif-simulator

# Lancer les tests de vague

git checkout main
git merge integration/wave-1
```

Même logique pour `integration/wave-2` et `integration/wave-3`.

### Si un agent est bloqué

- Lui dire: "Mock la dépendance manquante et continue. On branchera le vrai module au merge."
- Exemple: si `absa_engine.py` a besoin de `sentiment_classifier.py` pas encore fini, l'agent crée un mock qui retourne toujours `{"label": "neutre", "confidence": 0.5, "logits": []}` et continue avec ce contrat

### Ce qu'il ne faut pas faire

- Ne pas faire `git checkout -b` dans 3 terminaux sur le même dossier
- Ne pas merger dans `main` au fil de l'eau sans validation de vague
- Ne pas inventer un contrat local différent du contrat cible
- Ne pas laisser un mock casser l'interface finale

