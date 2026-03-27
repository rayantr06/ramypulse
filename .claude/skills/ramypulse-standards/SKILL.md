---
name: ramypulse-standards
description: Standards et contraintes du projet RamyPulse. 
  Activer automatiquement quand on travaille sur du code Python 
  dans ce projet.
---

## Contraintes métier RamyPulse
- Les 5 classes de sentiment: très_positif, positif, neutre, négatif, très_négatif
- Les 5 aspects Ramy: goût, emballage, prix, disponibilité, fraîcheur
- Les canaux: facebook, google_maps, audio, youtube
- NSS = (positifs - négatifs) / total × 100

## Patterns obligatoires
- Tout DataFrame annoté DOIT avoir les colonnes: 
  text, sentiment_label, channel, aspect, source_url, timestamp, confidence
- Tout output FAISS DOIT inclure les metadata (channel, source_url)
- Toute réponse RAG DOIT inclure au moins 1 source cliquable
- Le normalizer DOIT gérer: Arabizi (7→ح), script arabe, français, mixte 
