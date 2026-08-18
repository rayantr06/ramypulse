# Baseline Gemini 3.5 Flash Lite — Gold candidat V0.1

Date : 29 juillet 2026  
Statut : baseline de référence, non validé pour une génération autonome

## Verdict

Gemini 3.5 Flash Lite peut servir de **pré-annotateur assisté**, mais ses sorties ne
doivent pas encore être utilisées directement comme données d'entraînement.

Les points les plus solides sont les intentions et les entités. Les faiblesses
principales sont :

1. la validité structurelle et l'alignement des preuves ;
2. le choix précis des familles et attributs d'aspects ;
3. la détection des commentaires non exploitables ;
4. les alertes, avec trop de faux positifs.

La revue experte avait déjà modifié 63 annotations sur 100. L'évaluation
quantitative confirme donc que la conformité JSON seule ne garantit pas la qualité
sémantique.

## Méthode

- Modèle : `gemini-3.5-flash-lite`
- Prédictions : sorties du pilote après normalisation déterministe des offsets
- Appels supplémentaires : aucun
- Gold : 100 commentaires relus, statut `single_reviewer_gold_candidate`
- DEV : 50 commentaires
- TEST verrouillé : 50 commentaires
- Chevauchement DEV/TEST : 0
- Politique de score : toute sortie absente, invalide ou sémantiquement incohérente
  est comptée comme une erreur
- Le benchmark DEV et TEST est exclu de tout entraînement

## Résultats de bout en bout

| Mesure | Global | DEV | TEST |
|---|---:|---:|---:|
| Sorties entièrement valides | 90 % | 94 % | 86 % |
| Exploitabilité — Macro-F1 | 0,750 | 0,984 | 0,444 |
| Pertinence business — Macro-F1 | 0,750 | 0,888 | 0,564 |
| Sentiment — Macro-F1 | 0,634 | 0,660 | 0,605 |
| Sarcasme — Macro-F1 | 0,842 | 0,906 | 0,457 |
| Langue dominante — Macro-F1 | 0,720 | 0,923 | 0,595 |
| Intentions — Micro-F1 | 0,851 | 0,863 | 0,836 |
| Aspects famille + attribut + sentiment — Micro-F1 | 0,674 | 0,681 | 0,667 |
| Alertes — précision | 0,278 | 0,222 | 0,333 |
| Alertes — rappel | 0,500 | 0,400 | 0,600 |
| Entités type + nom — Micro-F1 | 0,879 | 0,901 | 0,857 |
| Preuves correctement alignées | 97,7 % | 99,0 % | 96,5 % |

Le TEST est plus difficile que le DEV sur plusieurs axes rares. Cette différence
est utile : elle montre qu'un score moyen élevé sur les classes fréquentes serait
trompeur.

## Analyse des erreurs

### Validité

Sur 100 sorties :

- 4 violent le JSON Schema ;
- 6 autres passent le schéma mais échouent aux règles sémantiques ;
- 90 sont entièrement valides.

Les quatre erreurs de schéma comprennent des intentions hors vocabulaire, un
attribut d'aspect hors ontologie et des propriétés interdites dans une preuve.
Les erreurs sémantiques restantes concernent principalement des citations ou
offsets non alignés avec le commentaire original.

### Exploitabilité et pertinence

Le modèle classe à tort 3 des 5 commentaires non exploitables comme exploitables.
Il a donc tendance à produire une analyse métier même quand le texte ne permet pas
une conclusion fiable.

### Sentiment

Le sentiment global obtient 79 % d'exactitude, mais seulement 0,634 de Macro-F1.
Les deux cas mixtes sont manqués, et les sorties invalides touchent davantage les
commentaires négatifs. La classe majoritaire masque donc une faiblesse sur les cas
rares.

### Intentions

Les intentions sont le meilleur bloc métier :

- 148 associations correctes ;
- 23 associations ajoutées à tort ;
- 29 associations manquées ;
- Micro-F1 global : 0,851.

Les confusions dominantes concernent `avis`, `partage_experience`, `plainte` et
`suggestion`.

### Aspects

Sur 101 aspects gold :

- 64 triplets famille + attribut + sentiment sont corrects ;
- 25 sont ajoutés à tort ;
- 37 sont manqués.

Le Micro-F1 de 0,674 est insuffisant pour entraîner directement un modèle ABSA.
Les erreurs viennent surtout du routage vers la bonne famille, de l'attribut trop
générique et du sentiment associé à l'aspect.

### Alertes

Le modèle prédit 18 alertes pour 10 alertes gold :

- 5 vraies alertes détectées ;
- 13 faux positifs ;
- 5 alertes manquées.

Une plainte ordinaire est trop souvent transformée en alerte. Avec une précision
de 0,278, ce bloc est actuellement incompatible avec un usage opérationnel sans
revue humaine.

## Seuils avant le pilote d'entraînement

Les seuils sont mesurés de bout en bout, après au maximum une nouvelle tentative
contrôlée et la normalisation déterministe :

| Porte de qualité | Seuil |
|---|---:|
| Sorties entièrement valides | 100 % |
| Preuves et offsets alignés | 100 % |
| Exploitabilité — Macro-F1 | ≥ 0,90 |
| Rappel de la classe non exploitable | ≥ 0,80 |
| Pertinence business — Macro-F1 | ≥ 0,85 |
| Sentiment — Macro-F1 | ≥ 0,80 |
| Intentions — Micro-F1 | ≥ 0,85 |
| Aspects — Micro-F1 | ≥ 0,80 |
| Alertes — précision | ≥ 0,95 |
| Alertes — rappel | ≥ 0,80 |
| Entités — Micro-F1 | ≥ 0,90 |

La qualité des alertes devra aussi être confirmée sur un jeu de sécurité élargi
contenant au moins 30 cas positifs.

## Décision

**NO-GO pour la génération massive.**

**GO pour un cycle d'amélioration sur DEV**, limité au prompt V1, au validateur et
à une nouvelle tentative contrôlée. Le TEST reste verrouillé et ne doit pas être
utilisé pour choisir les corrections.

Après passage des seuils sur DEV :

1. geler le prompt et le schéma V1 ;
2. lancer un pilote de 200 nouveaux commentaires hors benchmark ;
3. contrôler manuellement un échantillon stratifié ;
4. exécuter une seule évaluation finale sur TEST ;
5. autoriser la génération étendue uniquement si les portes critiques passent.

## Fichiers de référence

- `data/processed/slm_v2_gold/business_comments_gold_dev_v0.1.jsonl`
- `data/processed/slm_v2_gold/business_comments_gold_test_v0.1.jsonl`
- `docs/slm_v2/gold_v0.1/split_manifest.json`
- `data/processed/slm_v2_baselines/gemini_3.5_flash_lite_gold_v0.1_predictions.jsonl`
- `docs/slm_v2/gold_v0.1/baselines/gemini_3.5_flash_lite_all.json`
- `docs/slm_v2/gold_v0.1/baselines/gemini_3.5_flash_lite_dev.json`
- `docs/slm_v2/gold_v0.1/baselines/gemini_3.5_flash_lite_test.json`
- `docs/slm_v2/gold_v0.1/baselines/acceptance_gates_v0.1.json`
