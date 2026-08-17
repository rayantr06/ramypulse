# Grille de revue experte — Gold candidat V0.1

## Statut du benchmark

Le benchmark est revu par un annotateur expert unique. Une ligne n'est acceptée que si son sens, ses catégories, ses citations et ses références sont cohérents. Le statut reste `single_reviewer_gold_candidate` jusqu'à une seconde annotation indépendante et une adjudication.

## Ordre de décision

### 1. Exploitabilité

Une annotation est exploitable lorsque le texte ou son contexte explicite permet une décision fiable.

- Un message court mais clair, comme « Ma limonade préférée », est exploitable.
- Une formule sociale sans objet business, comme une prière ou une salutation, est hors sujet.
- Un terme isolé ambigu n'est pas transformé en opinion uniquement grâce à un ancien label faible.
- Une marque connue par la collecte peut identifier la cible, mais ne suffit pas à inventer le produit, l'aspect ou le sentiment.

### 2. Pertinence business

- `directe` : évaluation, question, plainte, demande ou signalement visant une offre, une organisation, un service, une expérience ou un processus.
- `indirecte` : information de marché, contexte socio-économique, emploi, réputation sectorielle ou politique publique utile à la veille.
- `aucune` : aucun signal business fiable.

### 3. Sentiment

- Le sentiment porte sur la cible business réellement évaluée.
- Une question pure reste `neutre`, sauf formulation clairement critique ou élogieuse.
- `mixte` exige au moins un signal positif et un signal négatif dirigés vers la cible pertinente.
- Le sarcasme est activé uniquement lorsqu'un décalage entre le sens littéral et le sens visé est raisonnablement identifiable.
- Les anciens labels du corpus ne sont jamais une preuve.

### 4. Entités

- Une entité écrite dans le texte utilise `source=texte` et une mention exacte.
- Une marque fournie uniquement par la collecte utilise `source=contexte`.
- Un pays, une ville ou une région est un `lieu`.
- Une organisation, un produit ou une personne n'est jamais inféré sans preuve.
- Les noms d'utilisateurs et personnes taguées sans rôle dans l'opinion sont ignorés.

### 5. Intentions

Trois intentions maximum, en privilégiant :

1. l'action principale (`plainte`, `question`, `suggestion`, `signalement_incident`) ;
2. l'acte évaluatif (`avis`, `eloge`, `recommandation`) ;
3. le contexte expérientiel (`partage_experience`) s'il apporte une information distincte.

Une phrase déclarative n'est pas une `demande_information`.

### 6. Aspects

- Annoter le minimum d'aspects nécessaires pour représenter le sens explicite.
- Respecter strictement le couple famille/attribut.
- Ne pas créer un aspect à partir d'un mot isolé sans relation évaluative.
- Éviter deux aspects synonymes pour la même preuve.
- Un aspect implicite est autorisé seulement lorsque le jugement est évident.

Exemples de routage :

- promotion, concours, prix : `prix_valeur` ;
- procédure de participation : `operations_processus/procedure` ;
- ticket ou justificatif d'achat : `operations_processus/procedure` ou `communication_information/clarte`, selon le sens ;
- disponibilité d'une commande : `disponibilite_acces/stock` ;
- eaux usées et produit alimentaire : `securite_conformite/hygiene` et, si nécessaire, `produit_service/securite_produit` ;
- réseau mobile : `digital_technologie/connexion_reseau` ;
- disponibilité de médicaments : `disponibilite_acces/stock` ;
- recrutement et chômage : `emploi_management/recrutement`.

### 7. Alertes

Une alerte exige un risque concret :

- sécurité ou santé ;
- fraude ou arnaque ;
- rupture de service ou de stock notable ;
- risque juridique ;
- confidentialité ;
- harcèlement ou discrimination ;
- crise réputationnelle vraisemblablement virale.

Une mauvaise expérience ordinaire ne déclenche pas automatiquement une alerte.

Repères de sévérité :

- `faible` : signal limité, sans conséquence notable décrite ;
- `moyenne` : incident réel mais circonscrit ;
- `elevee` : risque sérieux pour plusieurs personnes ou continuité de service ;
- `critique` : danger grave, fraude majeure ou menace immédiate.

### 8. Preuves et offsets

- Toute preuve est une citation exacte et contiguë.
- Les offsets sont calculés par le pipeline, jamais acceptés sur la seule proposition du modèle.
- Une citation absente du commentaire invalide la ligne.
- Les preuves doivent être aussi courtes que possible sans perdre le sens.

## Contrôles avant acceptation

Chaque ligne doit satisfaire :

- schéma JSON V0.1 ;
- références d'entités existantes ;
- citations et offsets exacts ;
- absence de labels inventés ;
- absence de fuite des anciens labels faibles ;
- cohérence exploitabilité/pertinence/aspects/alertes ;
- justification de toute alerte ;
- note de revue explicite pour toute modification.

