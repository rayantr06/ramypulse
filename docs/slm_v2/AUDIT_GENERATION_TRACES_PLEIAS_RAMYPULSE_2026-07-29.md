# RamyPulse SLM V2 — génération et schéma des traces de décision

Date : 29 juillet 2026  
Objet : analyser la génération de traces PleIAs sur la tâche publique la plus
proche de RamyPulse et définir une adaptation vérifiable

## 1. Conclusion

Le pipeline `synth-funder` fournit une réponse très utile, mais il faut
distinguer son **principe** de son **implémentation publique**.

Principe à retenir :

> produire d'abord une annotation cible, puis demander à un professeur de
> reconstruire le chemin de décision qui relie le texte à cette annotation.

Ce n'est donc pas un raisonnement indépendant généré avant de connaître la
réponse. C'est un **back-reasoning conditionné par le texte et par le JSON
final**.

L'implémentation publique `synth-funder` utilise une trace libre en prose. Elle
n'a pas de schéma JSON propre, pas de références obligatoires vers des preuves,
et le code public ne valide pas la cohérence de la trace avec l'annotation.

Le système général SYNTH/Baguettotron possède cependant une **grammaire
sténographique de raisonnement** avec des marqueurs logiques, de confiance, de
vérification et d'entropie simulée. Cette couche, distincte du script public
`synth-funder`, doit également être prise en compte.

Pour RamyPulse, la décision est de conserver le back-reasoning, mais de le
représenter d'abord sous forme canonique structurée, contrôlée par des
validateurs et un critique. Une vue compacte est ensuite compilée pour
l'entraînement du SLM.

Schéma canonique :
`docs/slm_v2/business_decision_trace_v0.1.schema.json`.

## 2. Comment PleIAs génère réellement les données

Sources principales :

- [`generation/annotate.py`](https://github.com/Pleias/synth-funder/blob/main/generation/annotate.py) ;
- [`generation/generate_traces.py`](https://github.com/Pleias/synth-funder/blob/main/generation/generate_traces.py) ;
- [`data/test_set_200.jsonl`](https://github.com/Pleias/synth-funder/blob/main/data/test_set_200.jsonl) ;
- [`data/train.json`](https://github.com/Pleias/synth-funder/blob/main/data/train.json) ;
- [`training/full_sft.py`](https://github.com/Pleias/synth-funder/blob/main/training/full_sft.py).

### Étape A — annotation

Le texte brut est envoyé à Gemini 3 Flash Preview avec :

- une ontologie longue dans le prompt système ;
- des valeurs fermées pour les catégories ;
- des règles de désambiguïsation ;
- une température de `0.2` ;
- `response_mime_type="application/json"`.

Le modèle produit le JSON d'annotation. Le script vérifie que la réponse est du
JSON décodable, mais le code public n'utilise pas de `response_schema` strict et
ne montre pas de validation sémantique complète.

### Étape B — back-reasoning

Un second appel reçoit simultanément :

1. le texte brut ;
2. le JSON d'annotation déjà obtenu.

Le professeur doit rédiger une « découverte progressive » en cinq étapes :

1. premier scan : nature du texte, langue, qualité et troncature ;
2. identification des entités dans l'ordre du texte ;
3. relations et désambiguïsations entre entités ;
4. analyse des identifiants ;
5. évaluation du style et du type de contenu.

La génération utilise :

- Gemini 3 Flash Preview ;
- une température de `0.7` ;
- une sortie `text/plain` ;
- une prose libre, sans listes ;
- une longueur demandée de 100–200, 200–400 ou 400–600 mots.

### Étape C — complexité

La complexité publiée est calculée depuis l'annotation :

- `0` : texte non pertinent ou au plus une entité ;
- `1` : au plus quatre entités, trois identifiants et aucune troncature ;
- `2` : tous les autres cas.

Le score n'est pas injecté explicitement dans le prompt de chaque exemple. Le
modèle déduit approximativement la complexité en voyant le JSON. Le script
affiche ensuite la répartition et stocke le score.

### Étape D — entraînement

Les données intermédiaires contiennent :

```text
text
reasoning
annotation
complexity
publication_id
```

Le fichier d'entraînement du professeur regroupe ensuite dans une seule chaîne :

```text
### Acknowledgement Text ###
[texte]

### Reasoning ###
[trace]

### Annotation ###
[JSON]
```

`full_sft.py` entraîne causalement sur le champ `text` complet et active le
packing. Pour le modèle 600M, le README indique un corpus Qwen Chat contenant
`<think>` puis le JSON, mais ce corpus d'environ 1,6 million d'exemples est
privé.

## 3. Ce que montrent les 200 traces publiques

Mesure reproduite sur le fichier public de test :

| Complexité | N | Moyenne | P50 | P95 | Bande demandée respectée |
|---|---:|---:|---:|---:|---:|
| simple | 36 | 246,4 mots | 224 | 342 | 16,7 % |
| moyenne | 58 | 261,9 mots | 258 | 324 | 94,8 % |
| complexe | 106 | 329,7 mots | 322 | 409 | 9,4 % |

Les traces couvrent bien les cinq familles de décision, mais leur longueur
converge vers quelques centaines de mots au lieu de suivre précisément les
bandes. Dans le code public :

- toute trace non vide est acceptée ;
- aucun plafond n'est imposé ;
- aucune référence obligatoire ne relie une décision à un passage du texte ;
- aucune règle ne vérifie que la trace n'ajoute pas une entité ou un fait ;
- aucun critique indépendant n'est appelé ;
- « stratifier » signifie ici afficher les groupes après un échantillonnage
  aléatoire, pas équilibrer effectivement l'échantillon.

Des traces publiques contiennent parfois des développements plausibles mais non
nécessaires au JSON final. Pour RamyPulse, ce bruit serait coûteux en tokens et
pourrait apprendre au SLM à inventer des explications.

## 4. Grammaire de raisonnement SYNTH/Baguettotron

Sources :

- [carte modèle Baguettotron](https://huggingface.co/PleIAs/Baguettotron) ;
- [configuration réelle du tokenizer](https://huggingface.co/PleIAs/Baguettotron/blob/main/tokenizer_config.json) ;
- [dataset SYNTH](https://huggingface.co/datasets/PleIAs/SYNTH).

### 4.1 Marqueurs documentés

| Famille | Marqueur | Sens |
|---|---|---|
| logique | `→` | dérivation ou implication |
| logique | `↺` | retour, révision ou nouvelle tentative |
| logique | `?` | question ou incertitude à résoudre |
| logique | `!` / `※` | découverte ou point décisif |
| logique | `≈` | approximation ou hypothèse intermédiaire |
| logique | `∴` | conclusion stable |
| confiance | `●` | forte |
| confiance | `◐` | moyenne ou partielle |
| confiance | `○` | faible |
| risque | `⚠` | biais, prémisse fragile ou décalage de domaine |
| spéculation | `?maybe?` | branche provisoire |
| vérification | `☐` | hypothèse non vérifiée |
| vérification | `☑` | vérification intermédiaire |
| vérification | `✓` | confirmé |
| exploration | `⟨H≈0.1⟩` à `⟨H≈1.8⟩` | entropie simulée |

PleIAs utilise aussi des arbres `├─` et `└─` pour décomposer un problème.

### 4.2 Marqueurs réellement réservés dans le tokenizer

La configuration Baguettotron réserve explicitement :

```text
<think> → ↺ ※ ?maybe? ● ◐ ○ ⚠ ☐ ☑ ✓
⟨H≈0.1⟩ ... ⟨H≈1.8⟩
```

Elle réserve également les tokens de sources `source_1` à `source_10` et les
balises de référence. `?`, `!`, `≈` et `∴` sont documentés dans la grammaire,
mais ne figurent pas dans la liste `additional_special_tokens`.

### 4.3 Usage observé dans SYNTH

Mesure exploratoire sur 1 000 lignes du dataset public, échantillonnées à dix
positions entre 0 et 900 000 :

| Marqueur | Traces qui l'utilisent | Occurrences |
|---|---:|---:|
| `→` | 91,7 % | 5 713 |
| `∴` | 75,3 % | 953 |
| `●` | 69,7 % | 2 987 |
| `◐` | 54,4 % | 1 076 |
| `≈` | 44,3 % | 875 |
| `※` | 44,1 % | 512 |
| entropie simulée | 35,6 % | 492 |
| `○` | 34,3 % | 699 |
| `⚠` | 30,7 % | 419 |
| `✓` | 20,5 % | 534 |
| `☐` / `☑` | environ 5 % chacun | 292 au total |
| `↺` | 0,3 % | 3 |

Cette fréquence, combinée aux quelque 200 milliards de tokens d'entraînement de
Baguettotron, explique pourquoi le modèle peut apprendre une sémantique stable
pour une grammaire aussi riche.

### 4.4 Conséquence pour RamyPulse

Avec quelques milliers d'annotations validées, RamyPulse ne doit pas tenter
d'enseigner toute cette grammaire. Le vocabulaire actif V0.1 est limité à :

- `<think>` et `</think>` comme délimiteurs ;
- `→` pour relier une preuve à une décision ;
- `∴` pour introduire la synthèse stable avant le JSON.

Les autres marqueurs restent dans les métadonnées canoniques ou sont reportés.
En particulier :

- confiance `●/◐/○` : calculée par accord professeur/critique et calibration ;
- vérification `☐/☑/✓` : ajoutée par les validateurs, jamais auto-déclarée par
  le SLM ;
- `⚠` : remplacé par les champs d'alerte typés ;
- entropie simulée : interdite pour une extraction déterministe ;
- `↺` : reporté tant que nous n'avons pas de trajectoires de correction.

Manifeste de la notation :
[`reasoning_notation_v0.1.json`](reasoning_notation_v0.1.json).

### 4.5 Compatibilité avec les candidats Qwen

Mesure directe avec les tokenizers publics :

| Élément | Qwen3.5-0.8B | Qwen3-0.6B |
|---|---:|---:|
| `<think>` | 1 token | 1 token |
| `</think>` | 1 token | 1 token |
| `→` | 1 token | 1 token |
| `∴` | 2 tokens | 1 token |

Il n'est donc pas nécessaire d'agrandir le vocabulaire pour le pilote. Ajouter
des tokens spéciaux obligerait à apprendre de nouvelles représentations et
compliquerait le fine-tuning, la quantification et la comparaison des modèles.

## 5. Transposition des cinq étapes à RamyPulse

| PleIAs `synth-funder` | RamyPulse |
|---|---|
| nature, langue, qualité | exploitabilité, pertinence, langue, scripts |
| entités | marques, produits, services, organisations, concurrents |
| relations | cible de l'opinion, aspect, sentiment, intention |
| identifiants | preuves exactes et offsets |
| style | sarcasme, négation, intensité, alertes, actionnabilité |

La trace RamyPulse doit répondre seulement aux questions qui peuvent modifier le
JSON :

1. le commentaire est-il exploitable et pertinent ?
2. quelles langues et écritures sont présentes ?
3. quels segments du texte constituent les preuves ?
4. quelles entités sont les cibles ?
5. quels sentiments, intentions et aspects découlent de chaque preuve ?
6. existe-t-il une alerte, avec quelle gravité ?
7. quelle file métier doit recevoir le cas ?
8. existe-t-il une ambiguïté réelle à conserver ?

## 6. Deux représentations complémentaires

### 6.1 Trace canonique d'audit

La trace canonique est un objet JSON séparé de l'annotation. Elle contient :

- le niveau et les facteurs de complexité ;
- le scan initial ;
- une carte de preuves dédupliquée avec texte et offsets ;
- les décisions sur entités, sentiment, intentions, aspects et alertes ;
- les règles de désambiguïsation appliquées ;
- les incertitudes résolues ou non résolues ;
- les empreintes du texte et de l'annotation ;
- le professeur, le critique et la version du prompt ;
- les résultats des validations.

Cette représentation sert au contrôle qualité, aux audits, à la régénération et
à la compilation des données. Elle n'est pas envoyée telle quelle au modèle de
production.

### 6.2 Trace compacte pour le SLM

Une fonction déterministe compile l'objet canonique vers une trace courte :

```text
<think>
scan → exploitable,directe,darija_arabe
ev1[8:12]="مليح" → produit_service.qualite_generale:+
ev2[17:26]="غالي بزاف" → prix_valeur.prix:-:forte
ev3[28:46]="ما لقيتوش فالحوانت" → disponibilite_acces.stock:-
ev1+ev2+ev3 → sentiment:mixte
∴ intents:avis,plainte; alerts:none; action:pricing/elevee
</think>
{JSON_COMPACT}
```

La syntaxe finale sera figée après mesure avec les tokenizers des modèles
candidats. Le principe important est que les labels restent lisibles et que
chaque décision importante référence une preuve.

## 7. Complexité RamyPulse V0.1

Score proposé :

- `+1` code-switching ;
- `+1` plusieurs écritures ;
- `+1` plusieurs entités ou cibles ;
- `+1` au moins trois aspects ;
- `+1` sentiment mixte ;
- `+1` aspect implicite ou portée de négation ;
- `+1` sarcasme ou comparaison ;
- `+1` alerte ;
- `+2` alerte élevée ou critique ;
- `+1` ambiguïté non résolue.

Niveaux initiaux :

| Niveau | Score | Plafond de trace étudiant |
|---|---:|---:|
| simple | 0–1 | 64 tokens |
| moyen | 2–3 | 128 tokens |
| complexe | 4+ | 192 tokens |

Ce sont des plafonds, pas des objectifs à remplir. Un cas simple ne doit pas
être allongé artificiellement.

## 8. Pipeline de génération retenu

### 8.1 Annotation cible

1. annoter en sortie structurée avec le schéma métier V0.1 ;
2. valider JSON, enums, relations, preuves et offsets ;
3. envoyer les échecs en réparation ou en revue humaine ;
4. figer l'annotation acceptée et calculer son empreinte.

### 8.2 Projection déterministe

Construire automatiquement :

- la carte de preuves depuis les champs `evidence` ;
- les décisions qui sont déjà explicitement présentes dans l'annotation ;
- la complexité ;
- les références entre preuves et décisions.

Le professeur ne doit pas régénérer ce qui peut être dérivé sans ambiguïté.

### 8.3 Back-reasoning du professeur

Le professeur reçoit :

- le commentaire ;
- son contexte autorisé ;
- l'annotation acceptée ;
- la projection déterministe ;
- le schéma de trace.

Il complète seulement :

- les règles de désambiguïsation ;
- la portée de négation ou du sarcasme ;
- les liens implicites ;
- les incertitudes et alternatives réellement considérées.

La génération doit utiliser une température basse et une sortie structurée. Une
température élevée n'est utile que pour produire plusieurs candidats, qui
doivent ensuite être classés.

### 8.4 Critique indépendante

Un modèle d'une autre famille vérifie :

- chaque preuve existe exactement aux offsets annoncés ;
- aucun label de la trace n'est absent du JSON ;
- aucun label du JSON important n'est oublié dans la trace ;
- aucune connaissance externe non autorisée n'est ajoutée ;
- la négation, le sarcasme et les cibles sont correctement reliés ;
- la longueur respecte le plafond.

### 8.5 Validation et sélection

Rejeter toute trace si :

- un offset est faux ;
- une preuve a été paraphrasée ;
- la trace et l'annotation se contredisent ;
- une alerte n'a pas de preuve ;
- un fait ou une entité a été inventé ;
- une incertitude critique reste non résolue ;
- le budget de tokens est dépassé après une tentative de compression.

Les cas à alerte élevée ou critique passent en revue humaine.

## 9. Format du dataset

Conserver un objet maître par exemple :

```text
example_id
text
context
annotation
decision_trace
compact_trace
training_text
source_provenance
generation_provenance
validation
split
```

Les vues `compact_trace + JSON`, tâches auxiliaires et contrôle `JSON only` sont
construites depuis cet objet maître. Elles ne doivent pas devenir des copies
indépendantes difficiles à synchroniser.

## 10. Décision

RamyPulse ne copiera pas la prose libre de `synth-funder`. Il adoptera son
architecture de back-reasoning, avec quatre renforcements :

1. projection déterministe depuis le JSON accepté ;
2. trace canonique structurée ;
3. preuve obligatoire pour chaque décision métier sensible ;
4. critique indépendant et validation bloquante.

Le format principal d'entraînement reste `trace compacte + JSON`. Le format
`JSON only` sert uniquement de contrôle d'ablation et de mode de secours si un
runtime ne permet pas la trace.
