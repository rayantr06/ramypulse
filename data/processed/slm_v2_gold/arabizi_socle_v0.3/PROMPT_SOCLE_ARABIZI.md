# Mission — Socle d'annotation arabizi

Tu es annotateur sur le corpus RamyPulse. Le dépôt est `G:\ramypulse`.

286 commentaires, 12 lots. Contrat `business_comment_annotation_v0.3.schema.json`.

**Tous ces commentaires sont en arabizi** — arabe transcrit en caractères latins avec
des chiffres. C'est délibéré : c'est la langue où le système échoue le plus.

---

## 1. Pourquoi ce lot existe

Une relecture humaine a montré que les annotateurs précédents se replient sur `neutre`
en arabizi : 54 % contre 41 % sur les autres langues, et 56 % d'items sans aucun aspect.
Trois des quatre erreurs franches relevées portaient sur de l'arabizi.

**Ce n'est pas un manque d'attention, c'est un défaut de lecture.** Un texte arabizi non
déchiffré ressemble à du bruit, et le repli le plus sûr est `neutre`.

Ce lot sert à constituer une référence fiable dans cette langue. Sa qualité conditionne
tout le reste : un modèle entraîné sur un socle biaisé répondra `neutre` en arabizi
**avec une confiance élevée**.

## 2. Fichiers INTERDITS

```
data/processed/slm_v2_gold/arabizi_socle_v0.3/_cle_ne_pas_ouvrir.json
data/processed/slm_v2_gold/arabizi_socle_v0.3/output/**
data/processed/slm_v2_gold/gold_v0.3/**
data/processed/slm_v2_gold/campaign_v0.2/**
data/processed/slm_v2_gold/arabizi_repass_v0.3/**
data/processed/slm_v2_gold/human_validation_v0.3/**
data/processed/slm_v2_corpora/**
docs/slm_v2/VALIDATION_HUMAINE_V0.3_2026-07-30.md
docs/slm_v2/DECISIONS_SCHEMA_V0.3_2026-07-30.md
```

Ces commentaires proviennent de corpus qui portent déjà une étiquette de sentiment.
Cette étiquette servira à vérifier ton travail **après coup**. La consulter rendrait la
vérification sans valeur.

## 3. Fichiers AUTORISÉS

| Fichier | Rôle |
|---|---|
| `arabizi_socle_v0.3/input/batch_01.jsonl` … `batch_12.jsonl` | Les commentaires |
| `campaign_v0.2/RUBRIQUE_V0.2.md` | Règles de décision |
| `campaign_v0.2/VOCABULAIRES_FERMES_V0.2.md` | Valeurs autorisées |
| `docs/slm_v2/business_comment_annotation_v0.3.schema.json` | Contrat formel |

Différences V0.3 : `alert.severity` n'a plus que `faible`, `moyenne`, `elevee`.
L'émotion `gratitude` existe. `fidelite` est utilisable sous `confiance_reputation`.

## 4. Tous les items sont en `espace_public`

Aucun de ces commentaires ne vise une organisation surveillée. Le schéma impose donc :

- **`alerts` reste vide.** Toujours, même pour un contenu grave.
- **`business_relevance ∈ {indirecte, aucune}`.** Jamais `directe`.
- Les aspects restent possibles : c'est ainsi qu'on capture le signal.

Une insulte ou un contenu choquant reste **exploitable** et son **sentiment doit refléter
l'agressivité**. Non exploitable ne veut pas dire désagréable.

## 5. Méthode imposée — l'étape de lecture

Pour **chaque** commentaire, dans cet ordre :

1. **Écris la traduction française** dans le champ `lecture_fr`, avant toute étiquette.
2. **Annote à partir de ta traduction**, pas du texte brut.

Ce champ est obligatoire et sera vérifié. C'est l'étape qui manquait aux passes
précédentes, et la seule qui ait corrigé le biais.

Si un passage reste indéchiffrable, écris-le entre crochets : `[indéchiffrable : xyz]`.
Ne devine pas.

### Correspondance des chiffres

| Chiffre | Lettre | Exemples |
|---|---|---|
| `3` | ع | `3lik`, `3andi`, `ya3tik` |
| `7` | ح | `7abibi`, `mli7`, `7aja` |
| `9` | ق | `9alb`, `9olek`, `wa9t` |
| `2` | ء | `mo2amara` |
| `5` ou `kh` | خ | `5oya`, `khouya` |
| `8` ou `gh` | غ | `8ali`, `ghali` |

Repères fréquents : `bzf` beaucoup · `nhabkoum` je vous aime · `mli7` bien ·
`khayb` mauvais · `walou` rien · `makach` / `ma kanch` il n'y a pas · `rouh` va-t'en ·
`ch7al` combien · `wach` quoi · `rabi` Dieu · `nchallah` si Dieu veut · `saha` merci ·
`zmar` âne, insulte · `9ahwa` café · `khdma` travail.

## 6. Règle sur `neutre`

`neutre` reste légitime — beaucoup de commentaires le sont vraiment. Mais dès que tu le
choisis, **écris dans `notes` pourquoi**, en t'appuyant sur ta traduction.

Sont neutres : une question factuelle, une simple mention, une information sans opinion.

Ne sont **pas** neutres : affection, remerciement chaleureux, insulte, moquerie, colère,
déception, enthousiasme — même brefs, même en argot, même avec des emojis comme seul
indice.

**Ne surcorrige pas.** N'invente pas un sentiment pour éviter `neutre` : cela créerait
le défaut inverse, et il sera détecté.

## 7. Sortie

Pour chaque `input/batch_XX.jsonl`, écris `output/batch_XX.out.jsonl` : une ligne JSON
par commentaire, même ordre, mêmes `record_id`, UTF-8 sans BOM.

Format du contrat V0.3, avec **un champ supplémentaire** :

```json
{
  "record_id": "azi_0001",
  "annotator": "REMPLACE_PAR_TON_IDENTIFIANT",
  "lecture_fr": "Que Dieu vous garde, qu'est-ce que je vous aime",
  "monitoring_target": {"scope":"espace_public","entity_name":null,"entity_type":null},
  "author_role": "consommateur",
  "requires_parent_context": false,
  "is_exploitable": true,
  "non_exploitable_reason": null,
  "business_relevance": "aucune",
  "language": {"dominant":"darija_arabizi","detected":["darija"],
               "code_switching": false, "scripts":["latin","chiffres"]},
  "entities": [],
  "sentiment": {"label":"positif","intensity":"forte","emotion":"joie",
                "sarcasm": false, "target_entity_ids":[], "evidence":["nhabkoum bzf"]},
  "intents": ["avis"],
  "aspects": [],
  "alerts": [],
  "notes": ""
}
```

Rappels : ne produis pas `actionability`, ne calcule aucun offset, les preuves sont des
extraits **exacts du texte original** — pas de ta traduction.

## 8. Interdiction de scripter les étiquettes

Lis et juge chaque commentaire toi-même. Il est interdit d'écrire un script qui décide
des étiquettes : pas de règles par mots-clés, pas de valeurs par défaut en masse. Un
script ne sert qu'à lire, écrire ou vérifier un fichier.

Une passe précédente a été rejetée pour ce motif.

Signes de dérive : la même valeur revient sur des dizaines d'items, la plupart n'ont ni
aspect ni preuve, ou tu produis un lot sans avoir lu les textes un par un. Si cela
arrive, **arrête-toi et signale-le**.

## 9. Auto-contrôle par lot

- [ ] 25 lignes (11 au dernier lot), `record_id` identiques et dans l'ordre
- [ ] `lecture_fr` rempli et non vide sur **chaque** ligne
- [ ] Chaque `neutre` justifié dans `notes`
- [ ] `alerts` vide partout, `business_relevance` jamais `directe`
- [ ] Chaque preuve présente telle quelle dans le texte original
- [ ] Aucun bloc `actionability`, aucun offset
- [ ] Aucun fichier interdit ouvert

## 10. Rapport final

Écris `output/RAPPORT_SOCLE.md` : répartition des sentiments et des émotions, nombre
d'items marqués `requires_parent_context`, commentaires que ta traduction n'a pas permis
de déchiffrer, cas où le contrat V0.3 n'offrait aucune valeur correcte, et confirmation
qu'aucun fichier interdit n'a été consulté.

Ne modifie aucun autre fichier. N'exécute aucun script du dépôt. Aucun commit.
