# Mission — Annotateur B, passe indépendante en aveugle

Tu es **annotateur B** sur le corpus RamyPulse SLM V2. Le dépôt est `G:\ramypulse`.

Un annotateur A a déjà annoté ces 100 commentaires. **Tu ne dois jamais voir son
travail.** L'objectif est de mesurer l'accord entre deux jugements réellement
indépendants. Si tu consultes les annotations de A, la mesure est détruite et la
mission a échoué — même si tes réponses sont bonnes.

Ta valeur ici vient de ton **désaccord honnête**, pas de ta conformité.

---

## 1. Fichiers INTERDITS — ne les ouvre sous aucun prétexte

```
data/processed/slm_v2_gold/business_comments_gold_candidate_v0.1.jsonl
data/processed/slm_v2_gold/business_comments_gold_dev_v0.1.jsonl
data/processed/slm_v2_gold/business_comments_gold_test_v0.1.jsonl
data/processed/slm_v2_corpora/v0.1/normalized/ramypulse_business_gold_candidate.jsonl
data/processed/slm_v2_pilot/**
docs/slm_v2/gold_v0.1/review_decisions.jsonl
docs/slm_v2/gold_v0.1/review_audit.jsonl
docs/slm_v2/gold_v0.1/REVIEW_RUBRIC.md
docs/slm_v2/gold_v0.1/baselines/**
docs/slm_v2/pilot_reports/**
docs/slm_v2/GUIDE_ANNOTATION_BUSINESS_V0.1.md
data/processed/master_seed_7k.jsonl
```

N'utilise aucun `grep`, `rg`, `Select-String`, `cat` ni recherche plein texte sur
`data/processed/slm_v2_gold/` ou `docs/slm_v2/gold_v0.1/`, à l'exception des deux
répertoires autorisés ci-dessous. Si un outil te renvoie accidentellement du contenu
de ces fichiers, **arrête-toi et signale-le** au lieu de continuer.

## 2. Fichiers AUTORISÉS — les seuls dont tu as besoin

| Fichier | Rôle |
|---|---|
| `data/processed/slm_v2_gold/blind_pass_b/input/batch_01.jsonl` … `batch_05.jsonl` | Les commentaires à annoter |
| `data/processed/slm_v2_gold/blind_pass_b/RUBRIQUE_PASSE_B.md` | Les règles de décision |
| `data/processed/slm_v2_gold/blind_pass_b/VOCABULAIRES_FERMES.md` | Toutes les valeurs autorisées |
| `docs/slm_v2/business_comment_annotation_v0.1.schema.json` | Le contrat JSON formel |

Lis d'abord la rubrique et les vocabulaires **en entier**, avant le premier commentaire.

## 3. Entrée

Chaque ligne d'un batch est un objet :

```json
{"record_id":"...","text":"...","context":{"source":"...","topic":"...","brand":"..."}}
```

`context` décrit d'où vient le commentaire. `brand` peut identifier la cible, mais ne
justifie **jamais** à lui seul un produit, un aspect ou un sentiment.

## 4. Sortie

Pour chaque batch `input/batch_XX.jsonl`, écris
`data/processed/slm_v2_gold/blind_pass_b/output/batch_XX.out.jsonl` :
**une ligne JSON par commentaire, même ordre, même `record_id`, encodage UTF-8, pas de BOM.**

Format exact d'une ligne :

```json
{
  "record_id": "…",
  "annotator": "B",
  "is_exploitable": true,
  "non_exploitable_reason": null,
  "business_relevance": "directe",
  "language": {
    "dominant": "darija_arabizi",
    "detected": ["darija", "francais"],
    "code_switching": true,
    "scripts": ["latin"]
  },
  "entities": [],
  "sentiment": {
    "label": "mixte",
    "intensity": "moyenne",
    "emotion": "deception",
    "sarcasm": false,
    "target_entity_ids": [],
    "evidence": ["produit bon", "cher"]
  },
  "intents": ["avis", "plainte"],
  "aspects": [
    {"family":"produit_service","attribute":"qualite_generale","target_entity_id":null,
     "sentiment":"positif","intensity":"moyenne","implicit":false,"evidence":["produit bon"]},
    {"family":"prix_valeur","attribute":"prix","target_entity_id":null,
     "sentiment":"negatif","intensity":"moyenne","implicit":false,"evidence":["cher"]},
    {"family":"disponibilite_acces","attribute":"stock","target_entity_id":null,
     "sentiment":"negatif","intensity":"moyenne","implicit":false,
     "evidence":["ma nlqawhach f les magasins"]}
  ],
  "alerts": [],
  "actionability": {"actionable": true, "queue": "pricing", "priority": "moyenne"},
  "notes": "hésitation entre prix_valeur/prix et prix_valeur/abordabilite"
}
```

Cet exemple est **synthétique**, il ne provient pas du corpus. Il illustre uniquement
la forme. Remarque qu'il ne contient **aucune alerte** : c'est le cas normal.

Règles de sortie :

- **Ne calcule aucun offset `start`/`end`.** Les preuves sont uniquement des chaînes
  copiées **caractère pour caractère** depuis `text`. Les offsets seront calculés
  ensuite par le pipeline. Une preuve retouchée, normalisée ou reformulée sera rejetée.
- Si tu crées des entités, donne-leur des identifiants `ent_1`, `ent_2`… et n'utilise
  que ces identifiants dans `target_entity_ids` et `target_entity_id`.
- `notes` est **obligatoire mais peut être une chaîne vide**. Remplis-la dès que tu
  hésites entre deux valeurs : c'est exactement l'information qui servira à corriger
  le schéma. Une hésitation notée vaut mieux qu'une décision propre en apparence.

## 5. Règles absolues

1. **Aucune valeur inventée.** Toute valeur doit figurer dans `VOCABULAIRES_FERMES.md`.
   Un `attribute` doit appartenir à la `family` choisie.
2. **Maximum** : 3 intentions, 8 aspects, 5 alertes, 10 entités.
3. Si `is_exploitable` est `false` : `aspects = []`, `alerts = []`,
   `business_relevance = "aucune"`, et `non_exploitable_reason` est renseigné.
   Si `is_exploitable` est `true` : `non_exploitable_reason = null`.
4. **Les alertes sont rares.** Un mécontentement ordinaire n'est pas une alerte.
   En cas de doute, pas d'alerte.
5. Les preuves sont des extraits **exacts et contigus** du `text`, les plus courts
   possible.
6. N'essaie pas de deviner ce qu'un autre annotateur aurait répondu, et ne cherche pas
   à être « cohérent » avec quoi que ce soit d'extérieur à ce commentaire.

## 6. Méthode de travail

Traite **un batch à la fois**, dans l'ordre `batch_01` → `batch_05`. Pour chaque batch :

1. Lis les 20 commentaires.
2. Annote-les un par un, en suivant l'ordre de décision de la rubrique
   (exploitabilité → pertinence → langue → entités → sentiment → intentions → aspects
   → alertes → actionnabilité → preuves).
3. Écris le fichier de sortie complet du batch.
4. Vérifie, puis passe au batch suivant.

Ne fusionne pas les cinq batches en une seule passe : la qualité d'annotation chute
sur les séries longues.

## 7. Auto-contrôle avant de terminer chaque batch

Vérifie et corrige avant de passer à la suite :

- [ ] 20 lignes, `record_id` identiques et dans le même ordre que l'entrée
- [ ] Chaque ligne est un JSON valide sur une seule ligne
- [ ] Toutes les valeurs figurent dans `VOCABULAIRES_FERMES.md`
- [ ] Chaque couple `family`/`attribute` est autorisé
- [ ] Chaque preuve est présente telle quelle dans le `text` du même `record_id`
      (test : `evidence in text` doit être vrai, sans aucune modification)
- [ ] Les non-exploitables n'ont ni aspect ni alerte
- [ ] Chaque `target_entity_id` référence une entité déclarée sur la même ligne
- [ ] Aucun fichier de la liste interdite n'a été ouvert

## 8. Rapport final

Quand les cinq batches sont écrits, produis
`data/processed/slm_v2_gold/blind_pass_b/output/RAPPORT_ANNOTATEUR_B.md` avec :

- le nombre de commentaires annotés ;
- la répartition des sentiments, des familles d'aspect, des alertes et des langues ;
- la liste des `record_id` où tu as vraiment hésité, avec l'alternative envisagée ;
- les cas où le schéma V0.1 ne t'a proposé aucune valeur correcte — c'est le
  résultat le plus utile de toute la mission ;
- la confirmation explicite qu'aucun fichier interdit n'a été consulté.

Ne modifie **aucun autre fichier** du dépôt. N'exécute aucun script du dossier
`scripts/`. Ne fais aucun commit.
