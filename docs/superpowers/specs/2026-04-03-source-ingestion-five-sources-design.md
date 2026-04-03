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

## Source-specific expectations

### Import batch

Configuration attendue:

- `snapshot_path`
- `column_mapping`
- `default_channel`

Objectif:

- ingestion déterministe depuis CSV/Parquet/Excel
- propagation propre de la traçabilité vers les tables plateforme

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
