# RamyPulse — PRD Technique v2.0
## De la démonstration académique à la plateforme de surveillance métier

---

| Champ | Valeur |
|---|---|
| Projet | RamyPulse |
| Version document | 2.0 — 30 mars 2026 |
| Statut | Document de référence actif — remplace PRD v1.0 pour la planification long terme |
| Auteur | Solo developer |
| Compétition | AI EXPO 2026 — Industry Track — Université Blida 1 — 16 avril 2026 |
| Soumission | 3 avril 2026 |
| Audience | Agents de codage IA (Claude Code, Codex, GitHub Copilot) — Antigravity IDE |
| Scope | Wave 1–4 (PoC existant) + Wave 5.1–5.5 (plateforme) + Wave 6 (vision) |

---

## Table des matières

1. Résumé exécutif
2. Contexte et point de départ
3. Vision produit cible
4. Contraintes et hypothèses
5. Architecture cible en 8 couches
6. Décisions d'architecture fermes
7. Modèle d'intégration client
8. Modèle de données complet
9. Spécifications des composants existants (Wave 1–4)
10. Spécifications des nouveaux composants (Wave 5)
11. Watchlists — Spécifications détaillées
12. Moteur d'alertes — Spécifications détaillées
13. Flux d'ingestion par type de source
14. Sécurité, isolation et traçabilité
15. Roadmap d'implémentation
16. Dépendances et requirements.txt
17. Risques et mitigations
18. Critères de succès par wave
19. Glossaire

---

## 1. Résumé exécutif

RamyPulse démarre comme un Proof of Concept d'analyse de sentiment multimodale pour l'industrie agroalimentaire algérienne, ciblant la marque Ramy (jus et boissons), développé pour AI EXPO 2026 à l'Université Blida 1.

Ce PRD v2.0 étend la vision initiale au-delà du PoC. Il définit la trajectoire complète du produit sur deux horizons :

**Horizon immédiat (Wave 1–4 / PoC)** : Système d'analyse locale avec dashboard Streamlit, ABSA dialectal sur Darija/Arabizi/Français, chat RAG avec provenance, simulation What-If. Deadline de soumission : 3 avril 2026.

**Horizon cible (Wave 5–6 / Plateforme)** : Plateforme de surveillance métier branchable chez un client réel, avec registre de sources, ingestion multi-canal structurée, catalogue métier, watchlists configurables, moteur d'alertes proactif, et architecture multi-tenant sécurisée.

Le changement structurel central entre v1.0 et v2.0 est le suivant : RamyPulse passe d'une logique de consultation (l'utilisateur interroge) à une logique de supervision (le système détecte et alerte sans attendre de question).

---

## 2. Contexte et point de départ

### 2.1 État actuel — Wave 1–4

Le système fonctionne aujourd'hui comme :
- Application d'analyse locale sur fichiers plats (Parquet)
- Dashboard Streamlit d'exploration ABSA
- Chat RAG avec provenance cliquable
- Simulateur What-If pour scénarios métier

### 2.2 Ce que le système fait aujourd'hui

- Classifie le sentiment en 5 classes sur contenu dialectal (Darija, Arabizi, Français)
- Extrait des aspects métier (goût, emballage, prix, disponibilité, fraîcheur)
- Calcule le Net Sentiment Score global, par canal, par aspect, en tendance
- Répond à des questions en langage naturel avec sources cliquables
- Simule l'impact d'une amélioration sur le NSS

### 2.3 Ce que le système ne fait pas encore

- Se brancher à des sources réelles en continu
- Distinguer sources possédées / imports / collecte publique
- Gérer plusieurs clients avec isolation des données
- Surveiller des périmètres métier définis (watchlists)
- Détecter et pousser des alertes sans intervention de l'utilisateur
- Tracer la santé de chaque source de données
- Versionner les transformations pour permettre le reprocessing

---

## 3. Vision produit cible

### 3.1 Ambition

RamyPulse doit devenir une plateforme capable de :

- Connecter plusieurs types de sources client (APIs officielles, imports batch, collecte publique cadrée)
- Collecter des signaux de manière fiable et traçable
- Normaliser des données hétérogènes selon un pipeline versionné
- Rattacher les données à des entités métier (produit, wilaya, distributeur, canal)
- Suivre des watchlists configurables par l'utilisateur
- Détecter des évolutions importantes sans attendre une question
- Générer des alertes actionnables avec justification calculée

### 3.2 Positionnement concurrentiel

RamyPulse se différencie de Sprinklr, Brandwatch et Mention sur trois axes structurels :

**ABSA Dialectale** — Analyse par aspect directement sur Darija, Arabizi, Français mixte. Les plateformes globales ne supportent pas le dialecte algérien.

**Provenance Cliquable** — Chaque insight est lié à sa source originale : URL du post Facebook, timestamp exact dans l'audio, avis Google Maps. Traçabilité complète.

**Simulation What-If** — Modélisation de scénarios décisionnels : « Si on améliore l'emballage, quel impact sur le NSS ? » Outil décisionnel actionnable.

À ces trois axes s'ajoutent en Wave 5 :

**Surveillance Proactive** — Détection automatique des dérives, anomalies et divergences sans intervention utilisateur.

**Architecture Souveraine** — Déployable on-premise, sans dépendance cloud, adapté au contexte réglementaire algérien.

### 3.3 Métriques business

- **NSS (Net Sentiment Score)** = (nb_positifs + nb_très_positifs − nb_négatifs − nb_très_négatifs) / total × 100. Plage : [−100, +100].
- **Matrice ABSA** : Croisement 5 aspects × 5 classes de sentiment.
- **Channel-Specific NSS** : NSS isolé par source.
- **Source Health Score** : Score composite de fiabilité par source (Wave 5).
- **Watchlist Coverage Rate** : Pourcentage de périmètre métier effectivement surveillé (Wave 5).

---

## 4. Contraintes et hypothèses

### 4.1 Contraintes permanentes

| Contrainte | Détail | Impact |
|---|---|---|
| Équipe | 1 développeur solo | Architecture monolithique modulaire, pas de microservices distribués |
| Infrastructure PoC | Laptop local uniquement | Modèles quantisés, pas de cloud requis pour Wave 1–4 |
| Deadline soumission | 3 avril 2026 | Prioriser le MVP fonctionnel Wave 1–4 |
| Deadline démo | 16 avril 2026 | Polish et scénario après soumission |
| Budget | ≤ 5 000 € | Outils open source, modèles locaux, zéro infrastructure payante au démarrage |

### 4.2 Contraintes Wave 5

| Contrainte | Détail | Impact |
|---|---|---|
| APIs officielles | OAuth requis, validation partenaire possible | Onboarding client plus complexe qu'un scraping |
| Multi-tenant | Isolation logique obligatoire | Filtrage par tenant à chaque niveau |
| Conformité | RGPD, droit algérien applicable | Politique de rétention, consentement, audit logs |

### 4.3 Hypothèses

- Le dataset fallback 45K commentaires (arXiv:2512.19543) est suffisant pour le PoC.
- Ollama tourne en local avec llama3.2:3b ou qwen2.5:7b selon les ressources disponibles.
- En Wave 5, PostgreSQL est la seule base de données nécessaire pour les tables métadonnées.
- Le scraping n'est pas la fondation principale du produit.

---

## 5. Architecture cible en 8 couches

L'architecture cible est structurée en huit couches séquentielles et indépendantes. Chaque couche a une responsabilité unique. Aucune couche ne dépend de la logique interne d'une autre.

### Couche 1 — Connecteurs de sources

Gère la connexion aux sources d'entrée.

Responsabilités :
- Authentifier via OAuth, clé API, ou import fichier
- Récupérer les données dans leur format natif
- Valider le format d'entrée en entrée de pipeline
- Déclencher l'ingestion

Types de connecteurs : API officielle, import batch (CSV/Parquet/Excel), upload manuel, connecteur base de données, collecte publique cadrée.

### Couche 2 — Orchestrateur d'ingestion

Pilote les tâches de collecte selon les fréquences définies par source.

Responsabilités :
- Planifier les synchronisations selon `sync_frequency`
- Lancer les jobs de connecteurs
- Gérer les retries avec backoff exponentiel
- Journaliser chaque run dans `source_sync_runs`
- Maintenir le statut `last_sync_at` et `source_health_score`

### Couche 3 — Stockage brut

Conserve les données exactement telles qu'elles ont été reçues.

Responsabilités :
- Stocker les réponses API, fichiers importés, commentaires bruts, métadonnées d'origine, snapshots datés
- Garantir l'auditabilité et la traçabilité
- Permettre le reprocessing complet après une mise à jour du pipeline de normalisation

**Principe critique** : La donnée brute ne doit jamais être écrasée ou dépendre uniquement de la donnée enrichie. `raw_documents` est la source de vérité.

### Couche 4 — Normalisation et enrichissement

Transforme les données brutes en enregistrements cohérents et exploitables.

Responsabilités :
- Harmoniser les formats entre sources hétérogènes
- Nettoyer et normaliser les champs texte (Arabizi, diacritiques, tatweel)
- Mapper les canaux vers les valeurs standard
- Standardiser les dates et localisations
- Rattacher les entités métier (produit, wilaya, distributeur)
- Enrichir avec labels (sentiment, aspect, score de confiance)
- Versionner chaque transformation via `normalizer_version`

### Couche 5 — Modèle métier

Contient les entités business qui donnent du sens aux signaux.

Entités : client, produit, gamme, SKU, distributeur, wilaya, zone de livraison, point de vente, canal, watchlist.

**Rôle critique** : Cette couche transforme des signaux techniques en informations exploitables dans le vocabulaire du client. Sans elle, les alertes portent sur des URLs et des IDs, pas sur des wilayas et des gammes.

### Couche 6 — Moteur analytique et de surveillance

Calcule les indicateurs et suit les watchlists.

Responsabilités :
- Agréger les données enrichies
- Calculer les métriques NSS par dimension (global, canal, aspect, produit, wilaya, distributeur)
- Comparer les périodes (semaine vs semaine précédente, mois vs mois précédent)
- Produire les vues de monitoring
- Alimenter les règles d'alertes avec des métriques calculées

### Couche 7 — Moteur d'alertes

Détecte les situations qui méritent une notification ou une mise en avant.

Responsabilités :
- Exécuter les règles d'alerte sur les métriques calculées
- Détecter les anomalies statistiques
- Scorer la criticité de chaque alerte
- Créer des alertes persistées avec cycle de vie géré
- Dédupliquer les alertes redondantes via `dedup_key`

### Couche 8 — Exposition produit

Fournit les interfaces visibles aux utilisateurs.

Interfaces : dashboard Streamlit, explorer de données, chat RAG, écran watchlists, centre d'alertes, notifications e-mail / webhook / Slack / in-app, exports CSV/Parquet.

---

## 6. Décisions d'architecture fermes

### 6.1 Orchestrateur — APScheduler → Prefect

#### Décision Wave 5.1 : APScheduler in-process

APScheduler est choisi pour Wave 5.1 pour les raisons suivantes :
- Zéro infrastructure supplémentaire — s'intègre dans le processus FastAPI existant
- La source de vérité reste PostgreSQL via `source_sync_runs`
- Le déploiement reste un Docker Compose minimal : `postgres` + `api`
- Simple à débugger, logs dans le processus principal
- Si le processus redémarre, les jobs sont recréés depuis la table `sources`

Airflow est éliminé (trop lourd, YAML DAGs, workers séparés). Celery + Redis et RQ sont éliminés (dépendance Redis inutile à ce stade). Prefect est excellent mais prématuré avant d'avoir des connecteurs fonctionnels.

**Pattern d'implémentation Wave 5.1 :**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def load_sources_and_schedule():
    sources = await db.fetch_all(
        "SELECT * FROM sources WHERE is_active = true"
    )
    for source in sources:
        scheduler.add_job(
            run_sync_for_source,
            trigger='interval',
            minutes=source.sync_frequency_minutes,
            args=[source.source_id],
            id=f"sync_{source.source_id}",
            replace_existing=True
        )

async def run_sync_for_source(source_id: str):
    run_id = await create_sync_run(source_id)  # INSERT source_sync_runs
    try:
        result = await dispatch_connector(source_id)
        await complete_sync_run(run_id, result)
    except Exception as e:
        await fail_sync_run(run_id, str(e))
        await update_source_health(source_id)
```

`dispatch_connector` route vers le bon connecteur selon `platform` et `auth_mode`.

#### Migration Wave 5.3 : Prefect

Prefect devient pertinent à partir de Wave 5.3 si l'une de ces conditions est vraie :
- Plus de 15 sources actives simultanément
- Connecteurs longue durée (> 5 minutes)
- Plusieurs clients avec des profils de synchronisation distincts

Le passage à Prefect est une migration propre : `source_sync_runs` devient un complément aux Prefect flow runs, pas un doublon.

### 6.2 Stratégie de normalisation — Batch polling avec flag

#### Décision Wave 5.1 : Batch polling sur `is_normalized`

Le pattern retenu est : store raw → job périodique lit `raw_documents WHERE is_normalized = false` → normalise → écrit dans `normalized_records` + `enriched_signals` → met `is_normalized = true`.

Ce pattern est choisi parce que :
- Zéro nouvelle infrastructure (pas de Redis, pas de RabbitMQ)
- Entièrement porté par PostgreSQL
- Supporte nativement le reprocessing complet par reset du flag
- La transformation synchrone à l'ingestion (Pattern A) est éliminée car elle viole le principe de séparation brut/enrichi
- La queue async (Pattern B) est éliminée car prématurée

**Colonnes additionnelles sur `raw_documents` :**

```sql
ALTER TABLE raw_documents ADD COLUMN is_normalized BOOLEAN DEFAULT FALSE;
ALTER TABLE raw_documents ADD COLUMN normalizer_version VARCHAR(20);
```

**Reprocessing après mise à jour du pipeline :**

```sql
UPDATE raw_documents
SET is_normalized = false
WHERE normalizer_version < '2.0';
-- Le job reprend ces enregistrements dans son prochain cycle
```

**Pattern d'implémentation du job de normalisation :**

```python
CURRENT_NORMALIZER_VERSION = "1.0"

async def normalization_job():
    batch = await db.fetch_all("""
        SELECT * FROM raw_documents
        WHERE is_normalized = false
        ORDER BY collected_at ASC
        LIMIT 200
    """)

    for doc in batch:
        try:
            normalized = await normalize(doc)
            signals = await enrich(normalized)

            await db.execute(INSERT_normalized_record, normalized)
            await db.execute(INSERT_enriched_signal, signals)
            await db.execute("""
                UPDATE raw_documents
                SET is_normalized = true,
                    normalizer_version = :version
                WHERE raw_document_id = :id
            """, {"version": CURRENT_NORMALIZER_VERSION, "id": doc.raw_document_id})
        except Exception as e:
            await log_normalization_error(doc.raw_document_id, str(e))
            # Ne pas bloquer le batch — continuer avec le suivant
```

Le `LIMIT 200` est un levier de tuning ajustable selon les ressources disponibles.

#### Migration Wave 5.3 : PostgreSQL LISTEN/NOTIFY

Si la latence devient un enjeu (données attendues en quasi temps réel), PostgreSQL LISTEN/NOTIFY sur INSERT dans `raw_documents` remplace le polling. Migration propre, sans nouvelle infrastructure.

### 6.3 Santé des sources

Deux éléments absents de la V2 initiale, introduits ici comme décisions fermes.

**`data_freshness_sla` sur la table `sources` :**

```sql
ALTER TABLE sources ADD COLUMN freshness_sla_hours INTEGER DEFAULT 24;
```

Un job `source_health_check_job` tourne toutes les heures :

```sql
SELECT source_id
FROM sources
WHERE is_active = true
  AND last_sync_at < NOW() - INTERVAL '1 hour' * freshness_sla_hours
```

Toute source dépassant son SLA génère une alerte de type `source_health`, distincte des alertes métier. Sans ce mécanisme, une source cassée depuis 4 jours continue d'alimenter des watchlists qui affichent des métriques périmées sans que personne ne le sache.

**`source_health_score` :**

Calculé par `source_health_check_job` à chaque cycle et stocké dans `source_health_snapshots` :

```
source_health_score = f(
    taux_reussite_10_derniers_runs,
    age_derniere_sync_reussie_vs_sla,
    drift_volume_moyen_records_par_run,
    nombre_erreurs_consecutives_recentes
)
```

Score entre 0 et 100. En dessous de 60, alerte automatique.

### 6.4 Stratégie de migration du schéma existant

Le schéma actuel (`text`, `sentiment_label`, `channel`, `aspect`, `source_url`, `timestamp`, `confidence`) reste intact comme couche de compatibilité.

Les nouvelles tables Wave 5 sont créées en parallèle. Un script de migration unique porte les données existantes vers `normalized_records` + `enriched_signals` a posteriori. Les données existantes n'ont pas de `raw_document` correspondant, mais leurs champs suffisent pour peupler `normalized_records` directement.

---

## 7. Modèle d'intégration client

### 7.1 Position de conception — Modèle hybride

Le modèle recommandé combine trois niveaux de connexion, hiérarchisés par priorité.

**Niveau 1 — Sources officielles connectées (priorité)**

À privilégier dès qu'un accès officiel existe :
- Meta Pages (Facebook pages gérées par le client)
- Instagram Business (comptes professionnels liés à une Page Meta)
- Google Business Profile (établissements du client)
- YouTube (chaînes et vidéos ciblées via commentThreads.list)

Avantages : propre juridiquement, authentification OAuth officielle, métadonnées fiables, meilleure stabilité, industrialisable.

Limites : limité aux actifs possédés ou autorisés, onboarding plus complexe, dépend des permissions plateforme.

**Niveau 2 — Imports batch ou manuels**

Pour les données internes ou semi-structurées du client :
- Exports CRM, SAV, e-commerce
- Reviews exportées, tickets, incidents
- Données logistiques ou commerciales internes
- Fichiers CSV, Excel, Parquet

Avantages : simple à lancer, robuste, bon pour démarrer un POC, complément des APIs.

Limites : pas toujours temps réel, dépend de la qualité des exports, schémas variables.

**Niveau 3 — Collecte publique cadrée**

À réserver aux cas où aucune connexion officielle n'est possible :
- Veille concurrentielle
- Signaux publics (avis Google Maps de concurrents)
- Observation territoriale
- Sources ouvertes non connectables

Conclusion de conception : Le scraping peut exister comme couche complémentaire, uniquement dans un cadre contrôlé. Il ne doit pas être la fondation centrale du produit.

### 7.2 Ce que les plateformes offrent en pratique

**Meta / Facebook Pages** : Le modèle standard passe par OAuth et les pages gérées par l'utilisateur du client. On récupère un user access token, puis un page access token, puis on agit sur les pages que l'utilisateur gère. Le schéma naturel est "sources owned du client", pas "surveillance libre de tout Facebook".

**Instagram** : L'API officielle est centrée sur les comptes Business et Creator. Elle ne donne pas accès aux comptes consumer classiques. Dans le modèle Facebook Login, il faut lier une Page à un compte Instagram professionnel.

**Google Business Profile** : L'API GBP vise les établissements du client ou de l'organisation autorisée. Setup : demande d'accès API, activation des APIs associées, OAuth 2.0, accès aux données de localisation et reviews de l'organisation. Ce n'est pas une API généraliste pour aspirer n'importe quelle fiche publique.

**YouTube** : Expose une API publique plus exploitable pour les commentaires via `commentThreads.list` et `comments.list`. Utile pour les chaînes du client, vidéos ciblées, et cas de veille publique. Reste borné par quotas et permissions.

### 7.3 Options d'onboarding client

**Option A — Onboarding léger (Wave 5.1)**
Le client fournit : exports CSV/Parquet, liste de pages/comptes/établissements, nomenclature produits, mapping wilaya optionnel. Avantage : rapide pour démarrer.

**Option B — Onboarding API officiel (Wave 5.2)**
Le client connecte : Meta Business/Pages, Instagram Pro, Google Business Profile, YouTube. Avantage : industrialisable, meilleur futur produit.

**Option C — Modèle hybride (recommandé dès Wave 5.2)**
Combiner connexions API officielles, imports manuels/batch, quelques flux publics ciblés. C'est le modèle le plus crédible pour une version entreprise.

---

## 8. Modèle de données complet

### 8.1 Schéma existant — Couche PoC (Wave 1–4)

Colonne centrale du DataFrame annoté, inchangée pour compatibilité :

```
text | text_original | script_detected | language | sentiment_label | confidence
channel | aspect | aspect_sentiments | source_url | timestamp | author
```

Fichiers : `data/processed/clean.parquet`, `data/processed/annotated.parquet`

### 8.2 Nouvelles tables — Wave 5

#### Table `clients`

```sql
CREATE TABLE clients (
    client_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_name     VARCHAR(255) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table `sources`

```sql
CREATE TABLE sources (
    source_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id               UUID NOT NULL REFERENCES clients(client_id),
    platform                VARCHAR(50) NOT NULL,       -- facebook, instagram, google_maps, youtube, csv_import, internal_export
    source_type             VARCHAR(80) NOT NULL,       -- facebook_page, instagram_business_account, google_business_location, youtube_channel, youtube_video, imported_dataset
    display_name            VARCHAR(255) NOT NULL,
    external_id             VARCHAR(255),               -- page ID, place ID, channel ID
    url                     TEXT,
    owner_type              VARCHAR(30) NOT NULL,       -- owned, competitor, public
    auth_mode               VARCHAR(30) NOT NULL,       -- oauth, api_key, manual_import, public
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    sync_frequency_minutes  INTEGER NOT NULL DEFAULT 1440,
    freshness_sla_hours     INTEGER NOT NULL DEFAULT 24,  -- DÉCISION 6.3
    last_sync_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Valeurs `source_type` supportées** : `facebook_page`, `instagram_business_account`, `google_business_location`, `youtube_channel`, `youtube_video`, `imported_dataset`, `internal_export`.

#### Table `source_sync_runs`

```sql
CREATE TABLE source_sync_runs (
    sync_run_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           UUID NOT NULL REFERENCES sources(source_id),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at            TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'running',  -- running, success, partial, failed
    records_fetched     INTEGER DEFAULT 0,
    records_inserted    INTEGER DEFAULT 0,
    records_failed      INTEGER DEFAULT 0,
    error_message       TEXT,
    run_mode            VARCHAR(20) NOT NULL DEFAULT 'scheduled'  -- scheduled, manual, reprocess
);
```

#### Table `raw_documents`

```sql
CREATE TABLE raw_documents (
    raw_document_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID NOT NULL REFERENCES clients(client_id),
    source_id           UUID NOT NULL REFERENCES sources(source_id),
    sync_run_id         UUID REFERENCES source_sync_runs(sync_run_id),
    raw_payload         JSONB,                          -- réponse API complète
    raw_text            TEXT,
    raw_metadata        JSONB,                          -- auteur, date, URL, rating, etc.
    collected_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum            VARCHAR(64),                    -- SHA-256 pour déduplication
    is_normalized       BOOLEAN NOT NULL DEFAULT FALSE, -- DÉCISION 6.2
    normalizer_version  VARCHAR(20)                     -- DÉCISION 6.2
);

CREATE INDEX idx_raw_documents_not_normalized
    ON raw_documents(collected_at)
    WHERE is_normalized = false;
```

#### Table `normalized_records`

```sql
CREATE TABLE normalized_records (
    normalized_record_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id               UUID NOT NULL REFERENCES clients(client_id),
    source_id               UUID NOT NULL REFERENCES sources(source_id),
    raw_document_id         UUID REFERENCES raw_documents(raw_document_id),
    channel                 VARCHAR(50) NOT NULL,
    text                    TEXT NOT NULL,
    text_original           TEXT,
    script_detected         VARCHAR(20),    -- arabic, latin, mixed
    language                VARCHAR(30),    -- darija, french, mixed
    timestamp               TIMESTAMPTZ,
    author_label            VARCHAR(255),
    source_url              TEXT,
    confidence              FLOAT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table `enriched_signals`

```sql
CREATE TABLE enriched_signals (
    signal_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    normalized_record_id    UUID NOT NULL REFERENCES normalized_records(normalized_record_id),
    sentiment_label         VARCHAR(30) NOT NULL,   -- très_positif, positif, neutre, négatif, très_négatif
    sentiment_score         FLOAT,
    aspect                  VARCHAR(50),            -- goût, emballage, prix, disponibilité, fraîcheur
    metric_type             VARCHAR(50),            -- nss, volume, aspect_sentiment
    metric_value            FLOAT,
    anomaly_score           FLOAT,
    classifier_version      VARCHAR(20),
    enrichment_version      VARCHAR(20)
);
```

#### Table `products`

```sql
CREATE TABLE products (
    product_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(client_id),
    product_name    VARCHAR(255) NOT NULL,
    product_line    VARCHAR(255),
    sku             VARCHAR(100),
    category        VARCHAR(100),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);
```

#### Table `regions`

```sql
CREATE TABLE regions (
    region_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(client_id),
    wilaya          VARCHAR(100),
    delivery_zone   VARCHAR(100),
    sub_zone        VARCHAR(100),
    region_type     VARCHAR(50)     -- wilaya, zone, commune
);
```

#### Table `distributors`

```sql
CREATE TABLE distributors (
    distributor_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID NOT NULL REFERENCES clients(client_id),
    distributor_name    VARCHAR(255) NOT NULL,
    distributor_type    VARCHAR(50),
    region_id           UUID REFERENCES regions(region_id)
);
```

#### Table `source_health_snapshots` — DÉCISION 6.3

```sql
CREATE TABLE source_health_snapshots (
    snapshot_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id               UUID NOT NULL REFERENCES sources(source_id),
    health_score            FLOAT NOT NULL,     -- 0 à 100
    run_success_rate_10     FLOAT,              -- taux de réussite des 10 derniers runs
    age_since_last_success  FLOAT,              -- en heures
    volume_drift_ratio      FLOAT,              -- ratio vs volume moyen historique
    consecutive_errors      INTEGER DEFAULT 0,
    sla_breached            BOOLEAN DEFAULT FALSE,
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table `watchlists`

```sql
CREATE TABLE watchlists (
    watchlist_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(client_id),
    watchlist_name  VARCHAR(255) NOT NULL,
    description     TEXT,
    scope_type      VARCHAR(50),    -- product, region, channel, cross_dimension
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table `watchlist_filters`

```sql
CREATE TABLE watchlist_filters (
    watchlist_filter_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id        UUID NOT NULL REFERENCES watchlists(watchlist_id),
    source_id           UUID REFERENCES sources(source_id),
    product_id          UUID REFERENCES products(product_id),
    region_id           UUID REFERENCES regions(region_id),
    distributor_id      UUID REFERENCES distributors(distributor_id),
    channel             VARCHAR(50),
    aspect              VARCHAR(50),
    metric_type         VARCHAR(50),
    period_type         VARCHAR(30)     -- daily, weekly, monthly
);
```

#### Table `alert_rules`

```sql
CREATE TABLE alert_rules (
    alert_rule_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID NOT NULL REFERENCES clients(client_id),
    watchlist_id        UUID REFERENCES watchlists(watchlist_id),
    rule_name           VARCHAR(255) NOT NULL,
    rule_type           VARCHAR(50) NOT NULL,   -- absolute, relative, anomaly, drift, divergence
    threshold_value     FLOAT,
    comparator          VARCHAR(10),            -- lt, gt, lte, gte
    lookback_window     VARCHAR(30),            -- 7d, 30d, 3w
    severity_level      VARCHAR(20) NOT NULL,   -- critical, high, medium, low
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);
```

#### Table `alerts`

```sql
CREATE TABLE alerts (
    alert_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(client_id),
    watchlist_id    UUID REFERENCES watchlists(watchlist_id),
    alert_rule_id   UUID REFERENCES alert_rules(alert_rule_id),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    severity        VARCHAR(20) NOT NULL,   -- critical, high, medium, low
    status          VARCHAR(30) NOT NULL DEFAULT 'new',  -- new, acknowledged, investigating, resolved, dismissed
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    alert_payload   JSONB,                  -- métriques, comparaisons, contexte calculé
    dedup_key       VARCHAR(255),           -- pour éviter les doublons
    navigation_url  TEXT                    -- lien direct vers la vue concernée
);

CREATE UNIQUE INDEX idx_alerts_dedup ON alerts(dedup_key) WHERE status NOT IN ('resolved', 'dismissed');
```

---

## 9. Spécifications des composants existants (Wave 1–4)

### 9.1 `config.py` — Constantes et paramètres globaux

**Description** : Fichier central de configuration. Contient tous les chemins, constantes, paramètres de modèles et seuils. Aucune logique métier.

**Inputs** : Variables d'environnement (.env) + valeurs par défaut.

**Outputs** : Constantes Python importables par tous les modules.

**Dépendances** : python-dotenv, pathlib, os.

**Contenu attendu** :
- `BASE_DIR`, `DATA_DIR`, `MODELS_DIR`
- `DZIRIBERT_MODEL_PATH`, `WHISPER_MODEL_SIZE`
- `OLLAMA_MODEL` (llama3.2:3b ou qwen2.5:7b), `OLLAMA_BASE_URL`
- `FAISS_INDEX_PATH`, `EMBEDDING_MODEL` (multilingual-e5-base), `EMBEDDING_DIM` (768)
- `SENTIMENT_LABELS` (5 classes), `ASPECT_LIST` (goût, emballage, prix, disponibilité, fraîcheur)
- `CHANNELS` (facebook, google_maps, audio, youtube)
- `NSS_FORMULA` (documentation inline)
- `APIFY_API_KEY` (optionnel)
- Wave 5 : `DATABASE_URL`, `CURRENT_NORMALIZER_VERSION`, `SOURCE_HEALTH_THRESHOLD`

**Critères d'acceptation** : Tous les chemins existent ou sont créés au démarrage. Importable sans erreur. Valeurs par défaut permettant de lancer sans `.env`.

---

### 9.2 `app.py` — Point d'entrée Streamlit

**Description** : Fichier principal lancé par `streamlit run app.py`. Configure la page Streamlit, affiche la sidebar de navigation, route vers les pages.

**Algorithme** :
1. `st.set_page_config(title='RamyPulse', layout='wide')`
2. Sidebar avec logo textuel + navigation
3. Import conditionnel des pages via structure `pages/`

**Critères d'acceptation** : L'application démarre sans erreur. Navigation entre les 4 pages fonctionne. Layout responsive.

---

### 9.3 `pages/01_dashboard.py` — Dashboard principal ABSA + NSS

**Description** : Page d'accueil du dashboard. Affiche les KPIs principaux (NSS global, NSS par canal), la matrice ABSA interactive, les tendances temporelles.

**Inputs** : `data/processed/annotated.parquet` — colonnes `[text, sentiment_label, channel, aspect, source_url, timestamp, confidence]`.

**Outputs** : Visualisations Plotly interactives rendues dans Streamlit.

**Dépendances** : streamlit, pandas, plotly, `core.analysis.nss_calculator`.

**Algorithme** :
1. Charger le DataFrame annoté
2. Calculer NSS global via `nss_calculator`
3. Row de KPI cards : NSS global, volume total, nb canaux, période
4. Heatmap Plotly : matrice aspects × sentiments (colorscale divergent)
5. Bar chart : NSS par canal (horizontal)
6. Line chart : évolution NSS dans le temps (groupby semaine/jour)
7. Filtres sidebar : période, canal, aspect

**Critères d'acceptation** : Page en moins de 3 secondes. Matrice ABSA 5 × 5. KPI cards avec flèche directionnelle. Filtres mettent à jour toutes les visualisations.

---

### 9.4 `pages/02_explorer.py` — Explorateur de données

**Description** : Interface d'exploration avec filtres avancés. Permet de filtrer par canal, aspect, sentiment, période, et d'afficher les textes sources annotés.

**Algorithme** :
1. Filtres multiselect : canal, aspect, sentiment, période (`date_input`)
2. Appliquer les filtres (AND logique)
3. Donut chart : répartition des sentiments filtrés
4. `st.dataframe` paginé : texte tronqué, sentiment, aspect, canal, date, source
5. Expander par ligne : texte complet + lien source

**Critères d'acceptation** : Filtres en AND logique. Tableau avec au moins 50 lignes paginées. Chaque entrée avec lien source cliquable.

---

### 9.5 `pages/03_chat.py` — Interface Q&A RAG avec provenance

**Description** : Chat permettant au jury de poser des questions en langage naturel. Utilise le pipeline RAG pour fournir des réponses sourcées.

**Algorithme** :
1. `st.chat_input` pour la question
2. `retriever.search(question, top_k=5)`
3. `generator.generate(question, chunks)`
4. `st.chat_message('assistant')` avec réponse
5. Sources dans `st.expander` : texte du chunk, canal, URL, timestamp
6. Historique dans `st.session_state`

**Critères d'acceptation** : Chaque réponse contient au moins 1 source cliquable. Réponse "je n'ai pas assez d'informations" si les chunks ne couvrent pas la question. Pas d'hallucination détectable sur 20 questions test. Temps de réponse < 15 secondes.

---

### 9.6 `pages/04_whatif.py` — Simulation What-If

**Description** : Outil de simulation modélisant l'impact de changements sur un aspect donné.

**Algorithme** :
1. Selectbox : aspect (goût, emballage, prix, disponibilité, fraîcheur)
2. Radio : scénario (neutraliser, améliorer, dégrader)
3. `simulator.simulate(aspect, scenario, dataframe)`
4. Metric cards : NSS actuel / NSS simulé / Delta
5. Bar chart comparatif avant/après par canal
6. Texte d'interprétation généré

**Critères d'acceptation** : Delta vérifié manuellement. Visualisation avant/après claire. Interprétation cohérente avec le delta.

---

### 9.7 `core/ingestion/normalizer.py` — Normalisation dual-script

**Description** : Module central de nettoyage textuel. Gère Arabizi→Arabe, détection de script, nettoyage diacritiques et tatweel, normalisation graphémique.

**Inputs** : Texte brut (str) — Arabizi, Arabe, Français, ou mélange.

**Outputs** : `{"normalized": str, "original": str, "script_detected": str, "language": str}`

**Table de substitution Arabizi complète** :
- `7` → `ح`, `3` → `ع`, `9` → `ق`, `5` → `خ`, `2` → `ء`, `8` → `غ`, `6` → `ط`
- `ch` → `ش`, `gh` → `غ`, `kh` → `خ`, `th` → `ث`, `dh` → `ذ`, `sh` → `ش`

**Algorithme** :
1. Détection de script : ratio caractères arabes/latins
2. Si Arabizi : appliquer table de substitution phonétique
3. Unification graphèmes arabes : normaliser alef, ta marbuta, ya
4. Supprimer tatweel (ـ) et diacritiques (tashkeel)
5. Lowercase pour la partie latine
6. Nettoyer : URLs, mentions (@), hashtags, emojis excessifs, espaces multiples
7. Retourner le dict

**Critères d'acceptation** : Cohérence sur 50 exemples manuels. `"ramy m3andhoumch ta3m"` → texte arabe normalisé. `"le jus Ramy c'est bon"` → conservé en français, lowercase. Pas de perte sémantique.

---

### 9.8 `core/ingestion/audio_pipeline.py` — Pipeline ASR Whisper

**Description** : Transcription audio vers texte avec timestamps. Utilise faster-whisper pour transcrire fichiers audio (Darija, Français).

**Inputs** : Chemin fichier audio (str), format WAV/MP3/M4A.

**Outputs** : `[{"text": str, "start": float, "end": float, "language": str, "confidence": float}]`

**Algorithme** :
1. Charger le modèle Whisper V3 (large-v3 si GPU, small si CPU)
2. Transcrire avec `word_timestamps=True`
3. Segmenter par phrases (silences > 0.5s comme délimiteurs)
4. Pour chaque segment : texte, timestamp début/fin, langue détectée
5. Appliquer `normalizer.py` sur chaque segment
6. Retourner la liste de segments

**Note PoC** : Pour la démo, 3–5 enregistrements courts en Darija pré-enregistrés. Le module audio est ciblé pour l'intégration post-soumission (Jours 9–12).

**Critères d'acceptation** : 60 secondes d'audio transcrits en < 30 secondes (GPU) ou < 2 minutes (CPU). Timestamps précis à ±1 seconde.

---

### 9.9 `core/analysis/sentiment_classifier.py` — Classification DziriBERT

**Description** : Classifieur de sentiment basé sur DziriBERT fine-tuné sur dataset Algerian Dialect 45K. 5 classes discrètes. Inférence unitaire et batch.

**Inputs** : Texte nettoyé (str) ou liste de textes.

**Outputs** : `{"label": str, "confidence": float, "logits": list[float]}`

**Modèle** : `alger-ia/dziribert` + classification head (5 classes) fine-tunée.

**Paramètres de fine-tuning** :
- Dataset : Algerian Dialect 45K (arXiv:2512.19543) — Split 80/10/10
- Epochs : 3–5, Learning rate : 2e-5, Batch size : 16, Optimizer : AdamW, Max sequence length : 128 tokens

**Algorithme d'inférence** :
1. Tokenizer DziriBERT : encoder le texte
2. Forward pass → logits (5 classes)
3. Softmax → probabilités
4. Argmax → label
5. Retourner label, confidence, logits

**Mode batch** : DataLoader avec batch_size=32, inférence GPU/CPU, résultats en Parquet.

**Critères d'acceptation** : Accuracy > 75% sur test set (4 500 exemples). Inférence unitaire < 100ms. Modèle sauvegardé dans `models/dziribert/`. Fallback : zero-shot avec Ollama + prompt dialectal si fine-tuning échoue.

---

### 9.10 `core/analysis/aspect_extractor.py` — Extraction d'aspects

**Description** : Extracteur d'aspects basé sur dictionnaire bilingue. Détecte les mentions de 5 aspects Ramy dans Darija, Arabizi, Français.

**Inputs** : Texte nettoyé (str).

**Outputs** : `[{"aspect": str, "mention": str, "start": int, "end": int}]`

**Dictionnaire bilingue complet** :
- `goût` : `[ta3m, طعم, goût, saveur, madha9, bnin, ldid]`
- `emballage` : `[bouteille, plastique, قارورة, 9ar3a, emballage, packaging, علبة]`
- `prix` : `[ghali, rkhis, سعر, prix, cher, pas cher, t7ayol]`
- `disponibilité` : `[nlgah, ma_kaynch, متوفر, disponible, rupture, yla9awh]`
- `fraîcheur` : `[bared, skhoun, طازج, frais, froid, périmé, fraîcheur]`

**Algorithme** :
1. Pour chaque aspect, compiler les patterns regex (word boundary, insensible à la casse)
2. Scanner le texte pour chaque pattern
3. Enregistrer aspect, mention, position start/end pour chaque match
4. Gérer les overlaps : conserver les deux si deux aspects matchent le même span

**Critères d'acceptation** : Recall > 70% sur 100 exemples annotés manuellement. Chaque aspect avec position correcte. Dictionnaire extensible sans modification du code.

---

### 9.11 `core/analysis/absa_engine.py` — Pipeline ABSA complet

**Description** : Orchestre le pipeline ABSA complet. Combine l'extracteur d'aspects et le classifieur pour produire la matrice aspect × sentiment.

**Inputs** : DataFrame `[text, channel, source_url, timestamp]`.

**Outputs** : DataFrame enrichi `+ [sentiment_label, confidence, aspects, aspect_sentiments]`.

**Algorithme** :
1. Pour chaque texte : classifier le sentiment global
2. Extraire les aspects présents
3. Pour chaque aspect détecté : extraire la phrase contenant la mention, classifier le sentiment de cette phrase
4. Stocker `aspect_sentiments = [{aspect, mention, sentiment, confidence}]`
5. Sauver en `data/processed/annotated.parquet`

**Critères d'acceptation** : Toutes colonnes présentes. Chaque enregistrement a un sentiment global. Textes multi-aspects avec sentiments distincts par aspect. 1 000 textes en < 5 minutes (GPU).

---

### 9.12 `core/analysis/nss_calculator.py` — Calcul du NSS

**Description** : Calcule le NSS selon plusieurs dimensions : global, par canal, par aspect, en tendance temporelle.

**Formule** : `NSS = (nb_très_positif + nb_positif − nb_négatif − nb_très_négatif) / total × 100`

**Plage** : [−100, +100]. Interprétation : > 50 = excellent, 20–50 = bon, 0–20 = neutre, < 0 = problématique.

**Outputs** : `{"nss_global": float, "nss_by_channel": dict, "nss_by_aspect": dict, "trends": DataFrame, "volume_total": int, "distribution": dict}`

**Critères d'acceptation** : Cohérence sur comptage manuel de 100 samples. Toujours dans [−100, +100]. Aucune division par zéro (gérer volume=0).

---

### 9.13 `core/rag/embedder.py` — Génération d'embeddings

**Modèle** : `multilingual-e5-base` (768 dimensions). Préfixer avec `"query: "` ou `"passage: "` selon le contexte (requis par e5). Normalisation L2.

**Critères** : Vecteurs de dimension 768. Chargement < 10 secondes. Batch de 1 000 textes < 30 secondes (GPU).

---

### 9.14 `core/rag/vector_store.py` — Index FAISS

**Type d'index** : `IndexHNSWFlat(768, 32)`. Sauvegarde : `faiss.write_index` + metadata JSON parallèle.

**Critères** : Sauvegarde et rechargement corrects. Recherche top-10 < 50ms. Metadata synchronisées avec les vecteurs.

---

### 9.15 `core/rag/retriever.py` — Recherche hybride dense + BM25

**Algorithme** : Recherche dense FAISS + BM25 sparse → fusion par Reciprocal Rank Fusion (RRF) avec k=60.

**Outputs** : `[{"text": str, "channel": str, "url": str, "timestamp": str, "score": float}]`

**Critères** : Hybride plus pertinent que chaque méthode seule sur 10 queries test. < 500ms. Chaque résultat avec source.

---

### 9.16 `core/rag/generator.py` — Génération via Ollama

**Prompt système** : "Tu es un analyste de sentiment pour la marque Ramy. Réponds UNIQUEMENT à partir des extraits fournis ci-dessous. Cite les sources entre crochets [Source N]. Si les extraits ne contiennent pas assez d'information, réponds : Je n'ai pas assez d'informations dans les données analysées. Réponds en français. Format JSON : {answer, sources, confidence}."

**Critères** : Au moins 1 source par réponse. Réponse "je ne sais pas" quand chunks insuffisants. < 15 secondes.

---

### 9.17 `core/whatif/simulator.py` — Simulation de scénarios

**Scénarios** :
- `neutraliser` : supprimer les enregistrements de l'aspect du calcul NSS
- `améliorer` : remap très_négatif→négatif, négatif→neutre, neutre→positif, positif→très_positif
- `dégrader` : remap inverse

**Critères** : Delta vérifié manuellement. DataFrame original non modifié (copie). Interprétation cohérente avec le delta.

---

## 10. Spécifications des nouveaux composants (Wave 5)

### 10.1 `core/connectors/base_connector.py` — Interface abstraite

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseConnector(ABC):
    """Interface commune pour tous les connecteurs de sources."""

    def __init__(self, source: dict, credentials: dict):
        self.source = source
        self.credentials = credentials

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authentifie la connexion à la source. Retourne True si succès."""
        pass

    @abstractmethod
    async def fetch(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Récupère les enregistrements bruts depuis la source.
        `since` permet la synchronisation incrémentale."""
        pass

    @abstractmethod
    async def validate_schema(self, record: dict) -> bool:
        """Valide qu'un enregistrement brut a le schéma minimum requis."""
        pass

    async def run(self, since: Optional[datetime] = None) -> dict:
        """Exécution complète : authenticate → fetch → validate → return."""
        if not await self.authenticate():
            raise ConnectorAuthError(f"Authentication failed for source {self.source['source_id']}")
        records = await self.fetch(since)
        valid = [r for r in records if await self.validate_schema(r)]
        return {
            "records": valid,
            "records_fetched": len(records),
            "records_valid": len(valid),
            "records_rejected": len(records) - len(valid)
        }
```

---

### 10.2 `core/connectors/facebook_connector.py` — Connecteur Facebook Pages

**Description** : Connecte les pages Facebook gérées par le client via OAuth. Récupère les posts et commentaires. Gère la pagination et la déduplication par checksum.

**Inputs** : `source` (dict depuis table `sources`), `credentials` (page_access_token depuis secrets chiffrés).

**Outputs** : Liste de `raw_payload` JSON + `raw_text` + `raw_metadata` pour insertion dans `raw_documents`.

**Authentification** :
1. Récupérer le `user_access_token` depuis le vault de secrets
2. Échanger contre un `page_access_token` via Graph API
3. Valider la portée des permissions (`pages_read_engagement`, `pages_show_list`)

**Algorithme** :
1. `GET /{page_id}/posts?fields=id,message,created_time,permalink_url&since={since}`
2. Pour chaque post : `GET /{post_id}/comments?fields=id,message,from,created_time`
3. Dédupliquer par `SHA-256(raw_text + source_id + external_id)`
4. Construire le `raw_payload` JSONB complet avec toutes les métadonnées Meta
5. Retourner la liste pour insertion dans `raw_documents`

**Critères d'acceptation** : Fallback gracieux si token expiré (log + alerte source_health). Pagination complète jusqu'à `since`. Déduplication correcte. Zéro données inter-client possibles.

---

### 10.3 `core/connectors/google_maps_connector.py` — Connecteur Google Business Profile

**Description** : Connecte les établissements du client via Google Business Profile API. Récupère les reviews.

**Authentification** : OAuth 2.0 avec scopes `https://www.googleapis.com/auth/business.manage`.

**Algorithme** :
1. `GET /v4/accounts/{accountId}/locations`
2. Pour chaque location : `GET /v4/accounts/{accountId}/locations/{locationId}/reviews`
3. Extraire `rating`, `comment`, `createTime`, `reviewer.displayName`
4. Construire `raw_payload` avec rating comme métadonnée distincte

**Critères d'acceptation** : Le champ `rating` (1–5 étoiles) est conservé dans `raw_metadata`. Gestion de la pagination `nextPageToken`.

---

### 10.4 `core/connectors/youtube_connector.py` — Connecteur YouTube

**Description** : Récupère les commentaires des chaînes et vidéos ciblées via YouTube Data API v3.

**Endpoints utilisés** : `commentThreads.list`, `comments.list`.

**Algorithme** :
1. Selon `source_type` : récupérer la liste des vidéos de la chaîne ou cibler une vidéo directement
2. `GET commentThreads?part=snippet&videoId={videoId}&maxResults=100`
3. Pour chaque thread : récupérer les réponses via `comments.list`
4. Gérer le quota API (10 000 unités/jour par défaut)

**Critères d'acceptation** : Respect des quotas YouTube (ne pas dépasser la limite journalière). Gestion du `nextPageToken` pour la pagination complète.

---

### 10.5 `core/connectors/batch_import_connector.py` — Connecteur import batch

**Description** : Traite les fichiers CSV, Excel, Parquet déposés par le client. Valide le schéma, signale les erreurs de format, conserve le fichier brut.

**Inputs** : Chemin fichier (CSV/Excel/Parquet), mapping de colonnes (dict).

**Algorithme** :
1. Détecter le format par extension
2. Charger avec pandas en respectant les types déclarés
3. Valider le schéma : colonnes obligatoires présentes, types corrects
4. Remonter les erreurs ligne par ligne (ne pas bloquer l'import total sur une erreur partielle)
5. Mapper les colonnes client vers le schéma `raw_documents`
6. Insérer avec `sync_run_id` pour traçabilité

**Critères d'acceptation** : Rapport d'erreurs ligne par ligne. Fichier brut conservé même si des lignes sont rejetées. `records_fetched`, `records_inserted`, `records_failed` correctement comptés dans `source_sync_runs`.

---

### 10.6 `core/ingestion/orchestrator.py` — Orchestrateur APScheduler

**Description** : Charge la liste des sources actives au démarrage et crée les jobs périodiques correspondants. Gère le cycle de vie complet d'un run de synchronisation.

**Inputs** : Table `sources` (PostgreSQL).

**Algorithme** :
1. Au démarrage : `SELECT * FROM sources WHERE is_active = true`
2. Pour chaque source : `scheduler.add_job(run_sync_for_source, trigger='interval', minutes=sync_frequency_minutes, id=f"sync_{source_id}", replace_existing=True)`
3. Job `normalization_job` : toutes les 5 minutes, batch 200 documents non normalisés
4. Job `source_health_check_job` : toutes les 60 minutes, vérifie SLA et calcule health score
5. Job `alert_detection_job` : toutes les 30 minutes, exécute les règles sur les métriques calculées
6. Permettre le rechargement dynamique sans redémarrage si une source est ajoutée/modifiée

**Critères d'acceptation** : Tous les jobs se relancent après redémarrage du processus (état dans PostgreSQL). Un job en échec ne bloque pas les autres. Logs structurés pour chaque run.

---

### 10.7 `core/ingestion/health_checker.py` — Moteur de santé des sources

**Description** : Calcule le `source_health_score` pour chaque source active et génère des alertes de type `source_health` si le score passe sous le seuil ou si le SLA est breached.

**Algorithme** :

```python
async def compute_health_score(source_id: str) -> float:
    # 1. Taux de réussite des 10 derniers runs
    last_10 = await db.fetch_all("""
        SELECT status FROM source_sync_runs
        WHERE source_id = :id
        ORDER BY started_at DESC LIMIT 10
    """, {"id": source_id})
    success_rate = sum(1 for r in last_10 if r.status == 'success') / max(len(last_10), 1)

    # 2. Âge depuis la dernière sync réussie vs SLA
    last_success = await db.fetchrow("""
        SELECT ended_at FROM source_sync_runs
        WHERE source_id = :id AND status = 'success'
        ORDER BY ended_at DESC LIMIT 1
    """, {"id": source_id})
    age_hours = (datetime.now() - last_success.ended_at).total_seconds() / 3600 if last_success else 9999
    sla = await db.fetchval("SELECT freshness_sla_hours FROM sources WHERE source_id = :id", {"id": source_id})
    sla_ratio = min(age_hours / sla, 2.0)  # Cappé à 2x le SLA

    # 3. Drift de volume (ratio vs moyenne historique)
    avg_volume = await db.fetchval("""
        SELECT AVG(records_fetched) FROM source_sync_runs
        WHERE source_id = :id AND status = 'success'
        AND started_at > NOW() - INTERVAL '30 days'
    """, {"id": source_id})
    last_volume = last_10[0].records_fetched if last_10 else 0
    volume_drift = abs(last_volume - avg_volume) / max(avg_volume, 1) if avg_volume else 1.0

    # 4. Erreurs consécutives
    consecutive_errors = sum(1 for r in last_10 if r.status == 'failed')

    score = (
        success_rate * 50
        + max(0, (1 - sla_ratio) * 30)
        + max(0, (1 - volume_drift) * 10)
        + max(0, (1 - consecutive_errors / 10) * 10)
    )
    return round(score, 2)
```

**Critères d'acceptation** : Score entre 0 et 100. Alerte `source_health` générée si score < `SOURCE_HEALTH_THRESHOLD` (défaut : 60). Snapshot inséré dans `source_health_snapshots` à chaque calcul.

---

### 10.8 `core/normalization/normalizer_pipeline.py` — Pipeline de normalisation

**Description** : Job de normalisation batch. Lit les `raw_documents` non normalisés, applique la transformation, écrit dans `normalized_records` et `enriched_signals`.

**Paramètre clé** : `CURRENT_NORMALIZER_VERSION` depuis `config.py`. Toute modification de la logique de normalisation incrémente cette version et déclenche un reprocessing sélectif.

**Algorithme** :
1. `SELECT * FROM raw_documents WHERE is_normalized = false ORDER BY collected_at ASC LIMIT 200`
2. Pour chaque document :
   - Appliquer `normalizer.py` (nettoyage textuel)
   - Détecter le canal, la langue, le script
   - Insérer dans `normalized_records`
   - Appliquer `absa_engine` → insérer dans `enriched_signals`
   - `UPDATE raw_documents SET is_normalized = true, normalizer_version = :version`
3. En cas d'erreur sur un document : logguer, continuer avec le suivant (ne pas bloquer le batch)

**Critères d'acceptation** : Aucun document bloquant le batch. `normalizer_version` correctement propagé. Reprocessing fonctionnel via reset du flag.

---

## 11. Watchlists — Spécifications détaillées

### 11.1 Définition

Une watchlist n'est pas une liste de mots-clés. C'est une définition explicite d'un périmètre métier à surveiller, combinant des entités (produit, région, distributeur), des dimensions (canal, aspect, métrique), et une période.

### 11.2 Exemples de watchlists valides

| Nom | Périmètre | Métrique | Période |
|---|---|---|---|
| Livraison Oran | NSS livraison, canal google_maps, wilaya Oran | NSS aspect disponibilité | Hebdomadaire |
| Emballage Ouest Facebook | Aspect emballage, canal facebook, wilayas {Oran, Tlemcen, Sidi Bel Abbès} | NSS aspect emballage | Hebdomadaire |
| Goût Gamme Premium Constantine | Produit gamme Premium, aspect goût, wilaya Constantine | NSS aspect goût | Mensuel |
| Fraîcheur Google Maps | Canal google_maps, aspect fraîcheur, toutes wilayas | Volume négatif + très négatif | Hebdomadaire |
| Divergence Canal FB vs Maps | Canal facebook vs google_maps, tous aspects | Écart NSS inter-canal | Hebdomadaire |

### 11.3 Règles de construction

Une watchlist peut combiner n'importe quelle combinaison de :
- `source_id` (nullable)
- `product_id` (nullable)
- `region_id` (nullable)
- `distributor_id` (nullable)
- `channel` (nullable)
- `aspect` (nullable)
- `metric_type`
- `period_type`

Les filtres null signifient "toutes les valeurs de cette dimension". La combinaison de filtres non-null est en AND logique.

### 11.4 Calcul des métriques par watchlist

Pour chaque watchlist active, le moteur analytique calcule à chaque cycle :

```python
async def compute_watchlist_metrics(watchlist_id: str) -> dict:
    filters = await get_watchlist_filters(watchlist_id)
    query = build_filtered_query(filters)  # SQL dynamique avec jointures
    df = await db.fetch_dataframe(query)
    return nss_calculator.calculate_all(df, period=filters.period_type)
```

### 11.5 Watchlists suggérées automatiquement (Wave 5.3+)

Le système peut suggérer des watchlists à partir des patterns détectés. Si une divergence inter-wilaya dépasse un seuil sur 3 cycles consécutifs sans watchlist associée, le système génère une suggestion avec justification.

---

## 12. Moteur d'alertes — Spécifications détaillées

### 12.1 Les 5 types de détection

**Type 1 — Règle absolue**

Déclenche si une métrique passe sous ou au-dessus d'un seuil fixe.

Exemple : NSS disponibilité Oran passe sous 20.

```sql
-- Règle : metric_type = 'nss_aspect', comparator = 'lt', threshold_value = 20
```

**Type 2 — Variation relative**

Déclenche si une métrique varie de plus de X% par rapport à la période précédente.

Exemple : NSS livraison baisse de 15% vs semaine précédente.

```python
delta_pct = (current - previous) / abs(previous) * 100
if comparator == 'lt' and delta_pct < -threshold_value:
    trigger_alert()
```

**Type 3 — Anomalie statistique**

Déclenche si une valeur s'écarte de plus de N écarts-types de la moyenne historique du lookback window.

Exemple : Volume négatif cette semaine anormalement élevé vs les 8 dernières semaines.

```python
z_score = (current_value - historical_mean) / historical_std
if abs(z_score) > threshold_value:  # threshold = 2.0 ou 3.0
    trigger_alert()
```

**Type 4 — Dérive temporelle**

Déclenche si une métrique se dégrade de manière continue sur N périodes consécutives.

Exemple : NSS goût en baisse 3 semaines de suite.

```python
last_n_values = get_last_n_periods(metric, n=lookback_window)
if all(last_n_values[i] < last_n_values[i-1] for i in range(1, len(last_n_values))):
    trigger_alert()
```

**Type 5 — Divergence entre segments**

Déclenche si l'écart entre deux segments (wilayas, canaux, distributeurs) dépasse un seuil.

Exemple : NSS facebook dans l'est > NSS facebook dans l'ouest de plus de 25 points.

```python
segment_a = compute_nss(filter_segment_a)
segment_b = compute_nss(filter_segment_b)
if abs(segment_a - segment_b) > threshold_value:
    trigger_alert()
```

### 12.2 Structure complète d'une alerte

Chaque alerte doit contenir :

| Champ | Description | Exemple |
|---|---|---|
| `title` | Titre court actionnable | "NSS livraison Oran en chute de 14 points" |
| `description` | Explication métier détaillée | "Le score de satisfaction livraison dans la wilaya d'Oran a baissé de 47 à 33 entre la semaine du 10 mars et celle du 17 mars. Cette baisse est principalement portée par les avis Google Maps." |
| `severity` | Criticité calculée | critical / high / medium / low |
| `metric_type` | Métrique concernée | nss_aspect_disponibilité |
| `scope` | Périmètre concerné | {canal: google_maps, wilaya: Oran, aspect: disponibilité} |
| `period` | Période de détection | 2026-W11 vs 2026-W10 |
| `alert_payload` | Contexte calculé complet | {current: 33, previous: 47, delta: -14, delta_pct: -29.8, z_score: -2.3} |
| `navigation_url` | Lien direct vers la vue | /explorer?canal=google_maps&wilaya=Oran&aspect=disponibilite |
| `detected_at` | Timestamp de détection | 2026-03-17T08:00:00Z |
| `dedup_key` | Clé de déduplication | `nss_disponibilite_oran_google_maps_W11` |

### 12.3 Cycle de vie complet d'une alerte

```
new → acknowledged → investigating → resolved
              ↓                          ↑
           dismissed                 (si recurrence)
```

| État | Signification | Transition |
|---|---|---|
| `new` | Alerte détectée, non vue | Automatique à la création |
| `acknowledged` | Vue par un utilisateur | Action manuelle |
| `investigating` | En cours d'analyse | Action manuelle |
| `resolved` | Problème résolu ou métrique revenue à la normale | Manuel ou auto si métrique repasse le seuil |
| `dismissed` | Ignorée (faux positif ou non pertinente) | Action manuelle |

### 12.4 Déduplication

Une alerte avec le même `dedup_key` ne peut exister qu'une seule fois en statut `new`, `acknowledged`, ou `investigating`. Si la même condition est détectée lors d'un cycle suivant et que l'alerte existante est déjà dans ces états, le cycle est ignoré (pas de doublon).

Si l'alerte a été `resolved` ou `dismissed`, une nouvelle alerte peut être créée pour la même condition (récurrence).

### 12.5 Scoring de criticité

```python
def compute_severity(delta_pct: float, z_score: float, volume: int) -> str:
    score = 0
    if abs(delta_pct) > 30: score += 3
    elif abs(delta_pct) > 15: score += 2
    else: score += 1

    if abs(z_score) > 3: score += 3
    elif abs(z_score) > 2: score += 2
    else: score += 1

    if volume > 500: score += 1  # Plus de volume = plus significatif

    if score >= 6: return 'critical'
    if score >= 4: return 'high'
    if score >= 2: return 'medium'
    return 'low'
```

---

## 13. Flux d'ingestion par type de source

### 13.1 Flux API officielle

```
1. Le client connecte son compte via OAuth dans l'interface RamyPulse
2. RamyPulse stocke les tokens chiffrés dans le vault de secrets
3. Le connecteur enregistre les métadonnées source dans la table `sources`
4. L'orchestrateur APScheduler crée un job selon `sync_frequency_minutes`
5. À chaque déclenchement :
   a. INSERT dans `source_sync_runs` (status = 'running')
   b. Connecteur appelle l'API avec les credentials déchiffrés
   c. Les documents bruts sont insérés dans `raw_documents` (is_normalized = false)
   d. UPDATE `source_sync_runs` (status = 'success', counts)
   e. UPDATE `sources.last_sync_at`
6. Le job `normalization_job` (toutes les 5 minutes) traite les documents en attente
7. Les signaux enrichis alimentent les vues watchlists et le moteur d'alertes
```

### 13.2 Flux import batch

```
1. Le client dépose un fichier via l'interface (CSV, Excel, Parquet)
2. RamyPulse valide le schéma d'entrée (colonnes obligatoires présentes)
3. Les erreurs de format sont remontées ligne par ligne avant traitement
4. Une `source_sync_runs` est créée avec `run_mode = 'manual'`
5. Le fichier brut est conservé dans `raw_documents` (checksum calculé)
6. Les lignes valides sont marquées `is_normalized = false`
7. Le job `normalization_job` les traite dans son prochain cycle
8. Les métriques watchlists sont recalculées après enrichissement
9. Si des règles d'alerte sont satisfaites, les alertes sont créées
```

### 13.3 Flux collecte publique cadrée

```
1. Une source publique est enregistrée (owner_type = 'public', auth_mode = 'public')
2. Le rythme de collecte est défini (ex : batch quotidien)
3. À chaque déclenchement, le collecteur récupère les signaux accessibles
4. Les snapshots sont historisés dans `raw_documents`
5. Les enregistrements sont normalisés par le job de normalisation
6. Les règles de qualité et de conformité sont appliquées (filtrage de contenu)
7. Les signaux valides alimentent la veille et les alertes
```

---

## 14. Sécurité, isolation et traçabilité

### 14.1 Multi-tenant strict

Chaque `client_id` doit filtrer toutes les requêtes à tous les niveaux. Aucune jointure ne peut traverser les limites tenant sans `client_id` explicite.

Règle obligatoire sur toutes les queries Wave 5 :
```sql
WHERE client_id = :current_client_id
```

Un middleware FastAPI injecte le `client_id` depuis le contexte d'authentification dans toutes les requêtes.

### 14.2 Gestion des secrets OAuth

Les tokens OAuth ne sont jamais stockés en clair dans la base de données. Architecture :
- Vault de secrets dédié (Vault par HashiCorp en production, variable d'environnement chiffrée en développement)
- Rotation automatique des tokens quand l'expiry est détectée
- Journalisation des accès aux secrets sans journalisation des valeurs
- Zéro exposition côté front

### 14.3 Auditabilité complète

Pour chaque alerte, il doit être possible de répondre à :
- Quelle source a produit les données sous-jacentes ?
- Quel run de synchronisation a collecté ces données ?
- Quelle version du normalizer a traité ces données ?
- Quelle règle d'alerte a détecté cette condition ?
- Quelles métriques calculées ont déclenché l'alerte ?
- À quelle heure précise ?

### 14.4 Historisation et rétention

Les `raw_documents` sont conservés selon une stratégie de rétention configurable par client. Par défaut : 12 mois. Les `source_health_snapshots` sont conservés 6 mois. Les `alerts` sont conservées 24 mois.

### 14.5 Standards entreprise à viser

- OAuth pour tous les comptes autorisés
- Permissions minimales (scopes limités aux besoins réels)
- Journalisation de toutes les synchronisations dans `source_sync_runs`
- Historisation des snapshots bruts
- Séparation stricte source brute / donnée enrichie
- Mapping métier explicite (produit, wilaya, distributeur)
- Watchlists configurables par l'administrateur client
- Moteur d'alerting avec seuils et détection d'anomalies
- Auditabilité complète de chaque alerte

---

## 15. Roadmap d'implémentation

### Wave 1–4 — PoC AI EXPO 2026 (complété ou en cours)

**Statut cible : soumission 3 avril 2026**

| Phase | Tâches clés | Critère de fin |
|---|---|---|
| Phase 1 — Données (J1–2) | Dataset fallback 45K, normalizer.py, scrapers, clean.parquet | clean.parquet généré, 45K lignes |
| Phase 2 — Moteur IA (J3–5) | Fine-tuning DziriBERT, aspect_extractor, absa_engine, FAISS | annotated.parquet + faiss.index |
| Phase 3 — Interface (J6–7) | Dashboard, Explorer, Chat RAG, What-If | 4 pages fonctionnelles |
| Phase 4 — Polish (J8) | Test end-to-end, script one-click, soumission | Démo 15 min sans crash |
| Phase 5 — Démo (J9–21) | Audio pipeline, RAG amélioré, UI polish, scénario démo | Démo live 16 avril |

---

### Wave 5.1 — Registre de sources et ingestion structurée

**Objectif** : RamyPulse peut ingérer proprement plusieurs sources avec suivi d'exécution.

**Décisions d'architecture** : APScheduler in-process, PostgreSQL comme seul état persistant, Docker Compose minimal.

**Livrables** :
- Modèle de données : tables `clients`, `sources`, `source_sync_runs`, `raw_documents`
- Colonnes additionnelles : `freshness_sla_hours` sur `sources`, `is_normalized` + `normalizer_version` sur `raw_documents`
- Interface abstraite `BaseConnector`
- Connecteur `BatchImportConnector` fonctionnel
- Orchestrateur `APScheduler` avec jobs planifiés par source
- Job `normalization_job` (batch polling, LIMIT 200)
- Job `source_health_check_job` (toutes les 60 minutes)
- Table `source_health_snapshots`
- Journalisation structurée de tous les runs

**Critère de sortie** : Un fichier CSV déposé par un client est ingéré, normalisé, et disponible dans `enriched_signals` avec traçabilité complète dans `source_sync_runs`.

---

### Wave 5.2 — Modèle métier et normalisation

**Objectif** : Les données collectées deviennent exploitables dans un vocabulaire business.

**Livrables** :
- Tables `products`, `regions`, `distributors`
- Interface d'administration pour créer et gérer ces entités
- Pipeline de mapping source → entités métier (rattachement automatique par règles configurables)
- Versionnement des enrichissements (`normalizer_version`, `enrichment_version`)
- Connecteurs officiels : `FacebookConnector`, `GoogleMapsConnector`, `YouTubeConnector`
- Migration des données Wave 1–4 vers `normalized_records` + `enriched_signals`
- Script de reprocessing sélectif par `normalizer_version`

**Critère de sortie** : Les données sont requêtables en termes de produit, wilaya, distributeur — pas seulement d'URL et d'ID technique.

---

### Wave 5.3 — Watchlists et métriques surveillées

**Objectif** : L'utilisateur peut définir explicitement ce qu'il veut surveiller.

**Livrables** :
- Tables `watchlists`, `watchlist_filters`
- Interface de création et gestion des watchlists
- Moteur de calcul des métriques par périmètre watchlist
- Écrans dédiés watchlists avec comparaisons temporelles
- Système de suggestion automatique de watchlists (patterns détectés sans watchlist associée)
- Migration orchestrateur vers Prefect si conditions remplies (> 15 sources actives)
- Migration normalisation vers PostgreSQL LISTEN/NOTIFY si latence problématique

**Critère de sortie** : Un utilisateur peut créer une watchlist "NSS livraison Oran sur Google Maps, semaine par semaine" et voir les métriques calculées automatiquement.

---

### Wave 5.4 — Alerting engine

**Objectif** : RamyPulse signale automatiquement les événements significatifs.

**Livrables** :
- Tables `alert_rules`, `alerts`
- Moteur de règles : 5 types de détection implémentés
- Job `alert_detection_job` (toutes les 30 minutes)
- Scoring de criticité automatique
- Centre d'alertes dans l'interface (liste, filtres par sévérité et statut)
- Gestion du cycle de vie des alertes (new → acknowledged → investigating → resolved/dismissed)
- Déduplication par `dedup_key`
- Alertes `source_health` générées par le `source_health_check_job`

**Critère de sortie** : Sans aucune intervention utilisateur, RamyPulse détecte et affiche : "Le NSS livraison Oran a baissé de 14 points cette semaine" avec justification calculée et lien vers les données.

---

### Wave 5.5 — Notifications et industrialisation

**Objectif** : Le système devient crédible en contexte entreprise réel.

**Livrables** :
- Notifications e-mail (SMTP configurable)
- Webhooks configurables par watchlist
- Intégration Slack (webhook entrant)
- Gestion des préférences de notification par utilisateur
- Sécurisation complète des secrets OAuth (Vault ou équivalent)
- Audit logs pour toutes les actions administratives
- Observabilité : métriques de performance des jobs (temps d'exécution, volumes traités)
- Durcissement multi-tenant : tests d'isolation inter-client
- Documentation opérationnelle

**Critère de sortie** : Un client reçoit une alerte Slack ou e-mail automatique quand sa watchlist déclenche. Les secrets sont chiffrés. Les données sont isolées entre clients.

---

### Wave 6 — Vision long terme

**Sujets à évaluer après stabilisation Wave 5 :**
- Surveillance publique de la concurrence (veille territoriale étendue)
- Collecte audio en production (terrain, SAV, call centers)
- Modèle de données temporel avec snapshots historiques longue durée
- Interface d'auto-configuration des watchlists par le client (sans développeur)
- API publique RamyPulse pour intégration client (webhooks entrants)
- Déploiement multi-région (Béjaïa, Alger, Oran simultanément)
- Extension à d'autres marques agroalimentaires algériennes

---

## 16. Dépendances et requirements.txt

### 16.1 Packages Wave 1–4 (PoC)

```
transformers>=4.40
torch>=2.2
sentence-transformers>=3.0
faiss-cpu>=1.8
streamlit>=1.35
pandas>=2.2
plotly>=5.20
rank-bm25>=0.2.2
requests>=2.31
beautifulsoup4>=4.12
faster-whisper>=1.0
ollama>=0.3
python-dotenv>=1.0
pyarrow>=15.0
numpy>=1.26
```

### 16.2 Packages additionnels Wave 5

```
fastapi>=0.111
uvicorn>=0.30
asyncpg>=0.29
sqlalchemy>=2.0
alembic>=1.13
apscheduler>=3.10
httpx>=0.27
google-auth>=2.29
google-auth-oauthlib>=1.2
google-api-python-client>=2.130
prefect>=3.0           # Wave 5.3+
aiosmtplib>=3.0        # Wave 5.5 — notifications e-mail
hvac>=2.1              # Wave 5.5 — HashiCorp Vault client
pydantic>=2.7
pydantic-settings>=2.2
```

### 16.3 Prérequis système

- Python 3.10+
- Ollama (ollama.com) avec modèle : `ollama pull llama3.2:3b` ou `ollama pull qwen2.5:7b`
- PostgreSQL 15+ (Wave 5)
- GPU NVIDIA avec CUDA (recommandé pour fine-tuning et inférence)
- FFmpeg (requis par faster-whisper)
- Docker + Docker Compose (recommandé pour Wave 5)

---

## 17. Risques et mitigations

### Risques Wave 1–4

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Échec du scraping (blocage FB/Google) | Haute | Critique | Fallback dataset 45K arXiv:2512.19543. Système fonctionnel avec données locales. |
| GPU insuffisant pour fine-tuning | Moyenne | Élevé | Batch nocturne, batch_size=8, gradient accumulation. Fallback : DziriBERT zero-shot + Ollama. |
| Ollama trop lent pour Q&A live | Moyenne | Moyen | Pré-générer 20 réponses. Cache dans `st.session_state`. Utiliser llama3.2:3b. Spinner visible. |
| Qualité aspect extractor insuffisante | Moyenne | Moyen | Enrichir le dictionnaire. Fallback LLM pour extraction (plus lent, plus précis). |
| Crash pendant la démo | Basse | Critique | Script `05_run_demo.py` vérifie tous les prérequis. Données entièrement pré-calculées. Backup screenshots. |

### Risques Wave 5

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Token OAuth expiré en production | Haute | Élevé | Détection automatique à chaque run. Alerte source_health immédiate. Refresh token si disponible. |
| Source cassée silencieusement | Moyenne | Critique | `data_freshness_sla_hours` + `source_health_check_job` toutes les 60 minutes. Alerte dédiée. |
| Fuite de données inter-client | Basse | Critique | Middleware `client_id` sur toutes les queries. Tests d'isolation automatisés avant chaque déploiement. |
| Combinatoire watchlist trop grande | Moyenne | Moyen | Limiter le nombre de filtres combinables par watchlist (max 5). Optimisation des indexes PostgreSQL. |
| Volume de données dépassant les capacités locales | Moyenne | Élevé | Migration vers stockage objet (S3 ou équivalent MinIO) pour les `raw_documents`. Partitionnement PostgreSQL par `client_id` + mois. |
| Normalizer_version non incrémentée après modification | Haute | Élevé | Convention obligatoire documentée + test automatisé vérifiant la version avant chaque merge. |

---

## 18. Critères de succès par wave

### Wave 1–4 — Soumission 3 avril 2026

| Critère | Seuil | Vérification |
|---|---|---|
| Code fonctionnel | Le système démarre sans erreur | `python scripts/05_run_demo.py` → Streamlit accessible |
| Dataset traité | > 10 000 textes annotés | `annotated.parquet` volume vérifié |
| Modèle fine-tuné | Accuracy > 75% | Évaluation sur test set (4 500 exemples) |
| Dashboard opérationnel | 4 pages sans crash | Navigation complète testée |
| RAG fonctionnel | Réponses sourcées sur 10 questions | Test manuel avec questions variées |
| Rapport soumis | Avant 23h59 le 3 avril | Confirmation reçue |

### Wave 1–4 — Démo 16 avril 2026

| Critère | Seuil | Vérification |
|---|---|---|
| Stabilité | 15 minutes sans crash | Timer pendant navigation complète |
| Q&A interactif | Réponse avec sources à toute question du jury | Test live |
| Insights actionnables | Au moins 3 insights identifiables | Le jury identifie 3 infos utiles pour Ramy |
| What-If convaincant | Simulation en direct cohérente | Demo : améliorer emballage → impact NSS visible |
| Provenance | Chaque insight lié à sa source | Clic sur insight → texte source + URL/timestamp |
| Différenciation | Le jury comprend la valeur vs Sprinklr | Pitch 3 killer features en 2 minutes |

### Wave 5.1

| Critère | Seuil |
|---|---|
| Ingestion CSV | Un fichier déposé est intégrable en < 2 minutes |
| Traçabilité | Chaque run documenté dans `source_sync_runs` |
| Normalisation | `is_normalized = false` traité en < 5 minutes (batch 200) |
| Health check | Score calculé pour chaque source toutes les 60 minutes |

### Wave 5.4

| Critère | Seuil |
|---|---|
| Détection | Les 5 types de règles déclenchent correctement sur des données test |
| Déduplication | Zéro doublon sur `dedup_key` actif |
| Latence | Alerte créée en < 5 minutes après détection de la condition |
| Cycle de vie | Transitions d'état fonctionnelles pour tous les statuts |

### Wave 5.5

| Critère | Seuil |
|---|---|
| Isolation | Zéro fuite inter-client sur suite de tests dédiée |
| Notifications | E-mail et webhook déclenchés < 10 minutes après création de l'alerte |
| Secrets | Aucun token en clair dans la base de données ou les logs |
| Observabilité | Métriques de performance des jobs disponibles |

---

## 19. Hors périmètre immédiat

Les éléments suivants sont volontairement exclus du périmètre Wave 5 pour maintenir le focus :

- Scraping à large échelle non cadré
- Surveillance libre de plateformes fermées sans accès officiel
- Temps réel systématique sur toutes les sources
- IA générative trop complexe avant stabilisation de l'ingestion
- Alerting avancé (ML-based) avant constitution d'un historique propre de 3 mois minimum
- Interface d'auto-configuration complète des watchlists sans développeur (Wave 6)

---

## 20. Glossaire

| Terme | Définition |
|---|---|
| ABSA | Aspect-Based Sentiment Analysis — analyse de sentiment par aspect (goût, emballage, etc.) |
| NSS | Net Sentiment Score — métrique centrale de RamyPulse, plage [−100, +100] |
| Darija | Dialecte arabe algérien — langue cible principale du système |
| Arabizi | Translittération du dialecte arabe en caractères latins et chiffres |
| DziriBERT | Modèle BERT fine-tuné pour le dialecte algérien (alger-ia/dziribert) |
| Watchlist | Définition explicite d'un périmètre métier à surveiller (produit × région × canal × aspect) |
| Alert Rule | Règle de détection associée à une watchlist — définit le type de détection et le seuil |
| Source Health Score | Score 0–100 de fiabilité d'une source — basé sur taux de réussite, SLA, drift de volume |
| Freshness SLA | Délai maximum acceptable entre deux synchronisations réussies pour une source donnée |
| normalizer_version | Version du pipeline de normalisation ayant produit un enregistrement — permet le reprocessing sélectif |
| dedup_key | Clé unique par alerte active — empêche la création de doublons sur la même condition |
| Batch polling | Pattern de normalisation : job périodique lit les documents non normalisés et les traite par batch |
| RAG | Retrieval-Augmented Generation — architecture Q&A combinant recherche vectorielle et LLM |
| RRF | Reciprocal Rank Fusion — algorithme de fusion des résultats dense + sparse du retriever |
| Multi-tenant | Architecture où plusieurs clients partagent la même infrastructure avec isolation stricte des données |
| owned source | Source appartenant au client (sa propre page Facebook, son propre établissement GBP) |
| Wave | Unité de livraison du projet RamyPulse — ensemble cohérent de fonctionnalités livrables |

---

*Ce document est la spécification de référence complète pour le développement de RamyPulse.*
*Il est conçu pour être directement exploitable par les agents de codage IA (Claude Code, Codex, GitHub Copilot) dans l'environnement Antigravity IDE.*
*Version 2.0 — 30 mars 2026*
