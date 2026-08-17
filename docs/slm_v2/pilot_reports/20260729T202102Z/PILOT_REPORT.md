# Rapport du pilote — schéma business V0.1

## Verdict automatique

- Exécution : `20260729T202102Z`
- Fournisseur du pilote : `gemini`
- Modèle enseignant : `gemini-3.5-flash`
- Échantillon : 1 commentaires stratifiés
- Réponses API : 0/1 (0.0%)
- Valides sans correction : 0/0 (n/a)
- Valides après réalignement déterministe des offsets : 0/0 (n/a)
- Sorties nécessitant un réalignement d'offset : 0/0 (n/a)
- Latence moyenne / p95 : 0 ms / 0 ms
- Jetons totaux : 0
- Accord avec les anciens labels faibles de sentiment : 0/0 (n/a)

L'accord avec les anciens labels n'est pas une mesure d'exactitude : ces labels sont faibles et servent seulement de signal de divergence à revoir humainement.

## Couverture observée

- Pertinence business : aucun
- Sentiment : aucun
- Langue dominante : aucun
- Intentions : aucun
- Familles d'aspect : aucun
- Alertes : aucun

## Échecs après validation finale

- seed `5658` : API — ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}

## Corrections déterministes des offsets

- Aucun offset réparé.

## Fichiers

- Résultats détaillés : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T202102Z\pilot_results.jsonl`
- Manifeste de l'échantillon : `G:\ramypulse\data\processed\slm_v2_pilot\20260729T202102Z\sample_manifest.jsonl`
- Schéma métier validé : `G:\ramypulse\docs\slm_v2\business_comment_annotation_v0.1.schema.json`

## Critère recommandé avant génération massive

Ne pas relancer les milliers d'exemples tant que :

1. 100 % des sorties ne passent pas le schéma final et les contrôles de citations ;
2. les divergences sémantiques n'ont pas été revues sur un échantillon humain ;
3. l'ontologie n'a pas été testée sur davantage de secteurs réels que le corpus actuel ;
4. le format d'entraînement final du SLM n'est pas figé séparément du format d'annotation.
