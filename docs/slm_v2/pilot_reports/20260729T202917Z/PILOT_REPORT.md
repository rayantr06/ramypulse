# Rapport du pilote — schéma business V0.1

## Verdict automatique

- Exécution : `20260729T202917Z`
- Fournisseur du pilote : `gemini`
- Modèle enseignant : `gemini-3.5-flash-lite`
- Échantillon : 10 commentaires stratifiés
- Réponses API : 10/10 (100.0%)
- Valides sans correction : 2/10 (20.0%)
- Valides après réalignement déterministe des offsets : 10/10 (100.0%)
- Sorties nécessitant un réalignement d'offset : 8/10 (80.0%)
- Latence moyenne / p95 : 1632 ms / 1808 ms
- Jetons totaux : 57574
- Accord avec les anciens labels faibles de sentiment : 7/10 (70.0%)

L'accord avec les anciens labels n'est pas une mesure d'exactitude : ces labels sont faibles et servent seulement de signal de divergence à revoir humainement.

## Couverture observée

- Pertinence business : `directe` 9, `indirecte` 1
- Sentiment : `neutre` 4, `negatif` 3, `positif` 3
- Langue dominante : `darija_arabe` 5, `arabe_msa` 3, `francais` 2
- Intentions : `partage_experience` 3, `eloge` 3, `plainte` 2, `signalement_incident` 2, `question` 2, `demande_information` 2, `avis` 2, `suggestion` 1
- Familles d'aspect : `produit_service` 4, `prix_valeur` 3, `securite_conformite` 2, `disponibilite_acces` 1, `experience_client` 1, `marche_innovation` 1, `livraison_logistique` 1
- Alertes : `securite_sante` 2

## Échecs après validation finale

- Aucun échec final.

## Corrections déterministes des offsets

- seed `5715` : 3 offset(s) réaligné(s)
- seed `6611` : 2 offset(s) réaligné(s)
- seed `7013` : 2 offset(s) réaligné(s)
- seed `7047` : 2 offset(s) réaligné(s)
- seed `7226` : 5 offset(s) réaligné(s)
- seed `236` : 4 offset(s) réaligné(s)
- seed `5560` : 3 offset(s) réaligné(s)
- seed `4381` : 3 offset(s) réaligné(s)

## Fichiers

- Résultats détaillés : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T202917Z\pilot_results.jsonl`
- Manifeste de l'échantillon : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T202917Z\sample_manifest.jsonl`
- Schéma métier validé : `G:\ramypulse\docs\slm_v2\business_comment_annotation_v0.1.schema.json`

## Critère recommandé avant génération massive

Ne pas relancer les milliers d'exemples tant que :

1. 100 % des sorties ne passent pas le schéma final et les contrôles de citations ;
2. les divergences sémantiques n'ont pas été revues sur un échantillon humain ;
3. l'ontologie n'a pas été testée sur davantage de secteurs réels que le corpus actuel ;
4. le format d'entraînement final du SLM n'est pas figé séparément du format d'annotation.
