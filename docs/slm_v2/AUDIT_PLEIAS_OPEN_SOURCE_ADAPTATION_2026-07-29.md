# RamyPulse SLM V2 — audit des ressources open source PleIAs

Date : 29 juillet 2026  
Objet : identifier ce qui peut être utilisé directement, adapté ou seulement
étudié pour le pipeline de données synthétiques RamyPulse  
Périmètre audité : organisation GitHub PleIAs, modèles et datasets Hugging Face
associés

Audit détaillé de la génération et schéma RamyPulse des traces :
[`AUDIT_GENERATION_TRACES_PLEIAS_RAMYPULSE_2026-07-29.md`](AUDIT_GENERATION_TRACES_PLEIAS_RAMYPULSE_2026-07-29.md).

## 1. Verdict

La découverte la plus importante est
[`Pleias/synth-funder`](https://github.com/Pleias/synth-funder). Le problème
traité est très proche de RamyPulse :

- extraction d'informations depuis un texte non structuré ;
- ontologie fermée et règles de désambiguïsation ;
- sortie JSON complexe ;
- professeur de grande taille ;
- modèle spécialiste de production de 600M paramètres.

Cette expérience valide notre stratégie SLM. Elle ne fournit cependant pas un
pipeline intégralement réutilisable juridiquement :

- le dépôt `synth-funder` ne contient aucune licence ;
- les modèles `JZSG/baguette-funders-600m-4k`, `balanced-600M` et
  `gemma-12b-backreason` n'affichent pas de licence dans leurs métadonnées ;
- le dépôt `pleias/synth-gen` cité comme moteur de génération retourne 404 au
  29 juillet 2026 ;
- le corpus de 1,6 million d'exemples utilisé pour le petit modèle est privé.

Conclusion :

> **Nous pouvons reproduire indépendamment les principes publiés, mais nous ne
> devons pas copier le code `synth-funder`, ses données ou ses modèles dans un
> produit commercial sans licence ou autorisation écrite.**

Deux ressources sont réellement et immédiatement adaptables :

1. [`Pleias/toxic-commons`](https://github.com/Pleias/toxic-commons), sous MIT ;
2. [`Pleias/language_adherence_tests`](https://github.com/Pleias/language_adherence_tests),
   sous Apache 2.0.

Le dataset [`PleIAs/SYNTH`](https://huggingface.co/datasets/PleIAs/SYNTH) est
publié sous CC BY 4.0. Il sert surtout de référence de structure et, au besoin,
de petit replay généraliste en français. Il ne contient pas de Darija ni
d'arabe et ne constitue donc pas notre corpus métier.

## 2. Le cas `synth-funder`, analogue direct de RamyPulse

### Pipeline publié

PleIAs décrit quatre phases :

1. échantillonnage de 5 000 textes réels depuis 1,8 million de textes
   pré-annotés ;
2. annotation structurée par Gemini 3 Flash ;
3. génération d'une trace de raisonnement progressive avec longueur adaptée à
   la complexité ;
4. entraînement d'un professeur Gemma 3 12B, puis génération à grande échelle et
   continued pretraining d'un modèle de production d'environ 609M paramètres.

Le dépôt contient :

- `generation/annotate.py` ;
- `generation/generate_traces.py` ;
- `generation/remap_schema_v2.py` ;
- `training/full_sft.py` et `training/lora.py` ;
- 3 790 exemples d'entraînement et 200 exemples de test ;
- un fichier de configuration torchtitan pour le CPT du 600M.

### Ce qu'il démontre

| Élément PleIAs | Équivalent RamyPulse |
|---|---|
| texte de remerciement scientifique | commentaire consommateur ou citoyen |
| funder, projet, personne, infrastructure | entité, aspect, intention, alerte |
| règles de désambiguïsation | règles sentiment, pertinence et alertes |
| JSON structuré | annotation canonique RamyPulse |
| professeur 12B | professeur frontier ou open-weight fort |
| étudiant 600M | candidat RamyPulse 0,6B–0,8B |
| correction d'un schéma vers un autre | migration versionnée de l'ontologie |

La difficulté de `synth-funder` est au moins comparable à la nôtre. Cela renforce
la plausibilité d'un SLM inférieur à un milliard de paramètres.

### Ce que nous ne copierons pas littéralement

- le code sans licence ;
- le modèle 600M sans licence déclarée ;
- le corpus privé de 1,6 million de traces ;
- le full SFT 12B sur H100 comme première étape ;
- les chemins et configurations d'infrastructure spécifiques à PleIAs ;
- une trace de 100 à 600 mots pour chaque commentaire court.

### Décision corrigée sur les traces de raisonnement

PleIAs a déjà tranché la question générale en faveur des traces :

- `synth-funder` entraîne le professeur puis le 600M sur
  `raisonnement + annotation JSON` ;
- le corpus de continued pretraining du 600M contient explicitement des blocs
  `<think>` ;
- Baguettotron est entraîné nativement avec des traces denses et courtes, une
  grammaire sténographique (`→`, `↺`, `∴`, confiance, vérification et entropie
  simulée) et plusieurs tokens réservés dans son tokenizer ;
- sa carte modèle indique que forcer une réponse sans raisonnement dégrade
  significativement la majorité des tâches testées.

La variante RamyPulse retenue est donc :

> **trace de décision compacte et adaptative pendant l'entraînement et
> l'inférence, suivie du JSON final.**

La trace ne sera pas une dissertation. Elle contiendra seulement les décisions
utiles : langue, pertinence, preuves textuelles, désambiguïsations
aspect/sentiment/intention/alerte et incertitude éventuelle. Sa profondeur
augmentera uniquement pour les commentaires ambigus ou multi-aspects.

L'API métier continuera à retourner le JSON canonique uniquement. La trace sera
générée en amont du JSON, puis analysée par le serveur et non exposée par défaut.

`annotation_only` est rétrogradé au rôle de contrôle d'ablation. Il permettra de
quantifier le coût et le gain des traces sur RamyPulse, mais ce n'est plus
l'hypothèse principale. PleIAs ne publie pas, dans `synth-funder`, une ablation
contrôlée spécifique comparant une trace longue à une trace compacte ; la
compacité exacte reste donc un paramètre d'ingénierie à calibrer.

## 3. Toxic Commons : la ressource directement adaptable

Sources :

- [code GitHub MIT](https://github.com/Pleias/toxic-commons) ;
- [dataset Toxic Commons](https://huggingface.co/datasets/PleIAs/ToxicCommons) ;
- [modèle Celadon](https://huggingface.co/PleIAs/celadon).

### Méthode PleIAs

Le pipeline comporte :

1. annotation par un professeur sur cinq axes, chacun noté de 0 à 3 ;
2. apprentissage d'un classifieur multi-têtes léger ;
3. séparation des textes selon des seuils : non toxique, toxicité légère,
   toxicité forte ;
4. conservation, avertissement ou réécriture synthétique selon le niveau ;
5. réintroduction contrôlée durant l'annealing plutôt que suppression aveugle.

Les axes publiés sont :

- origine/race ;
- genre/sexualité ;
- religion ;
- handicap/capacité ;
- violence ou abus.

### Usage RamyPulse

Nous pouvons reprendre légalement le code MIT et adapter la méthode :

| Toxic Commons | RamyPulse |
|---|---|
| cinq axes universels | taxonomie d'alertes RamyPulse |
| notes 0–3 | `none`, `low`, `medium`, `high` |
| Llama 8B professeur | professeur validé sur Darija |
| DeBERTa multi-têtes | SLM ou classifieur auxiliaire multilingue |
| données de livres historiques | commentaires algériens CC BY |
| avertissement/réécriture | conservation, quarantaine ou cas synthétique corrigé |

Les axes RamyPulse candidats sont :

- `hate_or_discrimination` ;
- `harassment_or_bullying` ;
- `threat_or_violence` ;
- `offensive_language` ;
- `fraud_or_scam` ;
- `health_or_product_safety` ;
- `legal_or_reputation_risk`.

### Limite importante

Celadon n'est pas directement utilisable comme juge Darija. Il a été entraîné
sur neuf langues européennes :

`en`, `fr`, `es`, `de`, `pl`, `nl`, `pt`, `la`, `it`.

Le modèle et sa carte précisent aussi qu'il est conçu pour des documents du
Common Corpus, pas pour du webtext. Nous réutiliserons donc **le pipeline et le
code MIT**, mais nous entraînerons ou calibrerons les têtes sur les 14 150
commentaires algériens de toxicité et sur le gold RamyPulse.

## 4. SYNTH : à utiliser comme architecture de données

Le dataset PleIAs/SYNTH expose les champs utiles suivants :

- `synth_id` ;
- `language` ;
- `exercise` ;
- `model` ;
- `query` ;
- `query_seed_url` et `query_seed_text` ;
- `additional_seed_url` ;
- `seed_license` ;
- `constraints` ;
- `script` ;
- `synthetic_reasoning` ;
- `synthetic_answer` ;
- `words`.

Cette structure est directement transposable à RamyPulse :

| SYNTH | RamyPulse |
|---|---|
| `query_seed_url` | `source_url` ou identifiant du corpus |
| `query_seed_text` | commentaire source |
| `seed_license` | licence vérifiée et statut commercial |
| `exercise` | famille de difficulté métier |
| `constraints` | combinaison secteur/langue/aspect/alerte |
| `script` | version du générateur de prompt |
| `synthetic_reasoning` | trace privée du professeur/critique |
| `synthetic_answer` | annotation canonique |
| `model` | fournisseur, modèle et version |

PleIAs insiste sur trois éléments que nous reprenons :

1. graines dont les droits et la provenance sont clairs ;
2. contraintes aléatoires mais enregistrées ;
3. proportion importante de cas négatifs pour limiter les hallucinations.

Nous n'utiliserons pas le dataset SYNTH complet de 236 Go. Il est majoritairement
anglais et ne couvre pas l'arabe. Un petit échantillon français d'extraction
pourra éventuellement servir de replay lors d'un CPT, mais seulement si un test
d'ablation montre un bénéfice.

## 5. Tests d'adhérence linguistique

Le dépôt
[`language_adherence_tests`](https://github.com/Pleias/language_adherence_tests)
est sous Apache 2.0. Il compare la langue du prompt et de la continuation.

Le principe est utile, mais CLD3 ne sait pas distinguer correctement :

- Darija algérienne et arabe standard ;
- Arabizi et français ;
- un commentaire réellement code-switché.

Notre adaptation doit mesurer séparément :

- conservation de l'écriture arabe ;
- conservation de l'Arabizi ;
- taux de français injecté ou perdu ;
- conformité du champ `language.dominant` ;
- respect du code-switching dans les preuves citées ;
- absence de traduction ou normalisation non demandée.

## 6. Autres dépôts PleIAs

| Dépôt | Licence observée | Décision RamyPulse |
|---|---|---|
| `nanotron-pleias` | Apache 2.0 | utile seulement pour pré-entraînement distribué lourd ; pas nécessaire au pilote QLoRA |
| `Quest-Best-Tokens` | MIT | ressource pédagogique sur le décodage ; pas un pipeline de données |
| `OCRoscope` | MIT | utile pour documents OCR, peu pertinent pour commentaires sociaux |
| `open_data_toolkit` | aucune | seulement un README listant OCRonos, Segmentext, Celadon et Topical |
| `Various-Finetuning` | aucune | un ancien script Jamba ; ne pas intégrer |
| `RAG-Eval` | aucune | idées d'évaluation, mais code non réutilisable sans licence |
| `Pleias-RAG-Library` | fichier `LICENSE` vide | ne pas copier ; les concepts de citations sont déjà réimplémentés dans nos preuves avec offsets |
| `synthetic-ocr` | dépôt vide | rien à utiliser |
| `redline-docker-by-Matthieu` | aucune | déploiement RAG, hors du besoin immédiat |
| `RL-Reasoning` | aucune | matériel exploratoire, non nécessaire pour le SFT initial |

Le produit Synth Beta présenté par PleIAs n'est pas le même objet que le dataset
SYNTH. Le code complet de ce service n'est pas publié dans l'organisation GitHub
auditée.

## 7. Pipeline PleIAs adapté à RamyPulse

### Phase 0 — droits et séparation des jeux

- ne générer qu'à partir d'une graine autorisée ;
- stocker licence, URL, version et hash ;
- geler DEV et TEST avant toute amplification ;
- interdire tout quasi-doublon entre train et évaluation.

### Phase 1 — couverture réelle

Mesurer la distribution du gold et des corpus ouverts pour :

- langue et écriture ;
- secteur ;
- pertinence business ;
- sentiment et intensité ;
- intention ;
- famille et attribut d'aspect ;
- type et gravité d'alerte ;
- difficulté : négation, implicite, sarcasme, multi-entité, ambiguïté.

### Phase 2 — grammaire de contraintes

Générer seulement les cellules manquantes ou insuffisantes. Exemples
d'exercices :

1. commentaire non pertinent ressemblant à un commentaire business ;
2. même phrase avec négation qui inverse le sentiment ;
3. deux aspects de sentiments opposés ;
4. alerte mentionnée de manière descriptive mais sans risque réel ;
5. question d'achat sans sentiment ;
6. plainte implicite sans mot négatif évident ;
7. variante arabe, Arabizi et code-switching d'un même cas ;
8. faute, abréviation, emoji et répétition réalistes ;
9. commentaire avec marque dans le contexte mais absente du texte ;
10. extrait impossible à citer, qui doit produire zéro preuve.

### Phase 3 — professeur et critique

Pour chaque exemple :

1. un générateur propose le commentaire et l'annotation ;
2. un critique indépendant vérifie cohérence, naturel algérien et conformité au
   schéma ;
3. les validateurs déterministes contrôlent JSON, enums, offsets, références et
   règles sémantiques ;
4. les cas à haute gravité ou faible confiance passent en revue humaine ;
5. chaque rejet est conservé avec sa raison.

### Phase 4 — vues d'entraînement

Produire depuis un même objet canonique :

- `compact_decision_trace + answer`, vue principale ;
- `answer_only`, contrôle d'ablation ;
- tâches auxiliaires sentiment, toxicité, NER et langue ;
- exemples négatifs où la sortie correcte est vide ou neutre.

### Phase 5 — ablations

Comparer sur le même TEST :

1. gold réel uniquement ;
2. gold + corpus ouverts ;
3. gold + synthétique ciblé ;
4. même mélange sans trace, contrôle d'ablation ;
5. même mélange avec ou sans CPT linguistique.

La trace compacte est l'hypothèse principale issue des travaux PleIAs. Le
contrôle sans trace vérifie sa transférabilité à RamyPulse et mesure son coût de
latence. Le synthétique n'est conservé que s'il améliore les macro-F1 rares et
les preuves sans dégrader la distribution naturelle.

## 8. Décision

La stratégie retenue est :

- **adapter directement** Toxic Commons et les tests d'adhérence linguistique,
  en conservant leurs notices MIT/Apache ;
- **reproduire indépendamment** l'architecture de `synth-funder` ;
- **reprendre le schéma de traçabilité** du dataset SYNTH ;
- **ne pas dépendre** d'un code, d'un modèle ou d'un corpus PleIAs sans licence ;
- **ne générer qu'après** le rapport de couverture des corpus algériens réels.

Cette solution utilise effectivement le meilleur des travaux PleIAs tout en
restant compatible avec un produit commercial, la Darija algérienne et les
contraintes de latence RamyPulse.
