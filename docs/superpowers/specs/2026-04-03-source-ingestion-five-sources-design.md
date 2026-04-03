# Source Ingestion Five Sources Design

**Date:** 2026-04-03  
**Branch:** `integration/wave5`

## Goal

Construire un socle d'ingestion modulaire et extensible pour cinq sources initiales:

- `facebook`
- `google_maps`
- `youtube`
- `instagram`
- `import`

Ce socle doit supporter l'onboarding source, la résolution des secrets, les runs de synchronisation, la traçabilité source -> raw -> normalized -> enriched, et une page d'administration unique.

## Scope

### In scope

- contrat connecteur commun
- onboarding source dans l'admin
- stockage des secrets par référence
- synchronisation tenant-safe
- health snapshots
- traçabilité pipeline bout en bout
- modes de collecte `snapshot` et `collector` pour les 5 sources

### Out of scope

- `tiktok`
- `audio`
- migration vers orchestrateur distribué
- remplacement du pipeline de normalisation existant
- refonte frontend React/Stitch

## Architecture

Le système est organisé autour de quatre couches:

1. `BaseConnector` + helpers de config
2. `IngestionOrchestrator`
3. `normalizer_pipeline`
4. `SourceAdminService` + page admin

Le connecteur collecte uniquement des documents bruts traçables. Il ne porte ni ABSA métier ni logique d'analyse avancée. L'enrichissement continue dans les tables plateforme `normalized_records` et `enriched_signals`.

## Repo baseline and coexistence

Cette spec part de l'état réel de `integration/wave5`, pas d'un repo vide.

Éléments déjà présents dans le code:

- table legacy `source_registry`
- tables plateforme `sources`, `source_sync_runs`, `raw_documents`, `normalized_records`, `enriched_signals`, `source_health_snapshots`
- `core/connectors/base_connector.py`
- `core/ingestion/orchestrator.py`
- `core/ingestion/source_admin_service.py`
- `core/normalization/normalizer_pipeline.py`

Règle de coexistence figée:

- `sources` est la source de vérité plateforme pour tout nouveau travail
- `source_registry` reste un artefact legacy de compatibilité
- aucun nouveau comportement ne doit être ajouté dans `source_registry`
- aucune migration destructive n'est requise dans ce lot
- si des données legacy doivent être lues, elles sont adaptées vers `sources`, pas l'inverse

Règle de schéma:

- la source de vérité SQL reste `core/database.py`
- cette spec décrit les contrats et comportements, pas un DDL concurrent
- toute implémentation doit s'aligner sur les tables déjà présentes dans `core/database.py`

## Data model

### Source of truth

La table `sources` reste la source de vérité pour:

- `source_id`
- `client_id`
- `source_name`
- `platform`
- `source_type`
- `owner_type`
- `auth_mode`
- `config_json`
- `is_active`
- `sync_frequency_minutes`
- `freshness_sla_hours`
- `last_sync_at`

### Config rules

`config_json` contient uniquement de la configuration fonctionnelle. Aucun secret brut ne doit être stocké en base.

Champs de config typiques:

- `snapshot_path`
- `column_mapping`
- `default_channel`
- `fetch_mode`
- `page_id`
- `page_url`
- `place_id`
- `place_url`
- `channel_id`
- `video_ids`
- `profile_id`
- `profile_url`
- `credential_ref`

### Secret handling

Le stockage et la résolution des secrets passent par `core/security/secret_manager.py`.

Règles figées:

- l'UI admin n'écrit jamais une clé brute dans SQLite
- les secrets sont convertis en références via `store_secret()`
- les connecteurs récupèrent les valeurs réelles via `resolve_secret()`

## Connector contract

Tous les connecteurs doivent respecter le même contrat logique:

1. validation de configuration
2. résolution des secrets et inputs runtime
3. collecte de documents bruts
4. remontée optionnelle de `health_hints`

Le point d'entrée public reste `fetch_documents(...)`.

### Python interface

Le contrat Python cible est le suivant:

```python
class BaseConnector(ABC):
    def validate_source_config(self, source: dict) -> None:
        ...

    def resolve_runtime_inputs(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        **kwargs,
    ) -> dict:
        ...

    @abstractmethod
    def fetch_documents(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        **kwargs,
    ) -> list[dict]:
        ...

    def health_hints(
        self,
        source: dict,
        *,
        last_run: dict | None = None,
    ) -> dict:
        ...
```

Règles figées:

- `fetch_documents()` retourne une `list[dict]`
- un `fetch_mode` non supporté doit lever une erreur explicite, pas tomber en fallback silencieux
- la pagination, le rate limiting et les retries restent de la responsabilité du connecteur ou de son backend collector
- l'orchestrateur gère le cycle de vie du run et la persistance, pas la logique métier spécifique de la plateforme

### Canonical raw document format

Chaque document retourné doit contenir:

- `external_document_id`
- `raw_text`
- `raw_payload`
- `raw_metadata`
- `collected_at`
- `checksum_sha256`

Et `raw_metadata` doit inclure au minimum:

- `client_id`
- `source_id`
- `platform`
- `source_type`
- `owner_type`
- `channel`
- `source_url`
- `timestamp`

## Fetch modes

Chaque source supporte explicitement un `fetch_mode`:

- `snapshot`
- `collector`
- `api`

Le premier lot impose `snapshot` et `collector`. Le mode `api` fait partie du contrat mais n'est pas requis sur les cinq sources au même niveau de maturité.

Le choix du mode appartient au connecteur à partir de la config source. L'orchestrateur ne doit pas contenir de branches métier spécifiques par plateforme.

### Fetch mode semantics

Définitions opérationnelles:

- `snapshot`
  - lecture d'un export local déterministe déposé par l'utilisateur ou par un job amont
  - exemples: CSV/Parquet de posts Facebook, export reviews Google Maps, dump commentaires YouTube, export Instagram, import batch direct
- `collector`
  - appel d'un collecteur local ou d'un backend intermédiaire contrôlé par l'application
  - exemples: script interne, job maison, backend Apify si configuré
- `api`
  - appel direct d'une API officielle ou d'un provider managé

Règles:

- le `fetch_mode` est choisi dans l'onboarding source via `config_json`
- le connecteur peut refuser un mode qui n'est pas mature pour sa plateforme
- `APIFY_API_KEY` est une dépendance optionnelle disponible dans `config.py` et peut être utilisée comme backend collector pour les plateformes où cela a du sens

## Source-specific expectations

### Import batch

Configuration attendue:

- `snapshot_path`
- `column_mapping`
- `default_channel`

Objectif:

- ingestion déterministe depuis CSV/Parquet/Excel
- propagation propre de la traçabilité vers les tables plateforme
- réutilisation de `core/ingestion/import_engine.py` pour le parsing fichier, le mapping de colonnes et la déduplication avant insertion `raw_documents`

### Facebook

Configuration attendue:

- `page_id` ou `page_url`
- `fetch_mode`
- `credential_ref` optionnel

Modes visés au premier lot:

- `snapshot`
- `collector`

### Google Maps

Configuration attendue:

- `place_id` ou `place_url`
- `fetch_mode`
- `credential_ref` optionnel

Modes visés au premier lot:

- `snapshot`
- `collector`

### YouTube

Configuration attendue:

- `channel_id` ou `video_ids`
- `fetch_mode`
- `credential_ref` optionnel

Modes visés au premier lot:

- `snapshot`
- `collector`

### Instagram

Configuration attendue:

- `profile_id` ou `profile_url`
- `fetch_mode`
- `credential_ref` optionnel

Modes visés au premier lot:

- `snapshot`
- `collector`

## Execution flow

Le flux complet est figé comme suit:

1. création source dans l'admin
2. validation de la config
3. stockage ou résolution de la référence de secret
4. ouverture d'un `source_sync_run`
5. `fetch_documents()`
6. insertion dans `raw_documents`
7. mise à jour `last_sync_at`
8. lancement du `normalizer_pipeline`
9. écriture `normalized_records`
10. écriture `enriched_signals`
11. calcul et persistance `source_health_snapshots`

### Orchestrator contract

Le point d'entrée cible de l'orchestrateur reste:

```python
class IngestionOrchestrator:
    def create_source(self, payload: dict) -> dict:
        ...

    def get_source(self, source_id: str, *, client_id: str | None = None) -> dict | None:
        ...

    def run_source_sync(
        self,
        source_id: str,
        *,
        manual_file_path: str | None = None,
        column_mapping: dict[str, str] | None = None,
        run_mode: str = "manual",
        credentials: dict | None = None,
        client_id: str | None = None,
    ) -> dict:
        ...
```

Responsabilités figées:

- sélectionner le connecteur
- ouvrir et fermer `source_sync_runs`
- insérer `raw_documents`
- déclencher `normalizer_pipeline`
- préserver les documents bruts si l'aval échoue
- remonter un résumé de run exploitable par l'admin

### Existing pipeline integration

Le lot ne remplace pas le pipeline existant. Il le structure.

- `core/ingestion/import_engine.py` reste la brique spécialisée pour les imports fichier
- `core/ingestion/normalizer.py` reste la normalisation textuelle primaire
- `core/normalization/normalizer_pipeline.py` orchestre `normalizer.py`, ABSA et entity resolution vers `normalized_records` et `enriched_signals`
- aucun connecteur ne doit dupliquer la logique de normalisation ou d'ABSA

## Multi-tenant rules

Règles non négociables:

- toutes les lectures et écritures plateforme acceptent un `client_id` explicite
- `DEFAULT_CLIENT_ID` reste seulement un fallback dev
- un client ne peut jamais déclencher ni lire une source d'un autre client
- la trace admin doit être filtrée par `client_id`

## Admin UI design

La page `pages/09_admin_sources.py` devient le cockpit unique des cinq sources.

### Sections

1. tableau `Sources`
2. tableau `Sync runs`
3. tableau `Health snapshots`
4. panneau d'actions sur la source sélectionnée
5. bloc `Trace pipeline`

### Admin capabilities

- créer une source
- éditer sa configuration
- activer / désactiver
- lancer une sync
- calculer un health snapshot
- visualiser les derniers runs
- visualiser la traçabilité de pipeline

### Service contract

La page admin ne parle pas directement à un registre legacy. Elle passe par `SourceAdminService`.

Contrat de service cible:

```python
class SourceAdminService:
    def list_sources(...) -> list[dict]:
        ...

    def list_sync_runs(...) -> list[dict]:
        ...

    def list_health_snapshots(...) -> list[dict]:
        ...

    def get_source_trace(...) -> dict:
        ...

    def update_source(...) -> dict:
        ...
```

## Error handling

Règles d'erreur:

- config invalide -> refus avant sync
- connecteur en erreur -> `source_sync_run.status = failed` + `error_message`
- normalisation en erreur -> `raw_documents` préservés et échec aval explicite
- accès cross-tenant -> refus immédiat

Aucune erreur silencieuse. Aucun `except:` nu. Aucun demi-état masqué dans l'admin.

## Testing strategy

### Connector tests

- config valide
- config invalide
- mode `snapshot`
- mode `collector`
- format brut canonique

### Orchestrator tests

- ouverture / fermeture du run
- insertion `raw_documents`
- déclenchement normalisation
- création `normalized_records`
- création `enriched_signals`
- refus cross-tenant

### Secret tests

- stockage référence
- résolution runtime
- absence de secret brut en base

### Admin tests

- création source
- affichage sources
- affichage runs
- affichage health snapshots
- trace pipeline

### End-to-end source tests

- `facebook`
- `google_maps`
- `youtube`
- `instagram`
- `import`

avec snapshots locaux de test pour garantir des runs déterministes.

## Implementation order

Le lot sera exécuté en trois sous-lots:

1. socle connecteur + config source + secrets + service admin
2. brancher les cinq sources sur le contrat commun
3. finaliser l'admin sources et les smokes end-to-end

## Success criteria

Le lot est considéré réussi si:

- les cinq sources passent par un contrat unique
- l'admin sources pilote les tables plateforme et non un registre legacy
- la traçabilité source -> raw -> normalized -> enriched est visible
- les accès cross-tenant sont refusés
- les tests automatisés des cinq sources sont verts
- l'ajout d'une sixième source ne nécessite pas de réécrire l'orchestrateur
