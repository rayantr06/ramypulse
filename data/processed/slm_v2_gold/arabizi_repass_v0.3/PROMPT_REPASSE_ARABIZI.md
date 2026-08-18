# Mission — Réannotation ciblée, contrat V0.3

Tu es annotateur sur le corpus RamyPulse. Le dépôt est `G:\ramypulse`.

61 commentaires, 3 lots. Contrat `business_comment_annotation_v0.3.schema.json`.

Cette passe corrige un défaut identifié par une relecture humaine, décrit en
section 3. **Lis cette section avant tout.**

---

## 1. Fichiers INTERDITS

```
data/processed/slm_v2_gold/arabizi_repass_v0.3/_cle_ne_pas_ouvrir.json
data/processed/slm_v2_gold/arabizi_repass_v0.3/output/**
data/processed/slm_v2_gold/campaign_v0.2/**
data/processed/slm_v2_gold/human_validation_v0.3/**
data/processed/slm_v2_gold/business_comments_gold_*.jsonl
data/processed/slm_v2_gold/blind_pass_b/**
data/processed/slm_v2_corpora/**
docs/slm_v2/VALIDATION_HUMAINE_V0.3_2026-07-30.md
docs/slm_v2/gold_v0.1/**
docs/slm_v2/DECISIONS_SCHEMA_V0.3_2026-07-30.md
```

Ces commentaires ont déjà été annotés. Consulter ces annotations rendrait la
correction impossible à mesurer. Pas de `grep` ni `Select-String` sur ces chemins.

## 2. Fichiers AUTORISÉS

| Fichier | Rôle |
|---|---|
| `arabizi_repass_v0.3/input/batch_01.jsonl` … `batch_03.jsonl` | Les commentaires |
| `campaign_v0.2/RUBRIQUE_V0.2.md` | Règles de décision, toujours valables |
| `campaign_v0.2/VOCABULAIRES_FERMES_V0.2.md` | Valeurs autorisées |
| `docs/slm_v2/business_comment_annotation_v0.3.schema.json` | Contrat formel |

Différences V0.3 par rapport à la rubrique : `alert.severity` n'a plus que trois
niveaux — `faible`, `moyenne`, `elevee`. `critique` n'existe plus. L'émotion
`gratitude` est disponible, et `fidelite` est utilisable sous
`confiance_reputation`.

## 3. Le défaut à corriger

Une relecture humaine a montré que les annotateurs précédents se replient sur
`neutre` quand le commentaire est écrit en **arabizi** — l'arabe transcrit en
caractères latins avec des chiffres. Ils y mettent 54 % de `neutre` contre 41 %
sur les autres langues, et 56 % d'items sans aucun aspect.

Trois erreurs relevées par l'humain, toutes codées `neutre` :

- une déclaration d'affection explicite avec cœurs ;
- une insulte directe adressée à une personne ;
- un contenu sexuel explicite visant une personne nommée, sans aucune alerte.

**Ce n'est pas un manque d'attention, c'est un défaut de lecture.** Un texte
arabizi non déchiffré ressemble à du bruit, et le repli le plus sûr est `neutre`.

### La correspondance des chiffres

| Chiffre | Lettre arabe | Exemples |
|---|---|---|
| `3` | ع | `3lik`, `3andi`, `ya3tik`, `3omri` |
| `7` | ح | `7abibi`, `mli7`, `7aja`, `sma7` |
| `9` | ق | `9alb`, `9olek`, `9ahwa`, `wa9t` |
| `2` | ء | `mo2amara` |
| `5` ou `kh` | خ | `5oya`, `khouya` |
| `8` ou `gh` | غ | `8ali`, `ghali` |

Quelques repères fréquents : `bzf` = beaucoup · `nhabkoum` = je vous aime ·
`mli7` = bien · `khayb` = mauvais · `walou` = rien · `makach` / `ma kanch` =
il n'y a pas · `rouh` = va-t'en · `ch7al` = combien · `wach` = quoi ·
`rabi` = Dieu · `nchallah` = si Dieu veut · `saha` = santé, merci.

## 4. Méthode imposée — l'étape de lecture

Pour **chaque** commentaire, dans cet ordre :

1. **Écris d'abord la traduction française** du commentaire, dans le champ
   `lecture_fr`. Fais-le avant de choisir la moindre étiquette.
2. **Annote ensuite à partir de ta traduction**, pas du texte brut.

Ce champ est obligatoire et sera vérifié. Il n'est pas décoratif : c'est
l'étape qui manquait.

Si un passage reste indéchiffrable, écris-le tel quel entre crochets dans la
traduction : `[indéchiffrable : xyz]`. Ne devine pas.

## 5. Règle sur `neutre`

`neutre` reste une réponse légitime — beaucoup de commentaires le sont vraiment.
Mais dès que tu choisis `neutre`, **écris dans `notes` pourquoi**, en une ligne,
en t'appuyant sur ta traduction.

Exemples de `neutre` justifié : question factuelle sans jugement, simple
mention d'un nom, information sans opinion, formule sociale sans objet.

Exemples de ce qui **n'est pas** `neutre` : affection, remerciement chaleureux,
insulte, moquerie, colère, déception, enthousiasme — même exprimés brièvement,
même en argot, même avec des emojis comme seul indice.

**Ne surcorrige pas.** N'invente pas un sentiment pour éviter `neutre` : cela
créerait le défaut inverse. Le jeu contient des commentaires réellement neutres
et la surcorrection sera détectée.

## 6. Insultes et harcèlement

La catégorie `harcelement_discrimination` n'a jamais été utilisée sur tout le
corpus précédent, alors qu'au moins deux commentaires la justifiaient.

Une alerte `harcelement_discrimination` est requise quand un commentaire, sous
scope `organisation` :

- vise une personne nommée ou identifiable par des propos sexuels non sollicités ;
- l'attaque sur son origine, son genre, sa religion ou son apparence ;
- l'insulte de façon répétée ou dégradante.

Sous scope `espace_public`, aucune alerte n'est possible — le schéma l'interdit —
mais le **sentiment doit refléter l'agressivité** et l'item reste exploitable.

Une insulte n'est pas un texte « non exploitable » : elle porte un sentiment
parfaitement lisible.

## 7. Sortie

Pour chaque `input/batch_XX.jsonl`, écris
`arabizi_repass_v0.3/output/batch_XX.out.jsonl`, une ligne JSON par commentaire,
même ordre, mêmes `record_id`, UTF-8 sans BOM.

Format identique au contrat V0.3, avec **deux champs supplémentaires** :

```json
{
  "record_id": "v02_0111",
  "annotator": "REMPLACE_PAR_TON_IDENTIFIANT",
  "lecture_fr": "Que Dieu vous bénisse, qu'est-ce que je vous aime, je vous aime beaucoup ❤️",
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
                "sarcasm": false, "target_entity_ids":[],
                "evidence":["nhabkoum bzf"]},
  "intents": ["avis"],
  "aspects": [],
  "alerts": [],
  "notes": ""
}
```

Cet exemple est **réel** et sa lecture est correcte : il illustre précisément le
type de commentaire qui avait été classé `neutre` à tort.

Rappels : ne produis pas `actionability`, ne calcule aucun offset, les preuves
sont des extraits **exacts** du texte original — pas de ta traduction.

## 8. Interdiction de scripter les étiquettes

Tu dois lire et juger chaque commentaire toi-même. Il est interdit d'écrire un
script qui décide des étiquettes : pas de règles par mots-clés, pas de valeurs
par défaut en masse. Un script ne sert qu'à lire, écrire ou vérifier un fichier.

Une passe précédente a été rejetée pour ce motif.

## 9. Auto-contrôle par lot

- [ ] 21 lignes (19 au dernier lot), `record_id` identiques et dans le même ordre
- [ ] `lecture_fr` rempli et non vide sur **chaque** ligne
- [ ] Chaque `neutre` est justifié dans `notes`
- [ ] Chaque preuve est présente telle quelle dans le texte **original**
- [ ] `severity` ne vaut jamais `critique`
- [ ] Aucun bloc `actionability`, aucun offset
- [ ] Aucun fichier interdit ouvert

## 10. Rapport final

Écris `output/RAPPORT_REPASSE.md` :

- répartition des sentiments, globale et pour les seuls commentaires arabizi ;
- nombre d'alertes par type ;
- commentaires que ta traduction n'a pas permis de déchiffrer ;
- cas où le contrat V0.3 ne t'offrait aucune valeur correcte ;
- confirmation qu'aucun fichier interdit n'a été consulté.

Ne modifie aucun autre fichier. N'exécute aucun script du dépôt. Aucun commit.
