# RamyPulse SLM V2 — inventaire professionnel des corpus algériens

Date de recherche : 29 juillet 2026  
Périmètre : Darija algérienne, Arabizi, code-switching arabe–français–anglais,
sentiment, aspects métier, alertes, entités et, en seconde phase, kabyle  
Objectif : sélectionner des données réellement utiles à un SLM commercial
d'analyse de commentaires business

## 1. Conclusion exécutive

Le corpus `touati-kamel/algerian-darja-corpus` est intéressant, mais il n'est ni
le seul ni le meilleur corpus pour toutes les composantes de RamyPulse. La
meilleure stratégie est un **portefeuille de corpus spécialisés**, séparé en
trois couches :

1. **adaptation linguistique** : Darija, Arabizi et code-switching ;
2. **apprentissage supervisé des capacités** : sentiment, toxicité, entités ;
3. **gold RamyPulse** : schéma métier final, aspects, intentions, alertes,
   preuves et résumé.

Les découvertes les plus utiles sont :

- un corpus de **45 000 commentaires YouTube algériens annotés manuellement en
  cinq niveaux de sentiment**, sous CC BY 4.0 ;
- un corpus de **14 150 commentaires algériens** annotés pour discours haineux,
  cyberharcèlement et langage offensant, sous CC BY 4.0 ;
- un second corpus de **11 760 commentaires Facebook, YouTube et Twitter**
  annotés en sentiment et contenant beaucoup d'Arabizi, sous CC BY 4.0 ;
- NArabizi, petit mais de très haute qualité, pour l'Arabizi et le
  code-switching ;
- plusieurs corpus NER et parallèles, utiles avec des réserves de qualité ou de
  licence.

La recommandation est donc de **ne pas reprendre la génération synthétique
ancienne** et de ne pas entraîner immédiatement. Il faut d'abord construire un
registre de provenance, nettoyer et dédupliquer ces sources, puis mesurer leur
complémentarité avec le gold RamyPulse.

## 2. Sélection prioritaire

| Priorité | Ressource | Volume vérifié ou publié | Licence déclarée | Valeur pour RamyPulse | Décision |
|---|---|---:|---|---|---|
| P0 | Algerian Dialect — Mendeley | 45 000 commentaires, 5 sentiments | CC BY 4.0 | Commentaires sociaux algériens, sentiment fin, métadonnées | Télécharger l'original et auditer |
| P0 | AlgD Toxicity Speech | 14 150 commentaires, 3 familles d'alertes | CC BY 4.0 | Haine, cyberharcèlement, langage offensant | Intégrer après nettoyage |
| P0 | Sentiment dataset of Algerian dialect | 11 760 commentaires, sentiment binaire | CC BY 4.0 | Arabe, latin, Arabizi et code-switching | Intégrer après correction |
| P0 | NArabizi / UD Arabizi | 1 287–1 500 phrases gold + 50 000 non annotées | CC BY-SA 4.0 pour le treebank actuel | Ancre de qualité Arabizi, morphosyntaxe, traduction | Réserver une partie au test |
| P0 | Gold RamyPulse | volume à consolider | propriétaire | Contrat JSON, aspects, intentions, preuves | Source centrale du SFT |
| P1 | AfriSenti algérien | 3 023 tweets dans la version auditée | CC BY 4.0 | Benchmark sentiment algérien indépendant | Garder surtout en évaluation |
| P1 | Touati Algerian Darja Corpus | 14,10 M tokens Qwen3.5-0.8B | CC BY 4.0 déclarée | Adaptation linguistique longue | Bloqué jusqu'à preuve de provenance |
| P1 | Ayoub Algerian-Darija | 168 655 lignes, 4,79 M tokens Qwen | CC BY 4.0 déclarée | Commentaires et transcriptions réelles | Utiliser avec filtrage et audit des sources |
| P1 | DzNER | >21 000 phrases, >220 000 tokens, annotation humaine | article ouvert ; licence des données à confirmer | Personnes, lieux, organisations | Obtenir l'archive et ses termes |
| P1 | Awras Dictionary v1 | 4 636 entrées | CC BY 4.0 | Glossaire, variantes et définitions | Nettoyage humain avant usage |
| P2 | ELNER-DZ | 2 075 148 phrases | CC BY 4.0 | NER/liaison Wikidata, Arabizi | N'utiliser qu'en tâche NER et très sous-échantillonné |
| P2 | CALYOU | 5,19 k paires fortes + 38,5 k comparables | GPL-3.0 déclaré au dépôt | Arabizi/latin vers écriture arabe | Revue de compatibilité juridique |
| P2 | DziriAlign | 1 000 paires de préférence | licence incohérente ou absente | Culture, humour, sociolinguistique | Audit avant un éventuel alignement |

## 3. Audits réalisés

### 3.1 Corpus de sentiment YouTube à cinq niveaux

Source originale :
[Algerian Dialect, Mendeley Data](https://data.mendeley.com/datasets/zzwg3nnhsz/2)  
Article :
[Algerian Dialect](https://arxiv.org/abs/2512.19543)

L'original annonce :

- 45 000 commentaires YouTube ;
- plus de 30 chaînes algériennes de presse et médias ;
- annotation manuelle en `very_negative`, `negative`, `neutral`, `positive` et
  `very_positive` ;
- date de collecte, nombre de likes, URL de la vidéo et date d'annotation ;
- licence CC BY 4.0.

Le miroir
[`Abdou/dz-sentiment-yt-comments`](https://huggingface.co/datasets/Abdou/dz-sentiment-yt-comments)
contient 50 016 lignes et seulement trois classes. Notre audit du miroir donne :

- 50 010 textes uniques et 6 doublons exacts ;
- 637 670 mots, médiane de 8 mots et P95 de 35 mots ;
- 43 614 lignes avec caractères arabes ;
- 7 814 lignes avec caractères latins ;
- environ 2 296 lignes détectées par une heuristique Arabizi simple ;
- classes : 17 033 négatives, 11 136 neutres et 21 847 positives.

La différence **45 000/5 classes contre 50 016/3 classes** doit être résolue.
L'original Mendeley est la référence ; le miroir n'est qu'un moyen d'accès
pratique après vérification de sa transformation et de sa provenance.

### 3.2 Corpus algérien de toxicité et d'alertes

Source :
[Algerian Dialect Dataset — Targeted Hate Speech, Offensive Language and Cyberbullying](https://zenodo.org/records/10937445)

Audit du fichier XLSX :

- 14 150 commentaires et 14 139 textes uniques ;
- 11 doublons exacts, aucune cellule de commentaire vide ;
- 314 316 mots, médiane de 18 mots, P95 de 46 mots ;
- sources : 8 356 YouTube, 5 579 Facebook et 215 Twitter ;
- `hate_speech=yes` : 7 574 ;
- `cyberbullying=yes` : 4 531 ;
- `offensive_language=yes` : 5 768 ;
- 13 396 commentaires avec caractères arabes ;
- 1 096 avec caractères latins ;
- 341 détectés par une heuristique Arabizi simple.

Les sujets couvrent notamment misogynie, politique, religion, hausse des prix,
drogues et migration irrégulière. La licence CC BY 4.0 permet un usage
commercial avec attribution. Ce corpus est beaucoup plus pertinent pour les
alertes RamyPulse qu'une synthèse générique.

Il ne faut cependant pas recopier ses trois booléens tels quels dans le schéma
RamyPulse. Ils servent de tâches auxiliaires et doivent être mappés vers
`abuse_or_hate`, `harassment` et `toxic_language`, avec une revue des cas
ambigus.

### 3.3 Corpus de sentiment Hirak 2019

Source :
[Sentiment dataset of Algerian dialect](https://zenodo.org/records/10937412)

La publication annonce 11 760 commentaires Facebook, YouTube et Twitter :
6 111 positifs et 5 649 négatifs, en arabe, latin, Arabizi, français et Darija.
Licence CC BY 4.0.

Notre audit du fichier révèle :

- 11 659 textes uniques et 101 doublons exacts ;
- 205 752 mots, médiane de 13 mots et P95 de 44 mots ;
- 4 641 lignes contenant de l'arabe ;
- 8 167 lignes contenant des caractères latins ;
- environ 1 539 lignes détectées par une heuristique Arabizi simple ;
- une ligne mal formée (`1777007863`) ;
- 5 649 négatifs et 6 110 positifs effectivement lisibles, la ligne mal formée
  expliquant l'écart avec le total publié.

Le domaine politique crée un biais. Ce corpus doit apprendre la langue et une
polarité auxiliaire, pas définir à lui seul le sentiment business.

### 3.4 `ayoubkirouane/Algerian-Darija`

Source :
[`ayoubkirouane/Algerian-Darija`](https://huggingface.co/datasets/ayoubkirouane/Algerian-Darija)

Audit intégral de la version à 168 655 lignes :

- 167 321 textes uniques et 1 334 doublons ;
- 2 580 768 mots ;
- 4 792 093 tokens avec le tokenizer Qwen3.5-0.8B ;
- médiane de 19 tokens, P95 de 60 tokens ;
- 139 435 textes avec arabe, 38 555 avec latin ;
- présence de spam, de langues non algériennes, d'erreurs ASR et de commentaires
  concaténés.

La carte cite des datasets existants, du scraping web, des commentaires et des
transcriptions YouTube, sans source par ligne. La licence CC BY 4.0 déclarée ne
suffit donc pas, à elle seule, à prouver le droit de relicencier chaque texte.

### 3.5 `touati-kamel/algerian-darja-corpus`

Source :
[`touati-kamel/algerian-darja-corpus`](https://huggingface.co/datasets/touati-kamel/algerian-darja-corpus)

Audit détaillé dans
[`AUDIT_ALGERIAN_DARJA_CORPUS_2026-07-29.md`](./AUDIT_ALGERIAN_DARJA_CORPUS_2026-07-29.md).

Résultat :

- 1 789 documents ;
- 6,39 millions de mots ;
- 14,10 millions de tokens Qwen3.5-0.8B ;
- 32 121 fenêtres de 512 tokens avec recouvrement de 64 ;
- contenu utile sur société, entrepreneuriat et e-commerce ;
- artefacts ASR et provenance vidéo non fournie par ligne.

Décision : bon candidat de continued pretraining, mais **usage commercial
bloqué** jusqu'à confirmation des droits sur les transcriptions sources.

### 3.6 NArabizi

Sources :

- [projet NArabizi](https://parsiti.github.io/NArabizi/) ;
- [article ACL 2020](https://aclanthology.org/2020.acl-main.107/) ;
- [treebank UD actuel](https://universaldependencies.org/treebanks/qaf_arabizi/index.html).

La ressource historique contient 1 500 phrases intégralement annotées, avec
morphosyntaxe, dépendances et traductions mot à mot et phrase à phrase, plus
50 000 phrases non annotées collectées sur le Web. Le treebank UD actuel compte
1 287 phrases, 18 561 tokens et 19 793 mots syntaxiques, sous CC BY-SA 4.0.

Il s'agit d'une petite ressource, mais probablement de la meilleure ancre
publique pour l'Arabizi algérien réel. Une partie doit rester totalement hors
entraînement afin de mesurer la généralisation.

### 3.7 NER : DzNER contre ELNER-DZ

Sources :

- [DzNER](https://www.sciencedirect.com/science/article/pii/S294971912300002X) ;
- [ELNER-DZ sur Zenodo](https://zenodo.org/records/15798592) ;
- [`HadjerHaninebgt7878/ELNER-DZ`](https://huggingface.co/datasets/HadjerHaninebgt7878/ELNER-DZ).

DzNER annonce plus de 21 000 phrases et 220 000 tokens annotés manuellement à
partir de Facebook et YouTube. Il est, en principe, préférable pour apprendre
les trois entités fondamentales : personne, organisation et lieu. La licence
exacte et l'archive de données doivent toutefois être récupérées et vérifiées.

ELNER-DZ contient plus de deux millions de phrases et 1,9 million d'entités liées
à Wikidata. Notre inspection à plusieurs positions du dataset montre qu'une
grande majorité est issue de patrons synthétiques très répétitifs. Quelques
premières lignes ressemblent à des commentaires Arabizi naturels, mais de
larges zones répètent des patrons autour d'une même loi, saison de football,
organisation, personne ou date.

Décision :

- DzNER : priorité à l'annotation humaine, si l'accès et les droits sont clairs ;
- ELNER-DZ : tâche auxiliaire NER seulement, forte déduplication, contrôle par
  entité et sous-échantillonnage ; jamais deux millions de lignes injectées
  aveuglément dans le modèle de langue.

## 4. Ressources intéressantes sous réserve

| Ressource | Contenu | Réserve | Usage recommandé |
|---|---|---|---|
| [FASSILA](https://github.com/amincoding/FASSILA) | 10 087 phrases, sentiment et fake news, 7 domaines | pas de licence explicite dans le dépôt inspecté | évaluation/R&D ou permission écrite |
| [Corpus opinion–émotion LREC 2020](https://aclanthology.org/2020.lrec-1.328/) | >36 000 UGC code-switchés, sentiment et lexiques | archive et licence à obtenir | priorité de contact élevée |
| [TWIFIL](https://aclanthology.org/2020.lrec-1.151/) | 9 000 tweets sentiment, ~5 000 émotion, lexique de 9 000 entrées | disponibilité et licence à confirmer | utile pour émotions et intensité |
| [Corpus multi-couches](https://arxiv.org/abs/2105.07400) | écritures arabe/latine, code-switching, sujet et sentiment | accès à localiser | normalisation et classification |
| [SentiALG](https://arxiv.org/abs/1808.05079) | 8 000 messages arabe/Arabizi | étiquettes automatiques | données faibles, poids faible |
| [Sexism detection](https://arxiv.org/abs/2104.01443) | 5 000 commentaires annotés par 3 personnes | archive/licence non localisées | permission, puis alerte misogynie |
| [Fine-grained hate speech](https://aclanthology.org/2024.rail-1.15/) | misogynie algérienne, 13 classes et désaccords | accès/licence à confirmer | excellent pour taxonomie fine |
| [CALYOU](https://github.com/abidikarima/CALYOU) | latin/Arabizi vers arabe | GPL-3.0 ; compatibilité dataset/modèle à revoir | normalisation et translittération |
| [PADIC](https://smart.loria.fr/corpora/) | dialectes d'Alger et Annaba alignés au MSA | conditions précises à vérifier | traduction et normalisation |

## 5. Ressources à ne pas utiliser dans le produit sans autorisation

| Ressource | Motif |
|---|---|
| [BOUTEF](https://huggingface.co/datasets/TeamSmart/BOUTEF) | accord contrôlé réservé à la recherche et à l'éducation non commerciales |
| [MADAR](https://camel.abudhabi.nyu.edu/madar-parallel-corpus/) | usage interne de recherche/évaluation ; licence commerciale séparée |
| [MADOran](https://data.mendeley.com/datasets/pgr766jbhp/2) | CC BY-NC 3.0, donc non commercial |
| livres modernes et dictionnaires sous droit d'auteur | l'accès en lecture n'accorde pas le droit d'entraîner un modèle commercial |
| corpus sans licence explicite | « public sur GitHub » ne signifie pas « autorisé pour le commercial » |

Les livres anciens en accès intégral, tels que
[`L'idiome d'Alger` (1838)](https://books.google.com/books/about/L_idiome_d_Alger.html?id=n7e_XBSdnlIC),
le
[`Dictionnaire français-arabe, idiome parlé en Algérie` (1850)](https://books.google.com/books/about/Dictionaire_fran%C3%A7ais_arabe_idiome_parl.html?id=TRVFAAAAYAAJ)
et la
[`Grammaire arabe, idiome d'Algérie` (1865)](https://books.google.com/books/about/Grammaire_arabe_idiome_d_Alg%C3%A9rie_a_l_us.html?id=-yi51IOeH_YC)
peuvent aider à créer un lexique historique ou des tests. Ils ne reflètent ni la
Darija 2026, ni les produits, ni le code-switching actuel. Il faut aussi vérifier
le statut de domaine public dans les juridictions de diffusion.

## 6. Kabyle et Tamazight : phase 2, pas mélange immédiat

Pour un produit réellement algérien, le kabyle a une valeur commerciale réelle.
Il doit toutefois être traité comme une capacité identifiable, avec ses propres
tests, et non mélangé sans contrôle à la Darija.

Ressources repérées :

- [`kabyle-corpus-ummto`](https://huggingface.co/datasets/Imsidag-community/kabyle-corpus-ummto) :
  690 917 segments extraits de PDF universitaires, CC BY-SA 4.0 déclarée, mais
  corpus non nettoyé et droits des documents sources à auditer ;
- `kabyle-corpus-ubouira` et `kabyle-corpus-hca` : autres grands corpus de la
  communauté Imsidag, à auditer séparément ;
- [`kabyle-sentiments-corpus`](https://huggingface.co/datasets/michsethowusu/kabyle-sentiments-corpus) :
  4 887 phrases, MIT, mais labels projetés automatiquement depuis leur traduction
  anglaise ;
- [`kabyle-emotions-corpus`](https://huggingface.co/datasets/michsethowusu/kabyle-emotions-corpus) :
  les mêmes 4 887 phrases, 7 émotions projetées automatiquement ;
- corpus parallèles latin–tifinagh et Common Voice : utiles pour une future
  brique dédiée après audit.

Recommandation : lancer la V2 en Darija/arabe/français/Arabizi, instrumenter la
détection de langue, puis ajouter une édition kabyle avec un gold natif revu par
des locuteurs. Les labels automatiques kabyles ne doivent pas servir de gold.

## 7. Ressources hors Algérie

Le petit
[`ohidaoui/darija-reviews`](https://huggingface.co/datasets/ohidaoui/darija-reviews)
est particulièrement intéressant sur le plan métier : 851 avis de produits et
services, trois sentiments, secteurs et styles arabe/Arabizi. Ses exemples et
son vocabulaire sont toutefois marocains.

Décision : ne pas l'ajouter au train Darija algérienne initial. Il peut servir de
test hors domaine pour vérifier que le modèle ne confond pas « Darija
maghrébine » et « Darija algérienne », ou comme source de conception des cas
métier après réannotation algérienne indépendante.

## 8. Mélange d'entraînement recommandé

### Étape A — registre et nettoyage

Créer pour chaque ligne :

- `dataset_id`, version, URL et hash du fichier ;
- licence déclarée et licence vérifiée ;
- source originale et plateforme ;
- type humain, brut, pseudo-étiqueté ou synthétique ;
- domaine, écriture, langue et région si connue ;
- statut `train_allowed`, `eval_only`, `permission_required` ou `rejected`.

Ensuite :

- supprimer doublons exacts et quasi-doublons à travers **tous** les corpus ;
- éliminer PII, liens, spam, concaténations et textes hors Algérie ;
- conserver une trace réversible de chaque filtre ;
- calculer le chevauchement avec DEV et TEST avant entraînement.

### Étape B — adaptation linguistique éventuelle

Une courte adaptation linguistique n'est justifiée que si le benchmark zero-shot
du modèle de base montre un vrai déficit Darija/Arabizi.

Entrées possibles :

- Touati et Ayoub après validation des droits et nettoyage ;
- 50 000 phrases non annotées NArabizi ;
- texte seul des corpus CC BY, sans répliquer leurs labels comme vérité métier ;
- un replay contrôlé en arabe et français pour éviter l'oubli.

Ne pas injecter les deux millions de patrons ELNER-DZ dans cette étape.

### Étape C — SFT multitâche

1. gold RamyPulse pour la sortie canonique complète ;
2. sentiment à cinq niveaux du corpus Mendeley, mappé vers le schéma après étude ;
3. toxicité pour les alertes auxiliaires ;
4. NER humain pour personnes, organisations et lieux ;
5. exemples Arabizi/normalisation ;
6. synthèse ciblée uniquement pour les trous de couverture prouvés.

Chaque source doit avoir son propre prompt et son propre objectif. Les anciens
labels ne doivent pas être transformés artificiellement en annotations RamyPulse
riches si l'information n'existe pas.

### Étape D — évaluation verrouillée

Préserver des tests sans chevauchement :

- commentaires business RamyPulse revus humainement ;
- Arabizi NArabizi ;
- sentiment AfriSenti ou Mendeley tenu à l'écart ;
- toxicité séparée par plateforme ou sujet ;
- cas hors domaine marocains ;
- futur test kabyle natif.

## 9. Décision proposée

Le prochain travail de données doit porter sur quatre acquisitions seulement :

1. télécharger et vérifier le **Mendeley 45k original** ;
2. normaliser les corpus **toxicité 14 150** et **sentiment 11 760** ;
3. intégrer **NArabizi** comme ancre Arabizi et benchmark ;
4. construire un **registre de provenance et de déduplication global** incluant
   le gold RamyPulse, Touati et Ayoub.

Après cela, un rapport de couverture dira objectivement :

- quelles valeurs du schéma sont déjà couvertes ;
- quelles alertes et quels secteurs manquent ;
- combien d'exemples synthétiques sont réellement nécessaires ;
- si un continued pretraining linguistique apporte plus qu'un SFT propre.

Cette séquence maximise la qualité et réduit à la fois le coût, le risque
juridique et la contamination du benchmark.
