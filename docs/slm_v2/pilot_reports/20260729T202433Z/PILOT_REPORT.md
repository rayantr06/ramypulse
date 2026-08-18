# Rapport du pilote — schéma business V0.1

## Verdict automatique

- Exécution : `20260729T202433Z`
- Fournisseur du pilote : `gemini`
- Modèle enseignant : `gemini-3.5-flash-lite`
- Échantillon : 1 commentaires stratifiés
- Réponses API : 1/1 (100.0%)
- Valides sans correction : 1/1 (100.0%)
- Valides après réalignement déterministe des offsets : 1/1 (100.0%)
- Sorties nécessitant un réalignement d'offset : 0/1 (0.0%)
- Latence moyenne / p95 : 4052 ms / 4052 ms
- Jetons totaux : 2871
- Accord avec les anciens labels faibles de sentiment : 0/1 (0.0%)

L'accord avec les anciens labels n'est pas une mesure d'exactitude : ces labels sont faibles et servent seulement de signal de divergence à revoir humainement.

## Couverture observée

- Pertinence business : `indirecte` 1
- Sentiment : `neutre` 1
- Langue dominante : `darija_arabe` 1
- Intentions : `partage_experience` 1
- Familles d'aspect : aucun
- Alertes : aucun

## Échecs après validation finale

- Aucun échec final.

## Corrections déterministes des offsets

- Aucun offset réparé.

## Fichiers

- Résultats détaillés : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T202433Z\pilot_results.jsonl`
- Manifeste de l'échantillon : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T202433Z\sample_manifest.jsonl`
- Schéma métier validé : `G:\ramypulse\docs\slm_v2\business_comment_annotation_v0.1.schema.json`

## Critère recommandé avant génération massive

Ne pas relancer les milliers d'exemples tant que :

1. 100 % des sorties ne passent pas le schéma final et les contrôles de citations ;
2. les divergences sémantiques n'ont pas été revues sur un échantillon humain ;
3. l'ontologie n'a pas été testée sur davantage de secteurs réels que le corpus actuel ;
4. le format d'entraînement final du SLM n'est pas figé séparément du format d'annotation.
