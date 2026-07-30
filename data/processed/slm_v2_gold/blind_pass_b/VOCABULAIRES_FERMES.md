# Vocabulaires fermes — business-comment-annotation v0.1.0

Extrait automatiquement du JSON Schema. AUCUNE valeur en dehors de ces listes.

## Racine

- `is_exploitable` : true | false
- `non_exploitable_reason` : null | hors_sujet | spam | texte_insuffisant | incomprehensible | langue_non_supportee | bruit_technique | ambiguite_majeure
- `business_relevance` : directe | indirecte | aucune
- `intents` (0 a 3) : avis | plainte | eloge | question | demande_information | demande_aide | suggestion | recommandation | comparaison | intention_achat | partage_experience | signalement_incident | appel_action | promotion_spam | tag_mention | autre

## language

- `dominant` : darija_arabe | darija_arabizi | arabe_msa | francais | anglais | tamazight_latin | tamazight_tifinagh | mixte | autre
- `detected` : darija | arabe_msa | francais | anglais | tamazight | autre
- `scripts` : arabe | latin | tifinagh | chiffres | autre
- `code_switching` : true | false

## entities (max 10)

- `type` : marque | organisation | produit | service | personne | lieu | concurrent | campagne | politique_publique | autre
- `source` : texte | contexte   (`texte` = ecrit dans le commentaire, `contexte` = deduit du contexte)

## sentiment

- `label` : negatif | neutre | positif | mixte
- `intensity` : faible | moyenne | forte
- `emotion` : satisfaction | admiration | joie | confiance | deception | frustration | colere | inquietude | peur | tristesse | degout | surprise | aucune | autre
- `sarcasm` : true | false

## aspects (max 8) — couples famille/attribut AUTORISES

- **produit_service** -> qualite_generale, performance, fiabilite, durabilite, fonctionnalite, design, gout, odeur, texture, fraicheur, emballage, quantite, hygiene, securite_produit, conformite_description
- **prix_valeur** -> prix, abordabilite, rapport_qualite_prix, promotion, transparence_prix, facturation
- **disponibilite_acces** -> stock, rupture, couverture_geographique, accessibilite, horaires, canal_achat
- **experience_client** -> satisfaction_globale, facilite, attente, accueil, comportement_personnel, personnalisation, fidelite
- **service_client_sav** -> reactivite, resolution, remboursement, garantie, traitement_reclamation, professionnalisme
- **livraison_logistique** -> delai_livraison, etat_reception, suivi_commande, distribution, approvisionnement
- **digital_technologie** -> application, site_web, ergonomie, bug, connexion_reseau, paiement, securite_donnees
- **communication_information** -> clarte, exactitude, transparence, publicite, promesse, information_manquante
- **confiance_reputation** -> confiance, credibilite, image_marque, authenticite, recommandation, comparaison_concurrent
- **operations_processus** -> efficacite, delai, procedure, coherence, continuite_service, capacite
- **emploi_management** -> recrutement, salaire, conditions_travail, management, formation, equite_interne
- **securite_conformite** -> securite, sante, hygiene, conformite_legale, fraude, confidentialite
- **ethique_impact** -> equite, discrimination, corruption, responsabilite_sociale, environnement, impact_local
- **marche_innovation** -> innovation, positionnement, concurrence, production_locale, import_export, tendance
- **infrastructure_service_public** -> infrastructure, transport, eau_energie, sante_publique, education, administration, couverture_territoriale

- aspect `sentiment` : negatif | neutre | positif | mixte
- aspect `intensity` : faible | moyenne | forte
- aspect `implicit` : true | false

## alerts (max 5)

- `type` : qualite_produit | securite_sante | fraude_arnaque | juridique_conformite | rupture_service | rupture_stock | reputation_virale | donnees_confidentialite | harcelement_discrimination
- `severity` : faible | moyenne | elevee | critique

## actionability

- `actionable` : true | false
- `queue` : produit | pricing | service_client | ventes | operations | logistique | digital | communication | rh | juridique_conformite | securite_qualite | direction | aucune
- `priority` : faible | moyenne | elevee | critique
