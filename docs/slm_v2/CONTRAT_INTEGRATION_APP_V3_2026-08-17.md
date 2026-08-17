# Contrat d’intégration application V3 — SLM V0.4

**Statut :** implémenté sur `codex/lidal-pulse-v3`, activation pilote en attente des portes qualité
**Produit :** LIDAL Pulse V3
**Contrat source :** `business_comment_annotation_v0.4.schema.json`

## 1. Décision d’architecture

L’application ne consomme jamais directement le texte généré par le SLM. La sortie
compacte passe par le compilateur déterministe, qui restaure les offsets, la cible de
surveillance, `schema_version` et `actionability`, puis valide le résultat contre le
schéma V0.4.

```text
document normalisé
  → sortie compacte du SLM
  → compilateur V0.4
  → validation JSON Schema
  → annotation canonique
  → projections métier et API
```

Ce contrat reste identique pour un modèle `answer-only` ou un futur modèle avec
raisonnement sélectif. L’application dépend du schéma compilé, jamais de la variante
d’entraînement.

## 2. Enveloppe canonique d’un signal

Chaque analyse persistée doit conserver :

```json
{
  "signal_id": "sig_...",
  "client_id": "client_...",
  "text": "commentaire original",
  "source": {
    "channel": "google_maps",
    "source_url": "https://...",
    "published_at": "2026-08-17T12:00:00Z",
    "wilaya": "Alger"
  },
  "analysis": {
    "schema_version": "0.4.0",
    "annotation": {},
    "raw_model_output": "...",
    "validation_status": "valid",
    "model_version": "lidal-slm-...",
    "compiler_version": "wire-v0.4",
    "inference_ms": 2680,
    "created_at": "2026-08-17T12:00:03Z"
  },
  "legacy_projection": {
    "sentiment_label": "négatif",
    "aspect": "service_client_sav"
  }
}
```

`raw_model_output` est réservé au diagnostic et ne doit pas être exposé aux
utilisateurs métier. `annotation` est la seule vérité applicative.

## 3. Règles de projection historique

La projection permet de conserver les écrans V2 pendant la migration :

| V0.4 | Projection historique |
|---|---|
| `sentiment.label=positif`, intensité forte | `très_positif` |
| `sentiment.label=negatif`, intensité forte | `très_négatif` |
| autre sentiment | valeur normalisée équivalente |
| plusieurs aspects | première famille dans `aspect` |
| aucune famille | `aspect=null` |

La projection est un mécanisme de compatibilité, pas une donnée de référence. Le
sentiment `mixte`, les aspects secondaires, les entités et les preuves restent dans
l’annotation V0.4 même si un ancien écran ne les affiche pas.

## 4. Règles des indicateurs métier

Un signal n’entre dans les KPI d’opinion client que si :

- `is_exploitable=true` ;
- `business_relevance` vaut `directe` ou `indirecte` selon l’indicateur ;
- `author_role=consommateur` ;
- `requires_parent_context=false`.

Les autres signaux restent consultables dans l’Explorateur avec leur motif
d’exclusion. Ils ne doivent pas fausser le NSS ou les tendances.

Les aspects sont agrégés par `(family, attribute, target_entity_id, sentiment)`, et
non plus par un unique champ texte. Les alertes sont agrégées par type, sévérité et
entité cible.

## 5. Contrat API transitoire

Pendant la migration, les routes actuelles restent valides. Chaque élément de
`/api/explorer/verbatims` et `/api/explorer/search` peut recevoir les champs
additionnels suivants :

```json
{
  "signal_id": "sig_...",
  "annotation": {
    "schema_version": "0.4.0",
    "monitoring_target": {},
    "author_role": "consommateur",
    "requires_parent_context": false,
    "is_exploitable": true,
    "non_exploitable_reason": null,
    "business_relevance": "directe",
    "language": {},
    "entities": [],
    "sentiment": {},
    "intents": [],
    "aspects": [],
    "alerts": [],
    "actionability": {}
  },
  "model_version": "lidal-slm-...",
  "compiler_version": "wire-v0.4",
  "validation_status": "valid",
  "inference_ms": 2680
}
```

Le frontend accepte également `analysis.annotation` afin de permettre l’enveloppe
canonique future. L’absence d’annotation déclenche un affichage « analyse
historique » sans casser la page.

## 6. Explorateur V3

L’Explorateur suit une logique maître–détail :

1. rechercher ou filtrer les signaux ;
2. sélectionner un verbatim ;
3. lire le texte original avec ses preuves surlignées ;
4. comprendre sentiment, émotion, intentions, entités et aspects ;
5. inspecter alertes, actionabilité, langue et provenance du modèle ;
6. ouvrir la source originale.

L’utilisateur métier ne voit jamais la syntaxe compacte du modèle. Les libellés
techniques sont traduits en français lisible. Les limites restent explicites :
analyse historique, contexte parent requis, signal inexploitable ou validation en
échec.

## 7. Persistance cible

La migration backend doit ajouter une annotation complète sans supprimer
`enriched_signals` immédiatement. Deux options restent compatibles :

- colonne JSON canonique indexée + colonnes de projection ;
- table `signal_annotations` et tables enfants pour aspects, entités et alertes.

Pour le volume et les requêtes multi-tenant attendus, la cible recommandée est une
approche hybride : annotation JSON immuable, plus projections indexées pour les
filtres et agrégations fréquentes.

## 8. Déploiement progressif

1. double écriture V2 + V0.4 ;
2. contrôle du taux de sortie valide et des exclusions KPI ;
3. activation de l’Explorateur V3 par fonctionnalité ;
4. migration des alertes ;
5. migration des agrégations dashboard ;
6. alimentation du RAG et des recommandations ;
7. retrait de la projection historique après validation terrain.

Les recommandations et alertes ne déclenchent aucune action externe automatique.
La validation humaine reste obligatoire pendant la phase pilote.

## 9. Implémentation livrée

- service d’inférence : `inference/slm_v04_service.py` ;
- client serveur-vers-serveur : `core/analysis/slm_v04_client.py` ;
- compilateur et validation : `core/analysis/slm_v04_compiler.py` ;
- double écriture : `core/normalization/normalizer_pipeline.py` ;
- stockage de l’annotation et de sa provenance dans `enriched_signals` ;
- exposition additive dans les routes de l’Explorateur et les métadonnées FAISS ;
- lecture par le frontend des annotations JSON natives ou sérialisées par SQLite.

Le drapeau `SLM_V04_ENABLED` reste désactivé par défaut. Une sortie invalide ou une
indisponibilité réseau ne bloque pas la collecte : la projection historique est
conservée et l’échec est enregistré pour contrôle.
