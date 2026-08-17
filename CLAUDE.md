# RamyPulse

Veille marketing pour marques algériennes. Backend FastAPI + SQLite, frontend React.
Deux chantiers actifs : le produit lui-même, et le SLM V2 qui analysera les commentaires.

## Environnement — Windows

Le projet tourne sous **Windows**. Les commandes POSIX échouent ou se comportent
autrement ; utiliser PowerShell, ou Git Bash pour les scripts shell.

**Le `.venv` du dépôt est vide.** Ni `pytest` ni `fastapi` n'y sont installés. Tout
s'exécute avec le **Python système** (`C:\Users\AZ\AppData\Local\Programs\Python\Python311`),
qui porte les dépendances. Ne pas activer le venv : les commandes échoueraient.

```powershell
uvicorn api.main:app --reload --port 8000
python -m pytest tests/ -q
python -m pytest tests/test_fb_ig_collectors.py -q      # un seul fichier
python -m pip install --user <paquet>                   # site-packages système non inscriptible
```

`ruff` et `flake8` ne sont pas installés. Ne pas proposer de commande de lint sans avoir
vérifié sa présence.

### État de la suite de tests

**19 tests échouent, 871 passent.** Ces échecs sont antérieurs et sans rapport avec la
collecte : `core.analysis.absa_engine` n'expose plus `classify_sentiment`, attendu par
`test_classify_sentiment.py`, `test_rag/test_generator.py` et `test_source_platform_admin.py`.

La règle n'est donc pas « la suite doit passer » mais **« ne pas ajouter d'échec »**.
Comparer avant/après sur les fichiers touchés.

## Carte du dépôt

| Élément | Emplacement |
|---|---|
| Point d'entrée API | `api/main.py` |
| Routeurs (14) | `api/routers/`, préfixe `/api` |
| Schémas de réponse | `api/schemas.py` |
| Authentification | `core/security/auth.py`, header `X-API-Key` |
| Logique métier | `core/` |
| Collecteurs | `core/watch_runs/collectors/` |
| Base SQLite (34 tables) | `data/ramypulse.db`, chemin défini dans `config.py` |
| Tests (66 fichiers) | `tests/` |
| Contrat frontend | `frontend/shared/schema.ts` — **source de vérité** |

Il n'y a **pas d'ORM ni de `api/models.py`**. Le schéma est en SQL brut dans les modules
de `core/`. Ne pas supposer SQLAlchemy.

## Worktrees

Le dépôt en utilise plusieurs. Vérifier où l'on se trouve avant d'écrire :

```powershell
git worktree list
git branch --show-current
```

- `G:/ramypulse` — worktree principal
- `.worktrees/agent-backend` — branche `agent/claude-backend`
- `.worktrees/agent-frontend` — branche `agent/codex-frontend`

Ne pas modifier `frontend/client/src/` depuis un worktree backend.

## Données et confidentialité — lire avant tout `git add`

`data/raw/` et `data/processed/` sont dans `.gitignore`. **C'est délibéré.**

Les commentaires collectés contiennent des **noms de personnes réelles**, utilisateurs
tagués sur Facebook. Le pipeline de préparation supprime URL, e-mails, téléphones et
identifiants `@`, mais **pas les noms propres en clair** : environ 15 % des lignes en
contiennent.

- **Ne jamais faire `git add -f` sur `data/`** sans validation humaine explicite. Forcer
  le `.gitignore` publie des données personnelles que son auteur avait choisi d'exclure.
- Avant un push, vérifier le contenu des fichiers ajoutés, pas seulement leur nom.
- Groupes privés et sources sans licence explicite : exclus de la collecte.

Point connu non résolu : **`.env` est suivi par git et présent dans l'historique avec au
moins une clé**. Ne pas aggraver. Rotation des clés et purge d'historique restent à faire.

## Contrats à ne pas casser

- `frontend/shared/schema.ts` : toute modification d'un schéma de réponse consommé par le
  frontend demande une synchronisation humaine.
- Réponses JSON en `snake_case` ; le frontend convertit dans `apiMappings.ts`.
- URLs en kebab-case : `/api/watch-runs`, jamais `/api/watchRuns`.
- Python : `snake_case` pour variables et fonctions, `PascalCase` pour les classes.
- Logging via `logging.getLogger(__name__)`, jamais `print()`.

## Méthode de travail

**Tests d'abord.** Écrire le test qui échoue, implémenter, vérifier que la suite passe.
Les collecteurs se testent avec de faux clients Apify — voir `tests/test_fb_ig_collectors.py`.

**Vérifier avant d'affirmer.** Ce fichier a contenu pendant des mois dix affirmations
fausses : chemins inexistants, compteurs périmés, commandes Unix sur une machine Windows.
Un chemin ou un chiffre cité de mémoire doit être recontrôlé avant usage — y compris
ceux de ce document.

**Ne pas committer sur `main`.** Branches en `feat/nom` ou `fix/nom`. Ne pousser que sur
demande explicite.

## Chantier SLM V2

Documentation dans `docs/slm_v2/`. Ces règles viennent de mesures, pas de préférences.

- **Contrat courant : `business_comment_annotation_v0.3.schema.json`.** Les V0.1 et V0.2
  sont conservées pour l'historique, pas pour usage.
- **Aucune porte de qualité au-dessus de l'accord inter-annotateurs mesuré.** Un modèle
  ne dépasse pas durablement la cohérence de sa propre référence. Seuils dans
  `docs/slm_v2/gold_v0.1/baselines/acceptance_gates_v0.3.json`.
- **Un champ sur lequel deux annotateurs ne s'accordent pas, mais qui se calcule depuis
  des champs sur lesquels ils s'accordent, doit être dérivé** plutôt qu'annoté. C'est
  ainsi que `priority` est passée de κ 0,306 à 0,907.
- **Les annotations ne se produisent jamais par script.** Un remplissage par gabarit a
  déjà été rejeté après avoir passé toutes les validations automatiques.
- **L'accord entre deux modèles ne prouve rien seul.** Sur l'arabizi, l'accord était le
  plus élevé du corpus et la validité la plus basse : les deux annotateurs partageaient
  le même repli sur `neutre`. Toute campagne doit inclure un échantillon d'accords tiré
  au hasard et relu par un humain.
- **Les preuves sont des extraits exacts du texte.** Le modèle ne calcule pas les
  offsets, le pipeline s'en charge — cela a supprimé toutes les erreurs mécaniques.
- Le gold porte un **palier de confiance par item**, jamais une confiance uniforme.

## Ce qu'il ne faut pas faire

- Modifier `frontend/client/src/` depuis un worktree backend.
- Toucher `frontend/shared/schema.ts` sans validation humaine.
- Committer sur `main`, ou pousser sans demande.
- Forcer l'ajout de fichiers de `data/` dans git.
- Utiliser `print()` pour du logging.
- Introduire un breaking change sur un endpoint consommé par le frontend.
