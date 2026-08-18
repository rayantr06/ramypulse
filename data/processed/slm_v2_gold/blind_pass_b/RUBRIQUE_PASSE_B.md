# Rubrique d'annotation — Passe B indépendante

Version : `blind_pass_b/0.1`
Contrat : `business-comment-annotation/0.1.0`

## Statut de ce document

Cette rubrique est dérivée de la grille de revue V0.1, **volontairement privée des
exemples de routage d'aspects** qui avaient été rédigés à partir des 100 commentaires
eux-mêmes. Les inclure ferait passer pour un accord entre annotateurs ce qui ne serait
qu'un alignement sur une consigne. Les principes généraux sont conservés intégralement.

## Ordre de décision

Traiter les champs dans cet ordre. Ne jamais remonter en arrière pour « faire coller »
une décision antérieure à une décision ultérieure.

### 1. Exploitabilité

Exploitable = le texte, ou le contexte de collecte explicite, permet une décision fiable.

- Un message court mais clair est exploitable.
- Une formule sociale sans objet business (prière, salutation, félicitation vide) est
  `hors_sujet`.
- Un terme isolé ambigu ne devient pas une opinion.
- Une marque connue par la collecte peut identifier la cible, mais ne suffit jamais à
  inventer un produit, un aspect ou un sentiment.
- Si non exploitable : aucun aspect, aucune alerte, `business_relevance = aucune`,
  sentiment `neutre` / `faible` / `aucune`.

### 2. Pertinence business

- `directe` : évaluation, question, plainte, demande ou signalement visant une offre,
  une organisation, un service, une expérience ou un processus.
- `indirecte` : information de marché, contexte socio-économique, emploi, réputation
  sectorielle ou politique publique utile à la veille.
- `aucune` : aucun signal business fiable.

### 3. Langue

- `dominant` = la langue qui porte la majorité du sens, pas la majorité des caractères.
- `darija_arabizi` = darija écrite en caractères latins/chiffres (3, 7, 9…).
- `code_switching = true` seulement si l'auteur alterne réellement entre deux langues
  porteuses de sens, pas pour un simple emprunt lexical isolé.

### 4. Entités

- Entité écrite dans le texte : `source = texte`, `mention` = citation exacte.
- Marque fournie uniquement par le contexte de collecte : `source = contexte`,
  `mention = null`.
- Pays, ville, région, wilaya : `lieu`.
- Ne jamais inférer une organisation, un produit ou une personne sans preuve.
- Ignorer les pseudonymes et personnes taguées qui ne jouent aucun rôle dans l'opinion.

### 5. Sentiment

- Le sentiment porte sur la cible business réellement évaluée, pas sur l'humeur générale
  du texte.
- Une question pure reste `neutre`, sauf formulation clairement critique ou élogieuse.
- `mixte` exige au moins un signal positif **et** un signal négatif dirigés vers la cible
  pertinente.
- `sarcasm = true` uniquement lorsqu'un décalage entre sens littéral et sens visé est
  raisonnablement identifiable dans le texte.

### 6. Intentions

Trois maximum. Priorité :

1. action principale (`plainte`, `question`, `suggestion`, `signalement_incident`) ;
2. acte évaluatif (`avis`, `eloge`, `recommandation`) ;
3. contexte expérientiel (`partage_experience`) s'il apporte une information distincte.

Une phrase déclarative n'est pas une `demande_information`.

### 7. Aspects

- Annoter le **minimum** d'aspects nécessaires pour représenter le sens explicite.
- Respecter strictement le couple famille/attribut autorisé.
- Ne pas créer un aspect à partir d'un mot isolé sans relation évaluative.
- Ne jamais poser deux aspects synonymes sur la même preuve.
- `implicit = true` seulement lorsque le jugement est évident sans être formulé.
- En cas d'hésitation entre deux familles, choisir celle qui décrit **ce sur quoi porte
  le jugement**, pas le domaine général du commentaire.

### 8. Alertes

Une alerte exige un **risque concret** :

sécurité ou santé · fraude ou arnaque · rupture de service ou de stock notable ·
risque juridique · confidentialité · harcèlement ou discrimination ·
crise réputationnelle vraisemblablement virale.

Une mauvaise expérience ordinaire, une plainte de prix ou un mécontentement banal
**ne déclenchent pas** d'alerte. En cas de doute : pas d'alerte.

Sévérité :

- `faible` : signal limité, aucune conséquence notable décrite ;
- `moyenne` : incident réel mais circonscrit ;
- `elevee` : risque sérieux pour plusieurs personnes ou pour la continuité de service ;
- `critique` : danger grave, fraude majeure ou menace immédiate.

### 9. Actionnabilité

- `actionable = true` seulement si une équipe peut réellement agir sur ce commentaire.
- `queue` = l'équipe la plus directement concernée par l'aspect dominant.
- `priority` suit la gravité réelle, pas l'intensité émotionnelle du texte.

### 10. Preuves

- Toute preuve est une **citation exacte et contiguë** copiée du commentaire.
- Aussi courte que possible sans perdre le sens.
- Ne jamais normaliser, corriger l'orthographe, retirer un emoji ni changer la casse.
- Une citation absente du commentaire invalide la ligne.
