# Décisions de contrat — V0.4

**Date** : 2026-08-11 · **Contrat précédent** : `business_comment_annotation_v0.3.schema.json`

## D12 — `hors_sujet` quitte les motifs de non-exploitabilité

### Ce qui a déclenché la décision

Le professeur `gemini-3-flash-preview` échouait quatre portes critiques mesurées contre le
gold V0.3. L'inspection des désaccords a montré que la cause n'était pas sa qualité.

Sur les 19 items où le gold disait `is_exploitable: false` et le professeur `true`, **les 19
portaient le motif `hors_sujet`** — des textes comme « جزاك الله خيراً » (que Dieu te
récompense) ou « نهاركم مبروك » (bonne journée).

Le professeur exprimait le même jugement dans un autre champ : `business_relevance: aucune`
sur 16 des 19, et aucun aspect sur 13.

### Pourquoi ce n'est pas anodin

Les deux encodages ne sont pas équivalents. Le schéma impose qu'`is_exploitable: false`
force `aspects` et `alerts` à rester vides. L'un jette le signal, l'autre le garde.

Sur 238 items de gold, **37 — 15,5 %** — étaient vides d'aspects par construction. Le
professeur, lui, n'a utilisé ce motif que **8 fois sur 13 505** avis Maps.

### Le principe qui tranche

Les six autres motifs décrivent tous **le texte lui-même** : `spam`, `texte_insuffisant`,
`incomprehensible`, `langue_non_supportee`, `bruit_technique`, `ambiguite_majeure`.

`hors_sujet` est le seul à décrire une **relation** entre le texte et l'entité surveillée —
ce que `business_relevance` encode déjà. Et il est indéfini en scope `espace_public`, où
aucune entité n'est surveillée : **13 des 19 désaccords s'y trouvaient**.

> `is_exploitable` porte sur le texte. `business_relevance` porte sur son rapport à ce
> qui est surveillé. Les confondre détruit du signal exploitable en veille sectorielle.

### Migration

37 items ré-encodés — `is_exploitable: true`, `non_exploitable_reason: null`,
`business_relevance: aucune`. Zéro invalide sous V0.4. Accord sur `is_exploitable` :
**103/122 avant, 121/122 après**.

Ce que la migration ne peut pas faire : retrouver les aspects que l'ancien encodage
interdisait. Ils n'ont jamais été annotés. Ces items portent `aspects_a_reannoter: true`
plutôt que d'être présentés comme complets.

## Deux constats de méthode, hors contrat

### La macro-F1 n'est pas interprétable sur les classes rares

Après migration, le gold compte 121 `is_exploitable: true` et 1 `false` ; le professeur
122 et 0. Ils s'accordent sur **121 des 122**, et la macro-F1 vaut **0,498** — la classe
minoritaire compte un item, sa F1 vaut 0, et la moyenne non pondérée tombe à la moitié.

Même artefact sur `author_role` : 2 erreurs sur 122, score 0,370.

Le banc reporte désormais l'accord brut et le support de la classe la plus rare à côté du
score. Sans ces deux chiffres, un artefact de mesure se lit comme un défaut de qualité —
et c'est ce qui s'est produit dans le premier rapport.

### Le professeur n'est pas déterministe

Deux passes du même modèle, même prompt, température 0, sur les mêmes 122 items :

| Champ | Identiques |
|---|---:|
| `author_role` | 98 % |
| `is_exploitable` | 97 % |
| `language` | 91 % |
| `sentiment` | **88 %** |

Quinze items sur 122 changent de sentiment d'une passe à l'autre. Une mesure de porte
conduite sur une seule passe porte donc une incertitude qui n'est pas chiffrée dans les
seuils actuels. À traiter avant d'affirmer qu'une porte est franchie.

## Question ouverte

Le gold marque **42 %** des items `neutre`, le professeur **27 à 32 %**. Le banc ne peut
pas trancher puisqu'il mesure contre le gold. L'arbitrage est confié à DziriBERT, qui ne
partage ni l'architecture ni les données des annotateurs LLM ayant produit le gold.
