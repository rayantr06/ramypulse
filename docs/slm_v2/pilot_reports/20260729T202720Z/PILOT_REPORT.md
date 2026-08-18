# Rapport du pilote — schéma business V0.1

## Verdict automatique

- Exécution : `20260729T202720Z`
- Fournisseur du pilote : `gemini`
- Modèle enseignant : `gemini-3.5-flash-lite`
- Échantillon : 24 commentaires stratifiés
- Réponses API : 23/24 (95.8%)
- Valides sans correction : 7/23 (30.4%)
- Valides après réalignement déterministe des offsets : 15/23 (65.2%)
- Sorties nécessitant un réalignement d'offset : 15/23 (65.2%)
- Latence moyenne / p95 : 1560 ms / 1909 ms
- Jetons totaux : 74450
- Accord avec les anciens labels faibles de sentiment : 17/23 (73.9%)

L'accord avec les anciens labels n'est pas une mesure d'exactitude : ces labels sont faibles et servent seulement de signal de divergence à revoir humainement.

## Couverture observée

- Pertinence business : `directe` 19, `indirecte` 2, `aucune` 2
- Sentiment : `negatif` 10, `neutre` 8, `positif` 5
- Langue dominante : `arabe_msa` 11, `darija_arabe` 7, `francais` 4, `anglais` 1
- Intentions : `avis` 10, `plainte` 8, `partage_experience` 7, `eloge` 5, `question` 4, `signalement_incident` 3, `suggestion` 2, `demande_aide` 1, `autre` 1, `appel_action` 1, `recommandation` 1
- Familles d'aspect : `produit_service` 7, `experience_client` 4, `prix_valeur` 3, `operations_processus` 2, `emploi_management` 2, `ethique_impact` 1, `securite_conformite` 1, `communication_information` 1, `confiance_reputation` 1, `disponibilite_acces` 1, `marche_innovation` 1, `infrastructure_service_public` 1, `digital_technologie` 1, `livraison_logistique` 1
- Alertes : `securite_sante` 2, `qualite_produit` 1, `rupture_stock` 1, `rupture_service` 1

## Échecs après validation finale

- seed `5715` : aspects.0.attribute: 'sante' is not one of ['equite', 'discrimination', 'corruption', 'responsabilite_sociale', 'environnement', 'impact_local']
- seed `6611` : aspects.0.attribute: 'facturation' is not one of ['efficacite', 'delai', 'procedure', 'coherence', 'continuite_service', 'capacite']
- seed `7013` : aspects.0.attribute: 'promotion' is not one of ['qualite_generale', 'performance', 'fiabilite', 'durabilite', 'fonctionnalite', 'design', 'gout', 'odeur', 'texture', 'fraicheur', 'emballage', 'quantite', 'hygiene', 'securite_produit', 'conformite_description']
- seed `7047` : aspects.1.attribute: 'sante' is not one of ['qualite_generale', 'performance', 'fiabilite', 'durabilite', 'fonctionnalite', 'design', 'gout', 'odeur', 'texture', 'fraicheur', 'emballage', 'quantite', 'hygiene', 'securite_produit', 'conformite_description']
- seed `7226` : intents: ['avis', 'plainte', 'partage_experience', 'signalement_incident'] is too long
- seed `236` : aspects.0.attribute: 'prix' is not one of ['innovation', 'positionnement', 'concurrence', 'production_locale', 'import_export', 'tendance'] ; aspects.1.attribute: 'production_locale' is not one of ['efficacite', 'delai', 'procedure', 'coherence', 'continuite_service', 'capacite'] ; entities.2.type: 'pays' is not one of ['marque', 'organisation', 'produit', 'service', 'personne', 'lieu', 'concurrent', 'campagne', 'politique_publique', 'autre']
- seed `1500` : API — JSONDecodeError: Invalid \uXXXX escape: line 1 column 525 (char 524)
- seed `5560` : aspects.1.attribute: 'qualite_generale' is not one of ['satisfaction_globale', 'facilite', 'attente', 'accueil', 'comportement_personnel', 'personnalisation', 'fidelite']
- seed `4381` : aspects.1.attribute: 'disponibilite_acces' is not one of ['delai_livraison', 'etat_reception', 'suivi_commande', 'distribution', 'approvisionnement']

## Corrections déterministes des offsets

- seed `5715` : 4 offset(s) réaligné(s)
- seed `6611` : 1 offset(s) réaligné(s)
- seed `6617` : 2 offset(s) réaligné(s)
- seed `7013` : 2 offset(s) réaligné(s)
- seed `7028` : 4 offset(s) réaligné(s)
- seed `7047` : 3 offset(s) réaligné(s)
- seed `7215` : 2 offset(s) réaligné(s)
- seed `7226` : 4 offset(s) réaligné(s)
- seed `7229` : 2 offset(s) réaligné(s)
- seed `0` : 2 offset(s) réaligné(s)
- seed `2` : 4 offset(s) réaligné(s)
- seed `236` : 6 offset(s) réaligné(s)
- seed `844` : 3 offset(s) réaligné(s)
- seed `5532` : 3 offset(s) réaligné(s)
- seed `5560` : 3 offset(s) réaligné(s)

## Fichiers

- Résultats détaillés : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T202720Z\pilot_results.jsonl`
- Manifeste de l'échantillon : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T202720Z\sample_manifest.jsonl`
- Schéma métier validé : `G:\ramypulse\docs\slm_v2\business_comment_annotation_v0.1.schema.json`

## Critère recommandé avant génération massive

Ne pas relancer les milliers d'exemples tant que :

1. 100 % des sorties ne passent pas le schéma final et les contrôles de citations ;
2. les divergences sémantiques n'ont pas été revues sur un échantillon humain ;
3. l'ontologie n'a pas été testée sur davantage de secteurs réels que le corpus actuel ;
4. le format d'entraînement final du SLM n'est pas figé séparément du format d'annotation.
