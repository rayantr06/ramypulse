# RamyPulse — Exécution Multi-Agents des Gaps Bloquants

## Objectif

Travailler à deux agents en parallèle, chacun dans son propre worktree et sa propre branche, puis intégrer les lots par ordre de dépendance sans conflit.

Ce document est fait pour :
- `Claude` dans un terminal / worktree
- `Codex` dans un autre terminal / worktree

Règle dure :
- pas de travail dans le même dossier
- pas de travail sur la même branche
- pas de fichiers partagés modifiés dans la même phase

---

## Priorités retenues

Ordre produit réel :

1. `auth / contrôle d'accès`
2. `jobs automatiques réels`
3. `connecteurs API officiels réels`
4. `health -> alerte`
5. `alerte -> notification auto`
6. `secrets durcis`
7. `nettoyage des faux contrôles UI`

On ne lance pas tout en même temps. On coupe le chantier en phases qui peuvent être mergées proprement.

---

## Règles de collaboration

Chaque agent doit respecter ceci :

1. travailler depuis `origin/main` à jour
2. créer un worktree dédié
3. créer sa propre branche
4. ne toucher que les fichiers explicitement dans son scope
5. lancer ses tests ciblés avant commit
6. ne jamais merge directement dans `main`
7. merger d'abord dans une branche d'intégration

Règle anti-conflit :
- si deux lots touchent les mêmes fichiers, ils ne doivent pas être en parallèle

---

## Préparation

Depuis le repo principal :

```bash
git fetch origin
git checkout main
git reset --hard origin/main
```

Créer les worktrees :

```bash
git worktree add ../ramypulse-claude-auth -b feat/auth-access-control
git worktree add ../ramypulse-codex-automation -b feat/automation-alert-runtime
```

Ensuite :
- `Claude` travaille dans `../ramypulse-claude-auth`
- `Codex` travaille dans `../ramypulse-codex-automation`

---

## Phase 1 — Deux lots parallèles

### Lot A — Claude

**Branche :** `feat/auth-access-control`

**But :**
ajouter une vraie couche minimale d'authentification et de contrôle d'accès côté API, avec injection propre du `client_id`.

**Scope autorisé :**
- `api/main.py`
- `api/routers/*.py` seulement si nécessaire pour brancher des dépendances auth, **sauf** `api/routers/admin.py`
- `api/schemas.py` seulement si un contrat de login/config l'exige
- `core/security/`
- `core/database.py` pour ajouter une table auth dédiée si nécessaire (`users`, `api_keys`, `service_accounts`), sans refondre les tables métier existantes
- `tests/` liés à auth

**Scope interdit :**
- `frontend/`
- `core/alerts/`
- `core/ingestion/`
- `core/social_metrics/`
- `api/routers/admin.py`

**Résultat attendu :**
- une couche auth minimale mais réelle
- un mécanisme clair pour déterminer `client_id`
- endpoints non publics protégés
- tests API qui vérifient :
  - accès refusé sans auth
  - accès autorisé avec contexte valide
  - `client_id` injecté de façon cohérente

**Prompt à donner à Claude :**

```text
Tu travailles dans le worktree ../ramypulse-claude-auth sur la branche feat/auth-access-control.

Mission :
implémenter la première couche réelle d'authentification / autorisation pour RamyPulse.

Contexte important :
- Aujourd'hui, l'API FastAPI est essentiellement ouverte.
- Le besoin prioritaire n'est pas un système IAM enterprise. Le besoin est une couche auth minimale mais réelle, cohérente avec le modèle client_id existant.
- Il faut éviter un faux système "mock auth".

Objectif :
- protéger les endpoints métier sensibles
- injecter proprement le client_id dans le contexte serveur
- préparer un socle extensible sans réécrire toute l'API

Contraintes :
- travaille uniquement dans ton scope
- ne touche pas au frontend
- ne touche pas au scheduler/alerts/notifications
- ne touche pas à `api/routers/admin.py` ; l'auth de ces routes sera branchée au moment de l'intégration
- écris les tests avant ou en même temps que l'implémentation
- reste pragmatique : pas d'usine à gaz

Livrables :
1. auth minimale fonctionnelle
2. tests API verts
3. court résumé : modèle choisi, endpoints protégés, limites restantes
```

---

### Lot B — Codex

**Branche :** `feat/automation-alert-runtime`

**But :**
rendre le système réellement autonome côté exécution des jobs critiques, sans dépendre d'un clic manuel permanent.

**Scope autorisé :**
- `core/ingestion/scheduler.py`
- `core/ingestion/health_checker.py`
- `core/alerts/alert_detector.py`
- `core/alerts/alert_manager.py`
- `core/notifications/notification_manager.py`
- `core/recommendation/weekly_report_job.py` seulement si nécessaire pour cohérence runner
- `api/routers/admin.py`
- `scripts/`
- `tests/`

**Scope interdit :**
- `frontend/`
- `api/routers/social_metrics.py`
- `core/security/`
- `core/connectors/`
- `api/main.py`

**Résultat attendu :**
- un mécanisme d'exécution automatique réel
- health score qui peut créer une alerte
- alerte qui peut déclencher notification email/Slack quand configuré
- tests ciblés

**Décision d'architecture à respecter :**
- le vrai but est l'automatisation réelle
- pas "mettre APScheduler juste pour cocher une case"
- si un runner externe + commandes/entrypoints explicites est plus propre, c'est acceptable

**Prompt à donner à Codex :**

```text
Tu travailles dans le worktree ../ramypulse-codex-automation sur la branche feat/automation-alert-runtime.

Mission :
transformer l'automatisation actuelle en exécution réellement exploitable.

Contexte important :
- Aujourd'hui on a un scheduler tick manuel.
- Le manque principal n'est pas "pas APScheduler", mais "rien ne tourne tout seul".
- Il faut aussi fermer deux chaînes incomplètes :
  1. source health -> alerte
  2. alerte -> notification auto

Objectif :
- fournir un mécanisme d'exécution auto crédible
- faire remonter la santé source en vraie alerte
- faire partir email/Slack automatiquement quand c'est configuré

Contraintes :
- ne touche pas à l'auth
- ne touche pas au frontend
- ne réécris pas les recommandations ni les campagnes
- `api/routers/admin.py` t'appartient exclusivement sur cette phase
- n'attends pas de changement dans `core/security/secret_manager.py` ; si le lot auth le modifie plus tard, l'intégration devra vérifier la compatibilité, mais ton lot ne doit pas dépendre d'une refonte de ce module
- pas de sur-ingénierie

Livrables :
1. runner/job/entrypoint d'automatisation clair
2. health -> alert branché
3. alert -> notification branché
4. tests verts
5. court résumé : ce qui tourne, comment le lancer, limites restantes
```

---

## Branche d'intégration Phase 1

Quand les deux lots sont finis :

```bash
git checkout main
git fetch origin
git reset --hard origin/main
git checkout -b integration/core-hardening
git merge feat/auth-access-control
git merge feat/automation-alert-runtime
```

Puis lancer :

```bash
python -m pytest tests/ -q --tb=no
cd frontend && npm.cmd run check
cd frontend && npm.cmd run build
```

Si tout est vert :
- seulement ensuite merge vers `main`

---

## Phase 2 — Après merge de la phase 1

### Lot C — Claude

**Branche :** `feat/platform-api-connectors`

**But :**
implémenter au moins un vrai connecteur API officiel de plateforme, idéalement le plus utile terrain.

**Priorité recommandée :**
1. Instagram officiel
2. YouTube Data
3. Facebook Graph
4. Google Business

**Règle :**
- un connecteur réel bien fini vaut mieux que trois squelettes

---

### Lot D — Codex

**Branche :** `feat/frontend-finish-pass`

**But :**
supprimer les faux contrôles visibles ou les brancher réellement, sans casser Stitch.

**Scope recommandé :**
- `frontend/client/src/pages/*.tsx`
- `frontend/client/src/components/*.tsx`
- `frontend/tests/stitchTextFidelity.test.mjs`
- `frontend/tests/visual/`

**Règle :**
- aucun bouton visible ne doit rester ambigu
- si un contrôle n'est pas prêt, il faut l'assumer visuellement au lieu de mentir

---

## Merge order recommandé

Ordre d'intégration :

1. `feat/auth-access-control`
2. `feat/automation-alert-runtime`
3. `integration/core-hardening`
4. `feat/platform-api-connectors`
5. `feat/frontend-finish-pass`

Pourquoi :
- auth et automation sont les vraies fondations
- les connecteurs réels viennent ensuite
- la finition UI passe après les fondations réelles

---

## Ce qu'il ne faut pas faire

- ne pas faire `auth`, `connecteurs`, `frontend`, `automation` tous en parallèle
- ne pas faire deux agents dans les mêmes fichiers
- ne pas merger directement dans `main` dès qu'une branche passe localement
- ne pas traiter les pages React manquantes comme des obligations si la décision produit les a supprimées
- ne pas inventer des métriques ou des comportements pour "faire joli"

---

## Définition de terminé

Une branche n'est pas "terminée" si :
- le code compile mais les tests ne couvrent pas le lot
- le comportement n'est pas documenté
- l'agent a touché des fichiers hors scope
- le résultat dépend encore d'un bouton manuel caché

Une branche est "terminée" si :
- le lot demandé est implémenté
- les tests ciblés passent
- la suite de régression pertinente passe
- le scope a été respecté
- le résumé de merge est clair
