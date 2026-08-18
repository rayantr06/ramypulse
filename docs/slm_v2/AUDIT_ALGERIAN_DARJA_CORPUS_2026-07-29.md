# Audit — `touati-kamel/algerian-darja-corpus`

Date de l'audit : 29 juillet 2026  
Source : https://huggingface.co/datasets/touati-kamel/algerian-darja-corpus  
Révision auditée : `69ce4e4970e69d08d5623215a940e7910433f4c5`  
Licence déclarée : CC BY 4.0  
Décision : **retenu pour R&D et adaptation linguistique, sous quarantaine de
provenance avant utilisation commerciale**

## 1. Résumé exécutif

Ce corpus est une découverte importante pour RamyPulse. Il ne contient pas des
annotations business, mais de longues transcriptions algériennes naturelles :
podcasts, interviews, récits et conversations avec arabe, darija, français,
anglais et arabizi.

Le bon usage n'est pas le SFT d'annotation. Le corpus doit servir à une courte
phase de **continued pretraining / language-adaptive training**, avant le SFT
sur les commentaires business annotés.

Sa taille est suffisante pour mesurer un effet linguistique réel sur un SLM de
350–800M, mais elle reste très inférieure aux volumes utilisés pour pré-entraîner
un modèle général. Elle doit donc adapter un modèle existant, pas entraîner un
SLM à partir de zéro.

## 2. Mesures vérifiées

Audit effectué sur le JSONL complet téléchargé depuis la révision indiquée.

| Mesure | Résultat |
|---|---:|
| Documents JSONL | 1 789 |
| JSON invalides | 0 |
| Taille du fichier | 63 860 225 octets |
| SHA-256 | `9A67B520F45CA1C2C99FB3004C13104A2F218AD20DEB1B33F3358A758A363585` |
| Caractères réels | 36 217 669 |
| Mots par séparation d'espaces | 6 386 960 |
| Tokens Qwen3.5-0.8B | **14 095 909** |
| Ratio tokens/mot | 2,207 |
| Documents doublons exacts normalisés | 2 paires |
| Fenêtres 512 tokens, chevauchement 64 | 32 121 |
| Tokens effectifs avec chevauchement | 16 037 157 |

Longueur des documents :

| Mesure | Mots | Tokens Qwen3.5 |
|---|---:|---:|
| Moyenne | 3 570 | 7 879 |
| Médiane | 2 309 | 5 201 |
| P95 | 10 870 | 24 350 |
| Maximum | 107 128 | 211 243 |

Les documents sont beaucoup trop longs pour être consommés directement par le
SLM. Le découpage est obligatoire.

## 3. Valeur linguistique

- 1 750 documents contiennent de l'écriture arabe ;
- 1 201 contiennent des caractères latins ;
- 611 contiennent à la fois plus de 100 caractères arabes et 100 caractères
  latins ;
- 121 contiennent des formes arabizi avec chiffres détectables ;
- environ 93,9 % des caractères alphabétiques arabe/latin détectés sont en
  écriture arabe ;
- les thèmes incluent entrepreneuriat, commerce électronique, voyages, société,
  technologie, récits personnels et culture.

Le corpus complète bien les commentaires RamyPulse :

- il apporte des phrases longues et du contexte ;
- il expose le modèle à la syntaxe orale algérienne ;
- il contient du code-switching réel ;
- plusieurs sources portent sur le business algérien ;
- il améliore potentiellement la compréhension avant l'apprentissage du schéma
  d'annotation.

## 4. Problèmes de qualité observés

Le corpus est exploitable, mais pas prêt à entraîner :

- 702 documents contiennent des frontières arabe/latin collées sans espace,
  pour 12 319 occurrences détectées ;
- la médiane du nombre de retours à la ligne est zéro : les tours de parole sont
  souvent perdus ;
- certains documents concatènent plusieurs heures ou épisodes ;
- des erreurs de transcription phonétique et des répétitions sont visibles ;
- 125 documents contiennent des formes ressemblant à des timestamps ;
- 277 documents contiennent des séquences numériques longues à auditer comme
  PII potentielles ;
- `char_count` ne correspond pas au texte dans 1 008 documents et `word_count`
  dans 981 documents ;
- chaque objet ne contient que `text`, `char_count` et `word_count` : aucune URL,
  chaîne, émission, date ou identité de source par document.

Les compteurs fournis ne doivent donc pas être utilisés. Ils doivent être
recalculés après nettoyage.

## 5. Risque de licence et provenance

La carte déclare CC BY 4.0, licence qui autorise normalement l'usage commercial
avec attribution. Cependant, le corpus est constitué de transcriptions provenant
de nombreuses chaînes YouTube et de trois autres datasets audio.

Avant un modèle commercial :

1. demander à l'auteur comment les transcriptions ont été produites ;
2. confirmer qu'il possède le droit de redistribuer et relicencier les textes ;
3. obtenir la correspondance document → vidéo/dataset source ;
4. vérifier les licences des contenus sources ;
5. définir l'attribution requise ;
6. supprimer ou masquer les informations personnelles éventuelles.

En attendant, le corpus peut être évalué en R&D, mais il ne doit pas entrer dans
le modèle de production sans cette vérification.

## 6. Pipeline recommandé

1. figer la révision et conserver le SHA-256 ;
2. supprimer les deux paires de doublons exacts ;
3. retrouver ou reconstruire la provenance de chaque document ;
4. supprimer publicités, génériques, appels à s'abonner et répétitions ASR ;
5. corriger uniquement les espaces et artefacts manifestes sans normaliser la
   darija authentique ;
6. détecter et masquer téléphones, e-mails, adresses et identifiants ;
7. segmenter par tours de parole quand c'est possible ;
8. découper en fenêtres de 384–512 tokens avec 32–64 tokens de recouvrement ;
9. dédupliquer les fenêtres par MinHash ou équivalent ;
10. produire un split par source, jamais un split aléatoire de fenêtres ;
11. réserver un jeu de validation linguistique distinct ;
12. entraîner avec un faible taux d'apprentissage et mesurer la régression sur
    le suivi d'instruction et les sorties structurées.

## 7. Expérience RamyPulse proposée

Comparer, pour Qwen3.5-0.8B et Qwen3-0.6B :

- **A — baseline** : SFT métier uniquement ;
- **B — adaptation darija** : continued pretraining sur le corpus nettoyé, puis
  le même SFT métier ;
- **C — adaptation avec replay** : corpus darija majoritaire + petit mélange
  arabe/français général, puis le même SFT.

Évaluer ensuite :

- perplexité sur darija tenue à l'écart ;
- compréhension de l'arabizi et du code-switching ;
- exactitude des offsets de preuve ;
- F1 sentiment, intentions, aspects et alertes ;
- validité du format filaire ;
- oubli du français, de l'arabe standard et du suivi d'instruction ;
- latence CPU et taille GGUF finale.

La variante B ou C n'est retenue que si elle améliore la langue sans dégrader les
portes métier.

