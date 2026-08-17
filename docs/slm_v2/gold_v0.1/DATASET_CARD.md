# RamyPulse Business Comments — Gold Candidate V0.1

## Statut

Ce fichier est un benchmark candidat à annotateur unique. Ses 100 lignes ont fait l'objet d'une revue sémantique explicite et passent le schéma métier V0.1 ainsi que les contrôles de citations et de références.

Il peut servir au développement, à la comparaison de prompts et à l'évaluation préliminaire. Il ne doit pas être présenté comme un gold humain définitif tant qu'une seconde annotation indépendante et une adjudication n'ont pas été réalisées.

Les 100 lignes portent le split `gold_evaluation` : elles doivent rester hors des données d'entraînement.

## Fichier

- Dataset : `G:\ramypulse\data\processed\slm_v2_gold\business_comments_gold_candidate_v0.1.jsonl`
- SHA-256 : `fae878f5ec1f36db412f1bd5bf7837d63ff650e14cfd049ade7f96d5a6d8fed9`
- Schéma : `G:\ramypulse\docs\slm_v2\business_comment_annotation_v0.1.schema.json`

## Composition

- Sources : {"ramypulse_v1_facebook": 36, "tenant_demo_expo": 5, "massinissa_algerian_corpus": 59}
- Thèmes : {"fmcg_beverages": 41, "business": 11, "economy": 10, "health": 10, "education": 8, "media": 1, "social": 9, "technologie": 3, "tourism": 7}
- Pertinence business : {"directe": 68, "aucune": 5, "indirecte": 27}
- Sentiment : {"negatif": 46, "neutre": 31, "positif": 21, "mixte": 2}
- Langues dominantes : {"darija_arabe": 47, "arabe_msa": 35, "darija_arabizi": 2, "francais": 11, "mixte": 4, "anglais": 1}
- Familles d'aspect : {"securite_conformite": 5, "produit_service": 14, "disponibilite_acces": 5, "communication_information": 8, "operations_processus": 7, "digital_technologie": 7, "confiance_reputation": 5, "experience_client": 4, "ethique_impact": 5, "prix_valeur": 10, "marche_innovation": 3, "service_client_sav": 3, "emploi_management": 8, "infrastructure_service_public": 16, "livraison_logistique": 1}

## Contrôles

- JSON Schema : 100/100
- Preuves et offsets : 100/100
- Références d'entités : 100/100
- Décisions de revue : {"modify": 63, "accept": 37}

## Évaluation d'un modèle

Le fichier de prédictions attendu contient une ligne par `record_id` avec un champ `annotation`.

```powershell
python scripts/evaluate_business_annotations_v01.py `
  --predictions chemin\predictions.jsonl `
  --output chemin\evaluation.json
```

L'évaluateur mesure la couverture, la validité du schéma, les catégories principales, les intentions, les aspects, les alertes, les entités et l'ancrage exact des preuves.

## Usage recommandé

1. Ne jamais entraîner et évaluer sur les mêmes lignes.
2. Conserver `text` inchangé.
3. Ne pas exposer les anciens labels faibles au modèle.
4. Utiliser `annotation` comme cible et `context` uniquement lorsque la donnée est réellement disponible en production.
5. Après double annotation, figer les splits et publier une nouvelle version immuable.
