# RamyPulse SLM V2 — choix du modèle de base et cible d'inférence

Date de décision : 29 juillet 2026  
Statut : recommandation d'architecture à valider par benchmark RamyPulse  
Périmètre : analyse structurée de commentaires business multilingues, avec priorité au contexte algérien

## 1. Décision exécutive

Le meilleur point de départ pour RamyPulse V2 est désormais :

> **une stratégie edge-first avec `Qwen/Qwen3.5-0.8B` post-entraîné,
> spécialisé par SFT LoRA/QLoRA en mode non-thinking, sortie filaire compacte
> contrainte, puis reconstruction déterministe du JSON canonique.**

Le matériel d'entraînement peut être loué sur Colab, RunPod ou un fournisseur
équivalent. Le matériel qui définit le produit est celui de **l'inférence** :
RamyPulse V2 doit d'abord fonctionner sur CPU, sans carte graphique obligatoire.

Ce n'est pas encore une décision irréversible. La décision finale doit être prise
après un benchmark identique sur les candidats suivants :

1. **Candidat principal edge — Qwen3.5-0.8B** : meilleur équilibre attendu entre
   couverture linguistique, extraction structurée, licence Apache 2.0 et CPU.
2. **Contrôle edge mature — Qwen3-0.6B** : plus ancien et très léger, avec une
   pile GGUF/llama.cpp plus éprouvée.
3. **Contrôle extrême — LFM2.5-350M ou LFM2-350M-Extract** : conçu pour
   l'extraction structurée sur CPU et couvrant arabe/français, mais sa licence
   commerciale impose une revue juridique avant d'en faire le socle du produit.
4. **Repli qualité — Qwen3.5-2B** : à utiliser seulement si les modèles edge
   échouent sur les aspects, les alertes ou le code-switching.
5. **Contrôle PleIAs — Baguettotron/Pleias-SLM-RAG 321M** : référence de taille,
   spécialisation et matériel, mais pas candidat linguistique pour la Darija.

Le 4B et Gemma 4 E2B sortent du premier pilote : ils restent des plafonds de
diagnostic, pas la cible d'un produit algérien facile à déployer.

## 2. Pourquoi utiliser le checkpoint post-entraîné, pas le modèle `Base`

RamyPulse dispose de quelques milliers d'exemples supervisés, pas des centaines
de millions d'instructions. Le checkpoint post-entraîné connaît déjà :

- le suivi d'instructions ;
- les conversations ChatML ;
- le formatage et les sorties structurées ;
- le mode non-thinking ;
- les langues générales.

Le modèle `Base` serait pertinent pour un véritable mid-training linguistique ou
un programme de post-entraînement beaucoup plus large. Avec environ 7 426
commentaires, commencer par `Qwen3.5-2B-Base` augmenterait le risque, le coût et
le volume de données requis sans avantage démontré.

La stratégie recommandée est donc :

1. SFT du checkpoint post-entraîné ;
2. audit des erreurs linguistiques ;
3. mid-training Darija/Arabizi uniquement si l'audit montre que le SFT ne suffit
   pas.

## 3. Ce que PleIAs démontre — et ce qu'il ne faut pas copier

### À reprendre

PleIAs démontre qu'un petit modèle spécialiste peut devenir exploitable quand :

- la tâche est bornée ;
- les sorties et les preuves sont conçues pour être auditables ;
- la majorité de l'effort porte sur la préparation des données ;
- le modèle est évalué sur le matériel final ;
- le déploiement reste entièrement local.

En juillet 2026, PleIAs documente un spécialiste juridique d'environ 321M
paramètres, quantifié en GGUF Q8, exécutant toute sa chaîne de raisonnement et de
citation à **28 tokens/s sur Raspberry Pi 5**, avec quatre threads CPU, sans GPU
et sans API externe. Le fichier de poids fait environ 328 Mo. Cela valide la
philosophie SLM souveraine et spécialisée.

Le cas comparable est `PleIAs/Pleias-SLM-RAG`, dérivé de Baguettotron et entraîné
pour l'assistant juridique Redline. Il doit :

- comprendre la question ;
- analyser des sources juridiques ;
- décider si elles suffisent ;
- produire une réponse ancrée avec citations exactes ;
- fonctionner entièrement hors ligne.

`PleIAs/Pleias-RAG-350M` confirme la même classe de complexité : classification
de la requête, détection de langue, analyse multi-source, raisonnement et réponse
citée. Ce n'est donc pas un exemple artificiellement facile.

### Mesure locale de contrôle

Nous avons exécuté le GGUF officiel `PleIAs/Baguettotron-GGUF` Q4_K_M
sur le poste RamyPulse actuel, en CPU uniquement :

- modèle : 320,96M paramètres, fichier de 228,6 Mo ;
- machine : Intel Core i5-10300H, 4 cœurs / 8 threads, 8 Go de RAM ;
- threads utilisés : 4 ;
- préremplissage 128–512 tokens : **120,5 à 122,9 tokens/s** ;
- génération : **29,2 à 44,7 tokens/s**.

Cette mesure indépendante rejoint les 28 tokens/s publiés par PleIAs sur
Raspberry Pi 5. Elle prouve que la classe 300–350M est réellement exploitable sur
une machine modeste. Elle ne prouve pas qu'un modèle PleIAs non spécialisé sait
annoter la Darija : un essai zero-shot n'a pas respecté notre JSON, ce qui
confirme précisément la nécessité du fine-tuning métier.

### Complexité PleIAs versus RamyPulse

| Dimension | PleIAs Redline/RAG 321–350M | RamyPulse V2 |
|---|---|---|
| Entrée | Question + plusieurs sources longues | Commentaire généralement court |
| Raisonnement | Pertinence, suffisance, synthèse multi-source | Pertinence, sentiment, intentions, aspects, alertes |
| Sortie | Réponse développée avec citations | Structure très dense à vocabulaire fermé |
| Difficulté linguistique | Langues européennes couvertes au pré-entraînement | Darija, arabe, français, arabizi et code-switching |
| Preuve | Citation des sources | Offsets exacts dans le commentaire |
| Volume spécialisé public | Environ 1,05M exemples Redline | Environ 7 426 annotations générées, gold plus petit |

La tâche PleIAs est plus lourde en contexte et en raisonnement multi-source.
RamyPulse est plus difficile sur la langue et la densité du contrat de sortie,
mais son entrée est beaucoup plus courte et son ontologie est fermée. La
complexité est donc suffisamment comparable pour justifier un essai 350–800M,
sans garantir à l'avance que 350M suffira.

### À ne pas copier aveuglément

Le dataset SYNTH public contient environ 79,6 millions d'exemples et 75 milliards
de tokens, mais il est limité à l'anglais et à sept langues européennes. Sa carte
indique explicitement que le multilingue mondial est hors périmètre. Les modèles
PleIAs actuels sont surtout orientés RAG, citations et langues européennes.

Le dataset spécialisé `BSF_Redline` contient environ **1,05 million d'exemples**.
RamyPulse dispose actuellement d'environ 7 426 annotations générées, dont le gold
humain est encore beaucoup plus petit. La petite taille du modèle PleIAs ne doit
donc pas masquer l'investissement massif dans les données.

Pour RamyPulse :

- **la méthode SYNTH est pertinente** ;
- **une trace de décision compacte constitue le signal d'apprentissage principal
  et précède le JSON à l'inférence** ;
- **l'API métier ne retourne que le JSON final** ;
- **les poids PleIAs ne constituent pas le meilleur prior linguistique** ;
- **les données doivent être amplifiées à partir de commentaires algériens et de
  cas métier réels**, pas à partir d'un corpus encyclopédique européen.

## 4. État de l'art utile pour RamyPulse

### 4.1 Qwen3 et Qwen3.5

Qwen3 est publié sous Apache 2.0 et documente 119 langues et dialectes. La liste
inclut explicitement l'arabe standard, marocain, tunisien, égyptien, levantin,
najdi et d'autres variantes. Même si l'algérien n'est pas nommé, les variantes
maghrébines voisines, le français et le large vocabulaire constituent le meilleur
prior public parmi les modèles compacts comparés.

Qwen3.5 étend la couverture annoncée à 201 langues et dialectes. Les tailles
0.8B, 2B et 4B utilisent une architecture hybride Gated DeltaNet/attention et
sont publiées sous Apache 2.0. Le serveur vLLM peut charger uniquement le modèle
de langue afin d'ignorer l'encodeur visuel, ce qui correspond au périmètre texte
de RamyPulse.

Point opérationnel : Qwen3.5 reste récent. Ses cartes recommandent encore des
versions très récentes ou nightly de vLLM/SGLang. Il faut donc figer les versions
dans un conteneur et conserver Qwen3-0.6B comme contrôle edge à pile plus mature.

### 4.2 Résultat de fine-tuning le plus proche de notre cas

Une étude de juin 2026 sur l'extraction structurée de transactions compare des
modèles de 270M à 8B, avec 8 015 exemples et un déploiement de validation sur
Databricks :

| Variante | F1 rapporté | Débit local rapporté |
|---|---:|---:|
| Qwen3.5-4B JSON-only | 0,9660 | 0,51 échantillon/s |
| Qwen3.5-2B FT non-thinking | 0,9518 | 0,98 échantillon/s |
| Qwen3.5-0.8B FT non-thinking | 0,9475 | 1,32 échantillon/s |
| Gemma 3 1B FT | 0,9393 | 2,16 échantillons/s |

L'étude conclut également que :

- le mode non-thinking conserve pratiquement la même qualité ;
- il peut être jusqu'à 2,9 fois plus rapide selon le prompt ;
- un LoRA de rang 8 suffit dans leur expérience ;
- les résultats Qwen et Gemma se transfèrent correctement vers leur endpoint de
  production ;
- la compatibilité du runtime doit compter dans la décision, pas seulement le F1.

Ces résultats ne prédisent pas directement RamyPulse : leur JSON est différent,
leurs langues aussi, et leurs mesures proviennent d'un DGX Spark. Ils fournissent
néanmoins la preuve externe la plus proche en faveur de la famille Qwen3.5.

### 4.3 Gemma 4

Gemma 4 est maintenant publié sous Apache 2.0, avec 140+ langues et une prise en
charge native du JSON structuré. Il doit être inclus dans le benchmark, mais avec
deux réserves :

- E2B représente 2,3B paramètres « effectifs », mais environ 5,1B paramètres avec
  les embeddings ;
- la famille et sa pile de fine-tuning sont beaucoup plus récentes que Qwen3.

Gemma 4 E4B représente environ 8B paramètres réels. Il ne correspond pas à la
cible CPU légère de RamyPulse, même avec quantification forte.

### 4.4 Autres modèles examinés

| Famille | Avis pour RamyPulse |
|---|---|
| LFM2.5-350M / LFM2-350M-Extract | 350M, arabe et français, spécifiquement positionné pour extraction JSON/XML/YAML sur CPU ; excellent contrôle extrême, mais licence commerciale limitée au seuil de 10 M USD. |
| LFM2.5-1.2B | Très rapide sur CPU, arabe et français ; candidat de repli inter-famille, avec la même réserve de licence. |
| Phi-4-mini 3.8B | Licence MIT, arabe et français ; intéressant comme contrôle, mais entraînement annoncé principalement anglophone et moins de preuves spécifiques sur Darija/extraction. |
| SmolLM3-3B | Excellent niveau d'ouverture, mais ses langues natives n'incluent pas l'arabe. |
| DeepSeek-R1-Distill-Qwen-1.5B | Prior Qwen2.5 plus ancien et comportement de raisonnement inutilement verbeux pour un annotateur JSON. |
| MiniCPM4 | Très efficace, mais les versions principales sont 8B et orientées chinois/anglais. |
| Baguettotron / Pleias-SLM-RAG / Pleias-RAG-350M | Preuve matérielle et méthodologique majeure à 321–350M ; mauvais prior linguistique pour la Darija. |

## 5. Matrice de décision

Les notes sont une présélection technique, pas des résultats RamyPulse.

| Modèle | Darija/Arabizi attendu | JSON métier | Maturité runtime | Empreinte | Licence | Rôle |
|---|---:|---:|---:|---:|---:|---|
| Qwen3.5-0.8B | 4/5 | 5/5 | 4/5 | 5/5 | 5/5 | **Choix principal edge** |
| Qwen3-0.6B | 4/5 | 4/5 | 5/5 | 5/5 | 5/5 | **Contrôle edge mature** |
| LFM2.5-350M / Extract | 3/5 | 5/5 | 4/5 | 5/5 | 2/5 | **Contrôle extrême CPU** |
| Qwen3.5-2B | 5/5 | 5/5 | 4/5 | 3/5 | 5/5 | **Repli qualité** |
| Baguettotron 321M | 1/5 | 3/5 | 5/5 | 5/5 | 5/5 | **Contrôle matériel** |

La procédure de décision doit appliquer des **portes éliminatoires de qualité**
avant tout score pondéré. Un modèle plus rapide ne doit jamais compenser une
faible précision sur les alertes ou les aspects.

Après franchissement de toutes les portes critiques, le classement peut utiliser :

- qualité métier : 60 % ;
- latence en ligne : 15 % ;
- débit batch : 10 % ;
- mémoire : 10 % ;
- licence et maturité opérationnelle : 5 %.

## 6. Format d'entraînement recommandé

### SFT avec trace de décision compacte

Entrée :

- instruction système courte et stable ;
- texte original ;
- contexte disponible : marque, secteur, source et date, sans inventer les
  informations absentes.

Sortie :

- une trace `<think>` courte et structurée, adaptée à la complexité ;
- langue et pertinence ;
- preuves exactes et décisions de désambiguïsation ;
- incertitude uniquement lorsqu'elle existe ;
- JSON compact immédiatement après `</think>` ;
- aucun Markdown ni commentaire après le JSON ;
- température 0 pour l'évaluation et l'exploitation ;
- preuves textuelles ou offsets strictement ancrés dans le commentaire.

La trace est un espace de décision, pas une explication littéraire. Une première
contrainte d'ingénierie limitera son budget à environ 64 tokens pour les cas
simples et 128 tokens pour les cas complexes, à ajuster sur DEV.

Les 3 000 anciennes générations peuvent servir de matière première, mais leurs
traces longues ne doivent pas être reprises automatiquement. Elles doivent être
validées, ramenées au format compact et rattachées à des preuves exactes.

PleIAs fournit ici une réponse directionnelle forte : `synth-funder` entraîne
son professeur et son modèle 600M avec raisonnement puis annotation, et la carte
Baguettotron rapporte une baisse significative lorsque le raisonnement est
désactivé à l'inférence. Le format sans trace reste uniquement un contrôle
d'ablation RamyPulse ; l'expérience encore ouverte concerne la longueur optimale,
pas l'utilité générale du signal de raisonnement.

### Format canonique et format filaire

Le schéma canonique V0.1 doit rester lisible et stable pour le stockage, l'API et
l'audit. Pour réduire la latence, le SLM peut apprendre un **format filaire
compact** ensuite transformé de manière déterministe vers le schéma canonique.

Optimisations possibles :

- omettre `schema_version`, ajoutée par le serveur ;
- ne produire que `start` et `end`, puis reconstruire `evidence.text` ;
- remplacer les chaînes d'énumération par des codes courts sur le fil ;
- reconstruire les valeurs constantes et les champs nuls dans le post-traitement.

Cette séparation réduit le nombre de tokens sans sacrifier le contrat métier.

## 7. Audit réel de longueur sur le gold RamyPulse

Mesure effectuée sur les 100 annotations gold candidates actuelles :

| Tokenizer | Entrée moyenne | Entrée P95 | Sortie moyenne | Sortie P95 |
|---|---:|---:|---:|---:|
| Qwen3.5-0.8B/2B, JSON canonique | 39,5 | 102 | 259,3 | 345 |
| Qwen3.5-0.8B/2B, format compact | 39,5 | 102 | **127,1** | **175** |
| Qwen3-0.6B, JSON canonique | 45,9 | 121 | 267,0 | 353 |
| Qwen3-0.6B, format compact | 45,9 | 121 | **130,6** | **181** |
| Baguettotron, JSON canonique | — | — | 290,5 | 389 |
| Baguettotron, format compact | — | — | **131,9** | **171** |

Le maximum Qwen3.5 observé atteint 835 tokens en entrée et 541 tokens en sortie
canonique. Le format compact réduit la sortie moyenne d'environ **51 %**, de
259,3 à 127,1 tokens, et son P95 de 345 à 175 tokens.

La sortie, pas l'entrée, domine la latence. Au débit CPU réellement mesuré sur le
321M PleIAs, 127 tokens représentent environ 2,8 à 4,4 secondes de génération ;
175 tokens P95 représentent environ 3,9 à 6 secondes. Un modèle 0.8B sera
probablement plus lent et doit être mesuré. L'objectif historique « moins de
200 ms par commentaire » n'est pas crédible sur CPU pour le JSON complet.

## 8. Objectifs de latence et de capacité

Les SLO doivent être mesurés sur des commentaires réels, modèle chaud, sans
inclure le démarrage du serveur.

### Profil client minimal — CPU sans GPU

- x86-64 avec AVX2, au moins 4 cœurs physiques ;
- 8 Go de RAM, SSD, Windows ou Linux ;
- GGUF Q4/Q5, contexte limité à 2 048 tokens ;
- latence P95 de certification : **≤ 8 s/commentaire** ;
- débit minimal soutenu : **≥ 0,2 commentaire/s** ;
- taux d'échec ou timeout : **< 0,1 %**.

À 0,2 commentaire/s, une seule machine traite environ 720 commentaires/heure,
soit 17 280 par jour si la file fonctionne en continu.

### Profil PME recommandé — CPU sans GPU

- 6 à 8 cœurs CPU modernes ;
- 16 Go de RAM et SSD NVMe ;
- latence P95 cible : **≤ 5 s/commentaire** ;
- débit cible : **≥ 0,3 commentaire/s**.

Le tableau de bord ne doit pas attendre l'analyse en direct : les nouveaux
commentaires sont traités en file de fond et les agrégats sont pré-calculés.

### Profil batch nocturne

- mesurer les concurrences 1, 8 et 32 ;
- maximiser le débit sans baisse de qualité ;
- enregistrer commentaires/s, tokens/s, P50/P95/P99, VRAM maximale et énergie ;
- séparer préfill, TTFT et décodage.

### Profil hub optionnel

Une petite carte GPU de 6 à 12 Go ou un serveur loué n'est utile que pour un
volume centralisé élevé, le batching ou le repli Qwen3.5-2B. Elle ne doit pas
être obligatoire chez chaque client.

Ces valeurs sont des objectifs de produit à confirmer sur les modèles
fine-tunés. Le Raspberry Pi 5 8 Go devient une cible de démonstration et de
certification pour la classe 350M ; il n'est pas encore promis pour le 0.8B.

## 9. Matériel

### Matériel constaté sur le poste actuel

- GPU : NVIDIA GeForce GTX 1650, 4 Go ;
- RAM système : environ 8 Go ;
- CPU : Intel Core i5-10300H, 4 cœurs / 8 threads.

Ce poste permet de préparer les données, d'exécuter l'évaluateur et de tester un
petit GGUF quantifié. Il n'est pas une plateforme fiable pour fine-tuner un 2B ou
un 4B ni pour mesurer la production.

### Cible commerciale retenue

La cible n'est plus une RTX 5070. Elle est :

> **CPU ordinaire + 8 Go de RAM au minimum ; CPU 6–8 cœurs + 16 Go de RAM
> recommandé ; aucune carte graphique obligatoire.**

Une configuration GPU reste un profil hub optionnel et une machine
d'entraînement, pas une exigence commerciale.

### Ordres de grandeur mémoire des poids

Les chiffres ci-dessous excluent les activations, le KV cache et le runtime.

| Modèle | BF16 | INT8 | 4-bit approximatif |
|---|---:|---:|---:|
| PleIAs/Baguettotron 321M | 0,64 Go | 0,32 Go | 0,23 Go mesuré |
| LFM2.5-350M | 0,70 Go | 0,35 Go | 0,25 Go |
| Qwen3-0.6B | 1,2 Go | 0,6 Go | 0,4 Go |
| Qwen3.5-0.8B | 1,6 Go | 0,8 Go | 0,5 Go |
| LFM2.5-1.2B | 2,4 Go | 1,2 Go | 0,7 Go |
| Qwen3-1.7B | 3,4 Go | 1,7 Go | 1,0 Go |
| Qwen3.5-2B | 4,0 Go | 2,0 Go | 1,2 Go |
| Qwen3.5-4B | 8,0 Go | 4,0 Go | 2,4 Go |
| Gemma 4 E2B, 5.1B réels | 10,2 Go | 5,1 Go | 3,0 Go |

Pour RamyPulse, le contexte serveur doit être limité à **2 048 ou 4 096 tokens**.
Charger les 128K ou 262K annoncés par les modèles gaspillerait la VRAM sans
valeur métier.

### Fine-tuning

L'entraînement est dissocié du matériel client. Une instance cloud de 16 à 24 Go
de VRAM suffit pour les pilotes LoRA/QLoRA 0.35B–2B ; une machine plus grande
réduit seulement la durée d'itération.

Configuration initiale :

- SFT LoRA/QLoRA ;
- rang 8, alpha 16 ;
- longueur 1 024 puis 2 048 uniquement si nécessaire ;
- batch par device 1 ;
- accumulation 8 ou 16 ;
- gradient checkpointing ;
- 3 à 6 époques avec sélection du meilleur checkpoint sur DEV ;
- deux graines au minimum pour les deux finalistes.

## 10. Runtimes de production

### Hub GPU optionnel

Utiliser **vLLM** pour :

- continuous batching ;
- API compatible OpenAI ;
- métriques TTFT, TPOT, latence inter-token et débit ;
- sortie structurée à partir d'un modèle Pydantic ou JSON Schema ;
- chargement Qwen3.5 en mode langue uniquement.

Les versions doivent être figées et testées dans un conteneur reproductible.

### Runtime principal CPU et local

Utiliser **llama.cpp** avec GGUF pour :

- quantification Q4/Q5 ;
- offload CPU/GPU ;
- grammaire GBNF ou JSON Schema ;
- déploiement simple hors ligne.

Le moteur qui produit le meilleur score local n'est pas automatiquement le moteur
de production. Le checkpoint final doit être revalidé dans le runtime final.

## 11. Protocole de benchmark

### Phase A — présélection sans entraîner le TEST

Sur DEV uniquement :

1. mesurer la tokenisation Darija, arabe, Arabizi, français et code-switching ;
2. exécuter le même prompt avec trace compacte et un contrôle sans trace ;
3. vérifier JSON, valeurs hors vocabulaire et preuves ;
4. mesurer mémoire et latence ;
5. éliminer les candidats manifestement faibles.

### Phase B — pilote identique

Fine-tuner les candidats restants avec :

- les mêmes exemples ;
- le même ordre de données ;
- le même rang LoRA ;
- le même nombre d'époques ;
- le même budget de tokens ;
- le même évaluateur.

Ne pas ajuster une famille avec le TEST.

### Phase C — finalistes

1. entraîner Qwen3.5-0.8B et le meilleur challenger edge sur l'ensemble autorisé ;
2. exécuter deux graines ;
3. sélectionner sur DEV ;
4. geler modèle, prompt, runtime et post-traitement ;
5. ouvrir le TEST une seule fois.

### Phase D — production simulée

- runtime final ;
- quantification finale ;
- batch réel ;
- 30 minutes de warm-up et charge stable ;
- cas courts, P95 et longs ;
- tests de concurrence ;
- test de redémarrage et de reproductibilité ;
- journalisation sans fuite du texte client.

## 12. Portes de qualité

Les portes V0.1 existantes restent prioritaires :

- sortie valide : 100 % ;
- preuves alignées : 100 % ;
- exploitabilité Macro-F1 ≥ 0,90 ;
- pertinence business Macro-F1 ≥ 0,85 ;
- sentiment Macro-F1 ≥ 0,80 ;
- intentions Micro-F1 ≥ 0,85 ;
- aspects famille + attribut + sentiment Micro-F1 ≥ 0,80 ;
- alertes précision ≥ 0,95 et rappel ≥ 0,80.

La sortie JSON doit être contrainte par le runtime, mais la contrainte syntaxique
ne corrige pas les erreurs sémantiques. Les alertes doivent être évaluées sur au
moins 30 positifs et, de préférence, beaucoup plus.

Le gold actuel de 100 exemples suffit pour orienter la R&D, pas pour certifier la
production. Avant le choix final, constituer au minimum :

- **500 exemples gold** relus et stratifiés ;
- idéalement **1 000** pour couvrir secteurs, langues, aspects et alertes rares ;
- au moins 50 positifs par famille d'alerte critique quand cela est possible ;
- déduplication stricte entre train, DEV et TEST.

## 13. Stratégie de données recommandée

Séparer deux flux :

1. **distribution naturelle** : reflète les vrais commentaires et sert à mesurer
   la performance commerciale réelle ;
2. **curriculum équilibré** : renforce classes rares, code-switching, négations,
   sarcasme, absence d'information, alertes et secteurs sous-représentés.

Pour le SFT, commencer avec environ 70 % de distribution naturelle et 30 % de cas
ciblés, puis mesurer l'effet sur DEV. Les exemples synthétiques doivent être
filtrés par schéma, règles sémantiques, déduplication et revue stratifiée.

Un professeur frontier peut générer et critiquer les annotations, mais :

- le gold humain reste la référence ;
- les sorties du professeur ne deviennent pas automatiquement vraies ;
- les cas de désaccord et les classes rares doivent être sur-échantillonnés pour
  la revue ;
- le modèle étudiant apprend une trace de décision compacte suivie du JSON, pas
  une longue justification libre.

### Portefeuille de corpus algériens trouvé

La recherche ne justifie plus une dépendance au seul
`touati-kamel/algerian-darja-corpus`. Le meilleur portefeuille trouvé combine :

- 45 000 commentaires YouTube algériens, annotés manuellement en cinq sentiments
  et publiés sous CC BY 4.0 sur Mendeley ;
- 14 150 commentaires algériens annotés pour haine, cyberharcèlement et langage
  offensant, sous CC BY 4.0 ;
- 11 760 commentaires Facebook, YouTube et Twitter annotés en sentiment, avec
  une forte présence de latin et d'Arabizi, sous CC BY 4.0 ;
- NArabizi comme ancre de haute qualité pour l'Arabizi et le code-switching ;
- Touati et Ayoub pour l'adaptation linguistique, seulement après validation des
  droits des sources ;
- DzNER, de préférence à l'injection massive des patrons synthétiques
  d'ELNER-DZ, pour apprendre les entités.

Touati reste utile : 1 789 documents et 14,10 millions de tokens
Qwen3.5-0.8B. Il ne remplace cependant ni les annotations métier, ni les jeux
d'alertes et de sentiment. Sa provenance vidéo doit être confirmée avant usage
commercial.

Inventaire, audits, licences et mélange proposé :
`docs/slm_v2/INVENTAIRE_CORPUS_ALGERIENS_SLM_V2_2026-07-29.md`.

Audit du code et des méthodes open source PleIAs :
`docs/slm_v2/AUDIT_PLEIAS_OPEN_SOURCE_ADAPTATION_2026-07-29.md`.

Audit Touati détaillé :
`docs/slm_v2/AUDIT_ALGERIAN_DARJA_CORPUS_2026-07-29.md`.

## 14. Règle finale de sélection

Choisir **le plus petit modèle qui franchit toutes les portes critiques** sur le
TEST verrouillé et respecte les SLO sur le matériel final.

- Si 350M passe tout et sa licence est acceptable : produire l'édition ultra-edge.
- Sinon, si 0.6B ou 0.8B passe tout : choisir le plus petit des deux.
- Si les modèles edge échouent et 2B passe : produire avec 2B sur le profil hub
  et poursuivre la distillation vers 0.8B.
- Si 2B échoue aussi : améliorer d'abord les données et l'ontologie avant de
  monter à 4B/8B.

Augmenter la taille ne doit pas être la première réponse à des annotations
incohérentes ou à un benchmark trop petit.

## 15. Prochaine action

La prochaine étape n'est pas l'entraînement complet. C'est un **benchmark de
présélection reproductible** :

1. préparer un environnement Linux/WSL2 isolé ;
2. télécharger Qwen3.5-0.8B, Qwen3-0.6B, LFM2.5-350M/Extract,
   Qwen3.5-2B et le contrôle PleIAs 321M ;
3. exécuter la Phase A sur DEV ;
4. retenir trois modèles maximum ;
5. lancer un pilote QLoRA identique ;
6. produire la matrice qualité/latence/mémoire ;
7. décider du modèle avant la génération massive finale.

## Sources principales

- Brochure produit RamyPulse :
  `docs/LIDAL_AI_RamyPulse_Brochure (3).docx`
- PleIAs SYNTH :
  https://huggingface.co/datasets/PleIAs/SYNTH
- PleIAs, déploiements offline de juillet 2026 :
  https://pleias.ai/blog/local-ai-for-knowledge
- PleIAs-SLM-RAG, modèle Redline 321M :
  https://huggingface.co/PleIAs/Pleias-SLM-RAG
- Pleias-RAG-350M :
  https://huggingface.co/PleIAs/Pleias-RAG-350M
- Baguettotron 321M :
  https://huggingface.co/PleIAs/Baguettotron
- Dataset spécialisé BSF_Redline :
  https://huggingface.co/datasets/PleIAs/BSF_Redline
- Corpus linguistique algérien Touati Kamel :
  https://huggingface.co/datasets/touati-kamel/algerian-darja-corpus
- Qwen3, langues, tailles et licence :
  https://qwenlm.github.io/blog/qwen3/
- Qwen3.5-0.8B :
  https://huggingface.co/Qwen/Qwen3.5-0.8B
- Qwen3-0.6B :
  https://huggingface.co/Qwen/Qwen3-0.6B
- Qwen3.5-2B, repli qualité :
  https://huggingface.co/Qwen/Qwen3.5-2B
- Étude LoRA et extraction structurée, juin 2026 :
  https://arxiv.org/html/2606.08051v1
- Gemma 4 :
  https://ai.google.dev/gemma/docs/core/model_card_4
- LFM2.5-350M :
  https://huggingface.co/LiquidAI/LFM2.5-350M
- LFM2-350M-Extract :
  https://huggingface.co/LiquidAI/LFM2-350M-Extract
- vLLM, structured outputs et benchmark :
  https://docs.vllm.ai/en/stable/features/structured_outputs
  et https://docs.vllm.ai/en/stable/benchmarking/cli
- llama.cpp, grammaires et JSON Schema :
  https://github.com/ggml-org/llama.cpp
- LLaMA-Factory :
  https://github.com/hiyouga/LlamaFactory
