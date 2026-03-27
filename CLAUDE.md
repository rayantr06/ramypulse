# RamyPulse — CLAUDE.md

## Projet
Système d'analyse de sentiment ABSA pour dialecte algérien.
Dashboard Streamlit + DziriBERT + FAISS + Ollama.

## Stack technique
- Python 3.10+, Streamlit, PyTorch, transformers, FAISS, Ollama
- Données: Parquet via pandas/pyarrow
- Visualisations: Plotly uniquement
- LLM local: Ollama (llama3.2:3b)

## Règles strictes
- JAMAIS de score de sentiment continu. Toujours 5 classes discrètes.
- JAMAIS de dépendance cloud. Tout tourne en local.
- Chaque fonction a un docstring en français.
- Chaque module a des tests unitaires.
- Les imports sont groupés: stdlib, third-party, local.
- Pas de print() — utiliser logging.
- Format de données standard: Parquet avec colonnes 
  [text, sentiment_label, channel, aspect, source_url, timestamp, confidence]

## Structure
Voir PRD Section 2.3 pour l'arbre de fichiers exact.
Le fichier config.py centralise TOUTES les constantes.

## Comment travailler
1. Lire le PRD (RamyPulse_PRD_Technique_v1.pdf) pour le contexte complet
2. Implémenter un fichier à la fois dans l'ordre du Sprint Plan (Section 4)
3. Écrire les tests AVANT l'implémentation (TDD)
4. Vérifier que les tests passent avant de passer au fichier suivant 
