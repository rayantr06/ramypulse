# Rapport du pilote — schéma business V0.1

## Verdict automatique

- Exécution : `20260729T203516Z`
- Fournisseur du pilote : `gemini`
- Modèle enseignant : `gemini-3.5-flash-lite`
- Échantillon : 100 commentaires stratifiés
- Réponses API : 97/100 (97.0%)
- Valides sans correction : 13/97 (13.4%)
- Valides après réalignement déterministe des offsets : 89/97 (91.8%)
- Sorties nécessitant un réalignement d'offset : 84/97 (86.6%)
- Latence moyenne / p95 : 1648 ms / 2247 ms
- Jetons totaux : 552488
- Accord avec les anciens labels faibles de sentiment : 70/97 (72.2%)

L'accord avec les anciens labels n'est pas une mesure d'exactitude : ces labels sont faibles et servent seulement de signal de divergence à revoir humainement.

## Couverture observée

- Pertinence business : `directe` 67, `indirecte` 28, `aucune` 2
- Sentiment : `negatif` 40, `neutre` 31, `positif` 25, `mixte` 1
- Langue dominante : `darija_arabe` 46, `arabe_msa` 35, `francais` 11, `mixte` 4, `darija_arabizi` 1
- Intentions : `avis` 51, `plainte` 26, `eloge` 23, `partage_experience` 21, `question` 19, `suggestion` 13, `signalement_incident` 7, `demande_information` 7, `demande_aide` 6, `recommandation` 5, `comparaison` 3, `appel_action` 2, `information_manquante` 1, `autre` 1
- Familles d'aspect : `produit_service` 18, `infrastructure_service_public` 14, `disponibilite_acces` 8, `communication_information` 8, `prix_valeur` 8, `emploi_management` 8, `experience_client` 7, `digital_technologie` 6, `securite_conformite` 4, `confiance_reputation` 4, `ethique_impact` 4, `marche_innovation` 3, `service_client_sav` 3, `operations_processus` 2, `livraison_logistique` 1
- Alertes : `rupture_service` 6, `rupture_stock` 5, `qualite_produit` 3, `juridique_conformite` 2, `securite_sante` 1, `fraude_arnaque` 1, `reputation_virale` 1

## Échecs après validation finale

- seed `6489` : intents.0: 'information_manquante' is not one of ['avis', 'plainte', 'eloge', 'question', 'demande_information', 'demande_aide', 'suggestion', 'recommandation', 'comparaison', 'intention_achat', 'partage_experience', 'signalement_incident', 'appel_action', 'promotion_spam', 'tag_mention', 'autre']
- seed `7028` : aspects.0.attribute: 'attachement' is not one of ['confiance', 'credibilite', 'image_marque', 'authenticite', 'recommandation', 'comparaison_concurrent']
- seed `36` : API — JSONDecodeError: Expecting ',' delimiter: line 1 column 553 (char 552)
- seed `212` : API — JSONDecodeError: Invalid \uXXXX escape: line 1 column 333 (char 332)
- seed `1517` : entities[0]:citation_non_alignee
- seed `1331` : API — JSONDecodeError: Invalid \uXXXX escape: line 1 column 1132 (char 1131)
- seed `844` : aspects[0].evidence[0]:citation_non_alignee
- seed `3090` : aspects[0].evidence[0]:citation_non_alignee
- seed `5540` : sentiment.evidence[0]:offset_hors_limites
- seed `5546` : aspects.0.evidence.0: Additional properties are not allowed ('source' was unexpected) ; sentiment.evidence.0: Additional properties are not allowed ('source' was unexpected) ; aspects[0].evidence[0]:citation_non_alignee
- seed `3946` : sentiment.evidence[0]:offset_hors_limites

## Corrections déterministes des offsets

- seed `5715` : 2 offset(s) réaligné(s)
- seed `6115` : 3 offset(s) réaligné(s)
- seed `6121` : 1 offset(s) réaligné(s)
- seed `6129` : 3 offset(s) réaligné(s)
- seed `6176` : 2 offset(s) réaligné(s)
- seed `6183` : 3 offset(s) réaligné(s)
- seed `6248` : 2 offset(s) réaligné(s)
- seed `6276` : 2 offset(s) réaligné(s)
- seed `6284` : 2 offset(s) réaligné(s)
- seed `6374` : 2 offset(s) réaligné(s)
- seed `6440` : 3 offset(s) réaligné(s)
- seed `6476` : 4 offset(s) réaligné(s)
- seed `6489` : 4 offset(s) réaligné(s)
- seed `6562` : 1 offset(s) réaligné(s)
- seed `6602` : 2 offset(s) réaligné(s)
- seed `6611` : 1 offset(s) réaligné(s)
- seed `6670` : 2 offset(s) réaligné(s)
- seed `6759` : 4 offset(s) réaligné(s)
- seed `6821` : 2 offset(s) réaligné(s)
- seed `6900` : 3 offset(s) réaligné(s)
- seed `7013` : 2 offset(s) réaligné(s)
- seed `7028` : 3 offset(s) réaligné(s)
- seed `7047` : 2 offset(s) réaligné(s)
- seed `7069` : 2 offset(s) réaligné(s)
- seed `7116` : 3 offset(s) réaligné(s)
- seed `7128` : 2 offset(s) réaligné(s)
- seed `7197` : 1 offset(s) réaligné(s)
- seed `7215` : 1 offset(s) réaligné(s)
- seed `7226` : 5 offset(s) réaligné(s)
- seed `7229` : 2 offset(s) réaligné(s)
- seed `7275` : 1 offset(s) réaligné(s)
- seed `7346` : 1 offset(s) réaligné(s)
- seed `1` : 3 offset(s) réaligné(s)
- seed `2` : 4 offset(s) réaligné(s)
- seed `20` : 2 offset(s) réaligné(s)
- seed `26` : 3 offset(s) réaligné(s)
- seed `32` : 3 offset(s) réaligné(s)
- seed `34` : 3 offset(s) réaligné(s)
- seed `39` : 2 offset(s) réaligné(s)
- seed `40` : 3 offset(s) réaligné(s)
- seed `236` : 2 offset(s) réaligné(s)
- seed `466` : 2 offset(s) réaligné(s)
- seed `576` : 4 offset(s) réaligné(s)
- seed `685` : 7 offset(s) réaligné(s)
- seed `740` : 4 offset(s) réaligné(s)
- seed `229` : 2 offset(s) réaligné(s)
- seed `191` : 3 offset(s) réaligné(s)
- seed `651` : 2 offset(s) réaligné(s)
- seed `665` : 2 offset(s) réaligné(s)
- seed `1500` : 4 offset(s) réaligné(s)
- seed `1517` : 1 offset(s) réaligné(s)
- seed `1632` : 3 offset(s) réaligné(s)
- seed `1447` : 3 offset(s) réaligné(s)
- seed `1461` : 4 offset(s) réaligné(s)
- seed `1471` : 2 offset(s) réaligné(s)
- seed `1360` : 1 offset(s) réaligné(s)
- seed `1392` : 2 offset(s) réaligné(s)
- seed `844` : 4 offset(s) réaligné(s)
- seed `855` : 3 offset(s) réaligné(s)
- seed `856` : 2 offset(s) réaligné(s)
- seed `914` : 3 offset(s) réaligné(s)
- seed `940` : 3 offset(s) réaligné(s)
- seed `947` : 2 offset(s) réaligné(s)
- seed `1173` : 3 offset(s) réaligné(s)
- seed `1175` : 2 offset(s) réaligné(s)
- seed `1874` : 1 offset(s) réaligné(s)
- seed `3090` : 2 offset(s) réaligné(s)
- seed `5531` : 5 offset(s) réaligné(s)
- seed `5532` : 3 offset(s) réaligné(s)
- seed `5540` : 1 offset(s) réaligné(s)
- seed `5541` : 2 offset(s) réaligné(s)
- seed `5544` : 8 offset(s) réaligné(s)
- seed `5545` : 1 offset(s) réaligné(s)
- seed `5546` : 4 offset(s) réaligné(s)
- seed `5560` : 2 offset(s) réaligné(s)
- seed `5562` : 2 offset(s) réaligné(s)
- seed `4381` : 3 offset(s) réaligné(s)
- seed `2856` : 2 offset(s) réaligné(s)
- seed `3431` : 2 offset(s) réaligné(s)
- seed `3946` : 1 offset(s) réaligné(s)
- seed `3923` : 1 offset(s) réaligné(s)
- seed `4364` : 2 offset(s) réaligné(s)
- seed `2729` : 3 offset(s) réaligné(s)
- seed `41` : 1 offset(s) réaligné(s)

## Fichiers

- Résultats détaillés : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T203516Z\pilot_results.jsonl`
- Manifeste de l'échantillon : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T203516Z\sample_manifest.jsonl`
- Schéma métier validé : `G:\ramypulse\docs\slm_v2\business_comment_annotation_v0.1.schema.json`

## Critère recommandé avant génération massive

Ne pas relancer les milliers d'exemples tant que :

1. 100 % des sorties ne passent pas le schéma final et les contrôles de citations ;
2. les divergences sémantiques n'ont pas été revues sur un échantillon humain ;
3. l'ontologie n'a pas été testée sur davantage de secteurs réels que le corpus actuel ;
4. le format d'entraînement final du SLM n'est pas figé séparément du format d'annotation.
