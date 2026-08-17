# Registre de décisions — Schéma d'annotation V0.3

Date : 30 juillet 2026
Base factuelle : accord A3 vs C sur 305 items, contrat V0.2
([rapport](gold_v0.1/IAA_V0.2_A3_VS_C_2026-07-30.md))

## Méthode

Chaque correction a été **simulée sur les 305 annotations existantes** avant adoption,
puis vérifiée après migration. Aucune réannotation n'a été nécessaire. Deux règles
candidates ont été **rejetées** parce que la mesure les a démenties — elles sont
documentées ici au même titre que celles retenues.

## Résultat global

| Champ | V0.2 | V0.3 | Écart |
|---|---:|---:|---:|
| `alerts` type+sévérité | 0,304 | **0,783** | **+0,479** |
| `actionability.priority` | 0,706 | **0,907** | **+0,201** |
| `business_relevance` | 0,950 | 0,945 | −0,005 |
| `sentiment.label` | 0,855 | 0,851 | −0,004 |
| `aspects` famille+sentiment | 0,711 | 0,710 | −0,001 |
| `actionable` | 0,956 | 0,956 | 0 |
| `queue` | 0,840 | 0,840 | 0 |
| Validité mécanique | 305 et 304 | **305 et 305** | +1 |

Deux gains majeurs, aucune régression au-delà du bruit d'une paire supplémentaire.

---

## D10 — Sévérité d'alerte à trois niveaux

**Problème.** `alerts` type+sévérité plafonnait à F1 0,304 alors que le type seul
atteignait 0,783. Onze des dix-huit désaccords étaient `critique` contre `elevee` sur
un contenu quasi identique.

**Mesure préalable.** Variantes testées sur les annotations existantes :

| Variante | F1 |
|---|---:|
| Référence, 4 niveaux | 0,304 |
| Type seul, sévérité ignorée | 0,783 |
| `critique` fusionné dans `elevee` | **0,783** |
| Trois niveaux | **0,783** |
| Deux niveaux | **0,783** |

Toutes les variantes fusionnant `critique` et `elevee` atteignent exactement le score du
type seul. Autrement dit, **après la fusion, la sévérité ne coûte plus aucun désaccord**.
Une seule frontière de l'échelle était mauvaise.

**Décision.** `alert.severity ∈ {faible, moyenne, elevee}`. `critique` est retiré de
l'annotation.

**Vérifié après migration.** 0,304 → 0,783.

---

## D11 — La criticité devient un signal d'agrégat

**Constat.** Les onze items litigieux sont le même énoncé répété par une dizaine de
comptes : le tuyau d'irrigation serait branché sur les eaux usées. Un annotateur ne voit
qu'un commentaire à la fois. Il ne peut pas savoir qu'il fait partie d'une vague.

**Décision.** La criticité n'est plus un jugement par commentaire. `actionability.priority`
conserve quatre niveaux, et le pipeline escalade vers `critique` lorsqu'un même type
d'alerte se répète sur plusieurs commentaires dans une fenêtre.

**Justification.** C'est la bonne granularité : un commentaire isolé mentionnant des eaux
usées est `elevee` ; dix commentaires identiques en une heure sont une crise. Cette
information existe au niveau du flux, pas du commentaire.

**Vérifié après migration.** `priority` passe de κ 0,706 à **κ 0,907**, la dérivation
n'héritant plus du bruit de sévérité.

---

## D12 — Deux manques du vocabulaire, confirmés par les données

- **`gratitude`** ajouté aux émotions. Absent de la V0.2 alors que le registre du
  remerciement est fréquent dans ce corpus. Cette seule absence causait le dernier rejet
  de validité de la passe C.
- **`fidelite`** ajouté à `confiance_reputation`. Il n'existait que sous
  `experience_client` ; C l'y a placé dix-huit fois, ce qui indique que la notion
  appartient légitimement aux deux familles.

**Vérifié.** Les deux passes atteignent désormais 305/305 valides.

---

## D13 — Règle sémantique : accusation circulante contre incident rapporté

Une accusation non vérifiée qui circule dans plusieurs commentaires relève de
`reputation_virale`. `securite_sante` est réservé à un incident vécu ou rapporté de
première main.

**Statut particulier.** Cette règle est **neutre du point de vue de l'accord** : les deux
annotateurs codaient déjà ces items du même type. Elle ne corrige pas une divergence,
elle corrige une sémantique produit. La réponse métier est en effet opposée — rappel
produit d'un côté, réponse de communication de l'autre.

Elle n'a donc **pas pu être validée par la mesure** et doit être vérifiée lors de la
prochaine campagne.

---

## Règles REJETÉES par la mesure

Ces deux pistes semblaient raisonnables et ont été abandonnées après test. Les
documenter évite de les reproposer.

### R1 — Dériver `requires_parent_context` de la longueur du texte : rejeté

| Seuil | n | κ vs A3 | κ vs C |
|---:|---:|---:|---:|
| 15 | 18 | 0,280 | 0,287 |
| 20 | 36 | 0,253 | 0,238 |
| 30 | 66 | 0,229 | 0,141 |
| 50 | 151 | 0,147 | 0,074 |

Une règle déterministe donnerait un accord parfait par construction, mais elle
mesurerait autre chose que ce que les annotateurs entendent : elle ne les reproduit
qu'à 0,28 alors qu'ils s'accordent entre eux à 0,530.

### R2 — Dériver `requires_parent_context` d'un référent non résolu : rejeté

| Règle | n | κ vs A3 | κ vs C |
|---|---:|---:|---:|
| Démonstratif ou pronom sans antécédent | 25 | 0,062 | −0,004 |
| Démonstratif seul | 38 | 0,009 | −0,026 |
| Court et démonstratif | 2 | 0,051 | 0,123 |
| Court et sans entité citée | 45 | 0,289 | 0,151 |

L'hypothèse était plausible au vu des exemples. Elle est fausse.

### Conséquence

`requires_parent_context` reste un champ de jugement, non critique, plafonné à κ 0,530.

**Le correctif réel est en amont.** Ce champ n'existe que parce que le texte du post
parent a été jeté à la collecte. Vérification faite dans le code : le collecteur
Facebook capture `postUrl` mais pas le contenu du post
([facebook_apify.py:96](../../core/watch_runs/collectors/facebook_apify.py:96)). Capturer
ce texte supprimerait le problème plutôt que de l'annoter.

---

## Portes d'acceptation

Recalibrées sur les plafonds mesurés en V0.3 :
[acceptance_gates_v0.3.json](gold_v0.1/baselines/acceptance_gates_v0.3.json).

`alerts_type_severity` **redevient critique** avec un seuil de 0,68 : l'échelle à trois
niveaux atteint le même accord que le type seul.

## Ce qui reste ouvert

1. **22 à 24 alertes positives** seulement, sous la cible de 30. La porte d'alerte reste
   statistiquement fragile.
2. **Accord machine-machine** : A3 et C sont deux LLM. Une validation humaine reste
   requise avant production.
3. **Scope `secteur`** toujours non testé, faute de veille sectorielle réelle dans le corpus.
4. **Trois marques seulement**, toutes agroalimentaires. Tout le scope `organisation` est
   appris sur un seul secteur.
5. **D13 non validée** par la mesure.
