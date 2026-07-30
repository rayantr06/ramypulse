# Mission — Annotation campagne V0.2

Tu es annotateur sur le corpus RamyPulse SLM V2. Le dépôt est `G:\ramypulse`.

Le contrat d'annotation a été révisé après une mesure d'accord entre deux annotateurs
indépendants. **Tu travailles sur la V0.2, pas sur la V0.1.** Plusieurs règles ont changé.

Cette campagne mesure si le nouveau contrat produit des annotations reproductibles.
Ta valeur vient de ton jugement honnête, pas de ta conformité à un autre annotateur.

---

## 1. Fichiers INTERDITS

```
data/processed/slm_v2_gold/business_comments_gold_candidate_v0.1.jsonl
data/processed/slm_v2_gold/business_comments_gold_dev_v0.1.jsonl
data/processed/slm_v2_gold/business_comments_gold_test_v0.1.jsonl
data/processed/slm_v2_gold/blind_pass_b/**
data/processed/slm_v2_gold/campaign_v0.2/sample_full.jsonl
data/processed/slm_v2_gold/campaign_v0.2/output*/**   <- TOUT dossier de sortie

data/processed/slm_v2_corpora/v0.1/normalized/**
data/processed/slm_v2_pilot/**
docs/slm_v2/gold_v0.1/**
docs/slm_v2/pilot_reports/**
docs/slm_v2/DECISIONS_SCHEMA_V0.2_2026-07-30.md
docs/slm_v2/GUIDE_ANNOTATION_BUSINESS_V0.1.md
data/processed/master_seed_7k.jsonl
```

Ces fichiers contiennent des annotations existantes ou les arbitrages ayant servi à
construire la V0.2. Les consulter détruirait la mesure. N'utilise ni `grep`, ni `rg`,
ni `Select-String` sur ces chemins. Si un outil t'en renvoie du contenu par accident,
**arrête-toi et signale-le**.

`sample_full.jsonl` est interdit parce qu'il contient les étiquettes de strate
révélant quels commentaires ont été sélectionnés comme candidats-alertes.

## 2. Fichiers AUTORISÉS

| Fichier | Rôle |
|---|---|
| `data/processed/slm_v2_gold/campaign_v0.2/input/batch_01.jsonl` … `batch_13.jsonl` | Les commentaires |
| `data/processed/slm_v2_gold/campaign_v0.2/RUBRIQUE_V0.2.md` | Les règles de décision |
| `data/processed/slm_v2_gold/campaign_v0.2/VOCABULAIRES_FERMES_V0.2.md` | Valeurs autorisées |
| `docs/slm_v2/business_comment_annotation_v0.2.schema.json` | Le contrat formel |

Lis la rubrique et les vocabulaires **en entier** avant le premier commentaire.

## 3. Entrée

```json
{"record_id":"v02_0001","text":"…",
 "monitoring_target":{"scope":"organisation","entity_name":"Ramy","entity_type":"marque"},
 "context":{"source":"…","topic":"…","brand":"Ramy"}}
```

`monitoring_target` est **fourni**. Ne le décide pas, ne le modifie pas, recopie-le tel
quel dans ta sortie. Il détermine ce que tu as le droit d'annoter — relis la section 0
de la rubrique.

## 4. Sortie

Le dossier de sortie t'est indiqué au lancement (`output` ou `output_c`). Il est
désigné ci-dessous par `<SORTIE>`. **N'ouvre jamais un autre dossier de sortie** :
une seconde passe qui lit la première ne mesure plus rien.

Pour chaque `input/batch_XX.jsonl`, écris
`data/processed/slm_v2_gold/campaign_v0.2/<SORTIE>/batch_XX.out.jsonl` :
une ligne JSON par commentaire, même ordre, mêmes `record_id`, UTF-8 sans BOM.

```json
{
  "record_id": "v02_0001",
  "annotator": "REMPLACE_PAR_TON_IDENTIFIANT",
  "monitoring_target": {"scope":"organisation","entity_name":"Ramy","entity_type":"marque"},
  "author_role": "consommateur",
  "requires_parent_context": false,
  "is_exploitable": true,
  "non_exploitable_reason": null,
  "business_relevance": "directe",
  "language": {"dominant":"darija_arabizi","detected":["darija","francais"],
               "code_switching": true, "scripts":["latin"]},
  "entities": [{"id":"ent_1","type":"marque","name":"Ramy","mention":null,
                "source":"contexte"}],
  "sentiment": {"label":"mixte","intensity":"moyenne","emotion":"deception",
                "sarcasm": false, "target_entity_ids":["ent_1"],
                "evidence":["produit bon","cher"]},
  "intents": ["avis","plainte"],
  "aspects": [
    {"family":"produit_service","attribute":"qualite_generale","target_entity_id":"ent_1",
     "sentiment":"positif","intensity":"moyenne","implicit":false,"evidence":["produit bon"]},
    {"family":"prix_valeur","target_entity_id":"ent_1",
     "sentiment":"negatif","intensity":"moyenne","implicit":false,"evidence":["cher"]}
  ],
  "alerts": [],
  "notes": "attribut omis sur prix_valeur : hesitation entre prix et abordabilite"
}
```

Exemple **synthétique**, absent du corpus. Il illustre la forme, y compris un aspect
sans `attribute` (autorisé en V0.2) et une absence d'alerte, qui est le cas normal.

Règles de sortie :

- **Ne produis pas `actionability`.** Le pipeline le calcule.
- **Ne calcule aucun offset.** Les preuves sont des chaînes copiées caractère pour
  caractère depuis `text`.
- Identifiants d'entité `ent_1`, `ent_2`… référencés uniquement dans `target_entity_ids`
  et `target_entity_id`.
- `notes` obligatoire, éventuellement vide. **Remplis-la dès que tu hésites** : c'est
  l'information la plus utile de la campagne.

## 5. Contraintes que le schéma refusera

1. `scope = espace_public` avec une alerte → rejet. Alertes réservées à `organisation`.
2. `scope = espace_public` avec `business_relevance = directe` → rejet.
3. Un aspect de sentiment `neutre` → rejet. Les aspects neutres n'existent plus.
4. `author_role = marque` avec un sentiment non neutre → rejet.
5. `requires_parent_context = true` avec un sentiment non neutre ou une alerte → rejet.
6. Plus de 3 intentions, 8 aspects, 5 alertes, 10 entités → rejet.
7. Une valeur absente de `VOCABULAIRES_FERMES_V0.2.md` → rejet.

## 6. Méthode — lis cette section avant de commencer

**Tu dois lire et juger chaque commentaire toi-même.**

Il est **interdit** d'écrire un script qui décide des étiquettes : pas de règles par
mots-clés, pas de valeurs par défaut appliquées en masse, pas de génération
programmatique des annotations. Un tel script produit un remplissage par gabarit,
pas une annotation, et rend la campagne inutilisable.

Un script est autorisé uniquement pour lire un fichier, écrire un fichier ou vérifier
un format. Jamais pour choisir un `sentiment`, un `aspect`, une `alerte` ou une langue.

Signes que tu es en train de dériver : la même valeur revient sur des dizaines d'items
d'affilée, la plupart de tes items n'ont ni aspect ni preuve, ou tu produis un lot
entier sans avoir lu les textes un par un. Si cela arrive, **arrête-toi et signale-le**.

13 lots de 25. Traite **un lot à la fois**, dans l'ordre. Pour chacun :

1. Lis les 25 commentaires.
2. Annote un par un, dans l'ordre de la rubrique : `monitoring_target` →
   `author_role` → `requires_parent_context` → exploitabilité → pertinence → langue →
   entités → sentiment → intentions → aspects → alertes → preuves.
3. Écris le fichier de sortie complet du lot.
4. Vérifie, puis passe au suivant.

Ne fusionne pas les lots : la qualité d'annotation chute sur les séries longues.

## 7. Auto-contrôle par lot

- [ ] 25 lignes, `record_id` identiques et dans le même ordre que l'entrée
- [ ] `monitoring_target` recopié à l'identique
- [ ] Chaque ligne est un JSON valide sur une seule ligne
- [ ] Aucune des 7 contraintes de la section 5 n'est violée
- [ ] Chaque preuve est présente telle quelle dans le `text` du même `record_id`
- [ ] Aucun bloc `actionability`, aucun offset
- [ ] Aucun fichier interdit ouvert
- [ ] Aucune étiquette produite par script : chaque commentaire a été lu et jugé
- [ ] Le lot contient une réelle diversité de sentiments, d'aspects et de preuves

## 8. Rapport final

Écris `<SORTIE>/RAPPORT_ANNOTATEUR.md` :

- volumétrie et répartitions (sentiment, familles, alertes, langues, `author_role`) ;
- nombre d'items marqués `requires_parent_context` ;
- `record_id` où tu as réellement hésité, avec l'alternative envisagée ;
- **les cas où la V0.2 ne t'a proposé aucune valeur correcte** — le résultat le plus
  utile de la campagne ;
- confirmation explicite qu'aucun fichier interdit n'a été consulté.

Ne modifie aucun autre fichier. N'exécute aucun script. Ne fais aucun commit.
