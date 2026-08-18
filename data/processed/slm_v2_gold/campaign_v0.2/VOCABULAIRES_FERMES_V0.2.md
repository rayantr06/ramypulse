# Vocabulaires fermes — business-comment-annotation v0.2.0

Extrait automatiquement du schema. AUCUNE valeur hors de ces listes.

## monitoring_target — FOURNI EN ENTREE, ne jamais le modifier

- `scope` : organisation | secteur | espace_public
- `entity_type` : null | marque | organisation | institution_publique | concurrent

## Racine

- `is_exploitable` : true | false
- `non_exploitable_reason` : null | hors_sujet | spam | texte_insuffisant | incomprehensible | langue_non_supportee | bruit_technique | ambiguite_majeure
- `business_relevance` : directe | indirecte | aucune
- `author_role` : consommateur | marque | moderateur | media | institution | inconnu
- `requires_parent_context` : true | false
- `intents` (0 a 3) : avis | plainte | eloge | question | demande_information | demande_aide | suggestion | recommandation | comparaison | intention_achat | partage_experience | signalement_incident | appel_action | promotion_spam | tag_mention | autre

## language

- `dominant` : darija_arabe | darija_arabizi | arabe_msa | francais | anglais | tamazight_latin | tamazight_tifinagh | mixte | autre
- `detected` : darija | arabe_msa | francais | anglais | tamazight | autre
- `scripts` : arabe | latin | tifinagh | chiffres | autre
- `code_switching` : true | false

## entities (max 10)

- `type` : marque | organisation | produit | service | personne | lieu | concurrent | campagne | politique_publique | autre
- `source` : texte | contexte

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
- **infrastructure_service_public** -> infrastructure, transport, eau_energie, sante_publique, education, administration, couverture_territoriale, degradation_entretien

- aspect `sentiment` : negatif | positif | mixte   <- AUCUN aspect neutre en V0.2
- aspect `intensity` : faible | moyenne | forte
- aspect `implicit` : true | false
- aspect `attribute` : OPTIONNEL en V0.2. Omets-le si tu hesites.

## alerts (max 5)

- `type` : qualite_produit | securite_sante | fraude_arnaque | juridique_conformite | rupture_service | rupture_stock | reputation_virale | donnees_confidentialite | harcelement_discrimination
- `severity` : faible | moyenne | elevee | critique

## actionability — NE PAS PRODUIRE

Bloc entierement DERIVE par le pipeline en V0.2. Ne l'inclus pas dans ta sortie.

