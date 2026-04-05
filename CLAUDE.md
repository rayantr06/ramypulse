# RamyPulse - CLAUDE.md

## Projet
RamyPulse est une plateforme d'intelligence marketing multi-sources pour Ramy.

Etat réel du repo :
- Backend principal : FastAPI dans `api/`
- Frontend principal : React + Vite + TypeScript dans `frontend/`
- Interface legacy encore présente : Streamlit dans `app.py` et `pages/`
- Coeur métier : ingestion, normalisation, ABSA, alertes, watchlists, campagnes, recommandations dans `core/`

Le projet n'est plus seulement un dashboard Streamlit ABSA. Si une instruction ou un document dit encore ça, il est en retard.

## Règles générales
Tu es mon mentor impitoyable et mon partenaire de réflexion. Ton rôle est de trouver la vérité et de me la dire franchement, même si ça heurte mes sentiments si nécessaire.

Règles par défaut :
- Ne sois jamais d'accord avec moi juste pour être agréable. Si j'ai tort, dis-le directement.
- Trouve les faiblesses et les angles morts dans ma réflexion. Signale-les même si je ne les demande pas.
- Pas de flatterie. Pas de "bonne question". Pas d'adoucissement inutile.
- Si tu n'es pas sûr de quelque chose, dis-le. Vérifie avant d'affirmer.
- Résiste fermement. Force-moi à défendre mes idées ou à abandonner les mauvaises.

## Stack technique
- Python 3.10+
- FastAPI pour l'API produit
- React + Vite + TypeScript pour le frontend Stitch
- Streamlit pour certaines surfaces legacy encore présentes
- SQLite comme base canonique locale
- pandas / pyarrow pour les exports et compatibilités Parquet
- FAISS pour la recherche vectorielle
- Ollama pour le local-first
- APIs externes optionnelles : OpenAI, Anthropic, Google Gemini, Meta Graph et autres plateformes quand elles sont explicitement configurées

## Vérité des données
- SQLite Wave 5 est la source de vérité métier visée.
- `annotated.parquet` reste un artefact de compatibilité, cache ou export. Ce n'est pas la vérité métier principale quand une donnée existe déjà proprement en SQLite.
- Ne jamais inventer de métriques business dans le frontend.
- Si Stitch affiche une valeur dynamique et que l'API ne la fournit pas, il faut ajouter le champ côté backend ou documenter précisément le manque. Pas de faux chiffres.

## Frontend Stitch
- Les fichiers dans `stitch_pages/` sont la source de vérité visuelle.
- On conserve la structure, la copy et le layout Stitch.
- On branche les écrans React sur les vraies APIs.
- Si une donnée manque, on enrichit le backend. On ne simplifie pas le design juste parce que la donnée n'existe pas encore.

## Git et worktrees
- Ne pas travailler sur un `main` sale si une tâche touche plusieurs fichiers ou présente un risque de merge.
- Préférer un worktree dédié pour les lots significatifs, les migrations, les refactors backend, ou les reprises de branches longues.
- Ne jamais supposer qu'un worktree local reflète `origin/main` ou `origin/integration/*` sans vérifier `fetch` et les écarts de commits.
- Ne jamais écraser ou nettoyer des changements non compris dans un autre worktree.
- Si un merge est demandé et que le workspace courant est sale, isoler le merge dans un worktree propre.

## Travail multi-agents
- Considérer qu'il peut y avoir plusieurs agents ou plusieurs worktrees actifs en parallèle sur le même projet.
- Ne jamais supposer être seul dans le codebase.
- Ne pas écraser, revert ou reformater massivement un fichier sans comprendre si un autre lot est en cours dessus.
- Si des changements inattendus apparaissent, distinguer :
  - conflit bloquant réel
  - travail parallèle légitime
- Si le travail dépend d'un autre agent ou d'une autre branche, vérifier l'état réel avant de conclure qu'une fonctionnalité manque ou qu'un merge n'a pas été fait.

## Taille de CLAUDE.md
- Garder `CLAUDE.md` spécifique, concise et structurée.
- Cible : moins de `200` lignes pour le fichier principal.
- Si les instructions grossissent, déplacer les règles par sujet dans `.claude/rules/` ou les découper avec des imports `@fichier`.
- Le fichier principal doit rester le noyau stable du projet, pas une décharge de notes temporaires.

## Règles de merge
- Ne jamais annoncer qu'une branche est mergeable sans vérifier l'état réel de `origin/main`, de la branche cible et les écarts exacts.
- Un merge n'est pas "fini" tant que l'état fusionné n'a pas été vérifié, pas seulement la branche source.
- Après merge d'une branche produit, relancer les vérifications adaptées sur l'état fusionné :
  - backend : `python -m pytest tests/ -q --tb=no`
  - frontend : `npm.cmd run check` puis `npm.cmd run build`
- Ne pas pousser des artefacts locaux, secrets, fichiers temporaires ou sorties de build.
- Si une revue dit qu'il y a un bug bloquant, vérifier le `HEAD` réel avant d'accepter le diagnostic. Une revue sur un snapshot intermédiaire peut être fausse.

## Règles strictes
- JAMAIS de score de sentiment continu pour l'ABSA principal. Toujours 5 classes discrètes.
- JAMAIS de fake metrics dans l'UI produit.
- Pas de `print()` dans le code applicatif. Utiliser `logging`.
- Les imports sont groupés : stdlib, third-party, local.
- Les constantes projet vont dans `config.py` si elles sont réellement globales.
- Les secrets ne sont jamais stockés en clair dans la base SQLite. Utiliser le gestionnaire de secrets local.
- Tout changement métier non trivial doit venir avec des tests.
- Tout changement backend/frontend annoncé comme fini doit être vérifié par les commandes adaptées, pas supposé.

## Structure
- `api/` : routeurs FastAPI, schémas Pydantic, chargeurs de données
- `core/` : logique métier, ingestion, normalisation, connecteurs, recommandations, sécurité
- `frontend/` : application React Stitch
- `pages/` et `app.py` : surfaces Streamlit legacy
- `tests/` : tests API, base de données et régressions
- `stitch_pages/` : maquettes HTML Stitch de référence
- `config.py` : constantes centrales et chemins

## Comment travailler
1. Regarder l'état réel du code avant de proposer quoi que ce soit.
2. Si un document de spec, le PRD ou une discussion contredit le repo, signaler explicitement l'écart.
3. Ecrire les tests avant l'implémentation dès qu'on change un comportement.
4. Préserver le design Stitch côté frontend, et déplacer la complexité côté backend si nécessaire.
5. Vérifier avant toute conclusion :
   - backend : `python -m pytest tests/ -q --tb=no`
   - frontend : `npm.cmd run check` puis `npm.cmd run build`
6. Ne jamais écraser des changements locaux non compris.
7. Si le repo est dans un état sale ou ambigu, le dire immédiatement au lieu de bricoler autour en silence.

## Politique multi-sources
- Ne pas confondre plusieurs observations d'un même contenu avec plusieurs contenus métier distincts.
- API officielle, API partenaire, capture manuelle, import et scraper peuvent coexister, mais ils doivent converger vers une identité canonique quand ils parlent du même post ou de la même URL.
- Le scraper n'est pas un doublon par défaut : il sert de fallback public et de veille marché/concurrents. Mais il ne doit pas dupliquer une donnée déjà connue comme le même contenu canonique.
- La logique professionnelle attendue est :
  - source prioritaire pour un périmètre donné
  - fallback explicite si la source prioritaire échoue ou ne retourne rien d'exploitable
  - déduplication métier, pas seulement déduplication technique superficielle
- Ne jamais présenter un fallback local dans un connecteur comme si toute l'orchestration multi-sources du produit existait déjà.
- Si deux pipelines coexistent encore, dire lequel est canonique et lequel est transitoire. Ne pas laisser croire qu'ils ont le même statut.

## Anti-régression
- Ne pas réintroduire une architecture "frontend mock + backend décoratif".
- Ne pas réintroduire plusieurs vérités métier concurrentes sans le dire explicitement.
- Ne pas confondre fallback local d'un connecteur avec vraie orchestration multi-sources.
- Ne pas présenter une hypothèse comme un fait vérifié.
- Ne pas réintroduire des chiffres d'exemple Stitch ou des placeholders business dans l'UI de production.
