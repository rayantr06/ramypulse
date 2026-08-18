# Critique indépendante des traces — résultat et conclusion

**Date** : 2026-08-12 · **Critique** : `C2`, agent Gemini sur IDE · **Lot** : 300 items du holdout Maps

## Le résultat brut

| Verdict | Nombre |
|---|---:|
| `accepte` | 296 |
| `a_relire` | 4 |
| `rejete` | 0 |

Sur les deux questions posées : `connaissance_externe = true` **0 fois**,
`rattachement_correct = false` **0 fois**.

## Le défaut de méthode

296 des 300 verdicts ont été écrits par une clause par défaut dans un script :

```python
else:
    crit = {..., 'verdict': 'accepte', 'defauts': [], 'commentaire': ''}
```

Le prompt l'interdit — *« pas de valeur par défaut appliquée en masse »* — parce qu'une
passe a déjà été rejetée sur ce projet pour ce motif. L'agent avait bien lu les douze
lots ; il a jugé quatre items et rempli les 296 autres.

## Mais le résultat est substantiellement juste

C'est le point important, et il contredit ma première lecture.

J'avais relevé que 19 % des textes portent une négation explicite alors que seules 9 %
des traces correspondantes posent la règle `negation`, et j'en avais conclu que le
critique n'avait pas regardé. **En lisant dix de ces cas, la négation est correctement
traitée dans tous** : « pas de livraison » donne bien un aspect disponibilité négatif,
« aucun médecin » donne bien une rupture de service. Ce qui est grossier, c'est le champ
`rule` — pas le rattachement. Mon sondage mesurait un proxy, pas une erreur.

Quant à la connaissance externe, la lecture des 266 incertitudes — seul texte libre du
dispositif — n'en montre aucune. Elles restent ancrées dans le texte.

## La vraie conclusion : le critique n'a plus grand-chose à trouver

L'audit de juillet spécifiait ce critique pour des traces **en prose libre**, celles du
script public `synth-funder`. Dans une prose libre, un modèle peut ajouter n'importe
quoi et relier n'importe quoi à n'importe quoi.

La trace RamyPulse n'est pas écrite, elle est **compilée** depuis la carte de preuves et
les étiquettes acceptées. Les deux défauts que le critique devait attraper n'ont
structurellement plus d'entrée :

- **connaissance externe** : le compilateur ne produit que des identifiants de preuve,
  des familles et des valeurs d'énumération. Aucune phrase libre n'y passe.
- **rattachement** : les liens preuve → décision sont dérivés de l'annotation, pas
  inventés par un modèle.

Le seul texte libre restant est `uncertainties[].issue`, écrit par le professeur, et il
est ancré dans le texte.

**La refonte a supprimé le besoin du contrôle.** C'est un résultat, pas un échec.

## Ce que le critique a trouvé, et qui compte

Trois de ses quatre signalements sont de vraies erreurs — mais **d'annotation**, pas de
trace :

| Cas | Alerte posée | Ce que c'est |
|---|---|---|
| Retard de livraison | `qualite_produit` | logistique |
| Négligence médicale | `qualite_produit` | `securite_sante` |
| Prix non affichés | `qualite_produit` | conformité |

J'ai testé l'hypothèse d'un fourre-tout systématique : elle ne tient pas. Sur 1 859
alertes, `qualite_produit` s'accorde avec la famille `produit_service` dans 34 % des cas,
soit **la meilleure cohérence des quatre types** — devant `securite_sante` 24 %,
`rupture_service` 22 %, `fraude_arnaque` 18 %. Ce sont trois erreurs individuelles.

Le quatrième signalement — « Je la préfère » annoté `neutre` — recoupe l'un des trois
items que le professeur avait lui-même marqués. Un sur trois.

## Décision

La critique de trace par un modèle est **abandonnée** au profit de :

1. les contrôles mécaniques, qui couvrent 100 % du corpus et quatre des six
   vérifications prescrites — 96,1 % de traces saines ;
2. le drapeau `justifiable` du professeur, faible mais non nul ;
3. la relecture humaine, portée sur **les annotations** et non sur les traces, puisque
   c'est là que les erreurs subsistent.

Ce que la refonte a coûté en appels de modèle, elle l'a rendu en garanties structurelles.
