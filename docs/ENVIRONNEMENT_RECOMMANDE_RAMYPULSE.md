# RamyPulse — Environnement recommandé

## Objet
Document de cadrage environnemental pour exécuter RamyPulse de manière stable, avec les vrais modèles et sans dépendre uniquement des fallbacks locaux.

Ce document capture :
- l'environnement recommandé
- les problèmes observés sur la machine actuelle
- la procédure de setup conseillée
- une checklist de validation

## Résumé
Sur la machine actuelle, RamyPulse fonctionne partiellement :
- l'application démarre
- les tests passent
- les scripts peuvent aller au bout avec des fallbacks

Mais l'environnement ML n'est pas sain pour un fonctionnement complet sur les vrais modèles.

Les deux symptômes principaux observés ici :
- `torchvision` casse à l'import
- `sentence-transformers` casse à l'import à cause d'une incompatibilité avec `transformers`

Résultat :
- DziriBERT tombe en fallback
- l'embedder E5 tombe en fallback

## Environnement observé sur cette machine

Python :
- `3.11.2`

Interpréteur utilisé :
- `C:\Users\AZ\AppData\Local\Programs\Python\Python311\python.exe`

Versions observées :
- `torch = 2.8.0+cpu`
- `torchvision = import error`
- `transformers = 4.55.2`
- `sentence_transformers = import error`
- `streamlit = 1.37.0`
- `faiss = 1.13.2`
- `pandas = 2.2.3`

Erreurs observées :
- `operator torchvision::nms does not exist`
- `cannot import name 'PreTrainedModel' from 'transformers'`

## Conclusion sur la machine actuelle
Le problème principal n'est pas le repo lui-même.

Le problème vient surtout d'un environnement Python global incohérent pour le stack ML :
- `torch`
- `torchvision`
- `transformers`
- `sentence-transformers`

Le système est donc capable de tourner en mode dégradé, mais pas dans les meilleures conditions.

## Recommandation générale
Ne pas utiliser l'environnement Python global de la machine pour RamyPulse.

Créer un environnement isolé dédié au projet.

## Environnement recommandé

### Python
Version recommandée :
- `Python 3.10` ou `Python 3.11`

Recommandation pratique :
- `Python 3.11` reste acceptable
- mais il faut impérativement un `venv` propre

### Isolation
Toujours utiliser un environnement dédié :
- `.venv`

À éviter :
- installation globale des libs
- mélange de paquets issus de plusieurs projets
- dépendances ML installées par couches successives sans contrôle

### Dépendances critiques à stabiliser
Le noyau à fiabiliser en priorité :
- `torch`
- `torchvision`
- `transformers`
- `sentence-transformers`

Le point clé :
- `torch` et `torchvision` doivent être compatibles
- `sentence-transformers` doit être compatible avec la version de `transformers`

## Setup recommandé

### 1. Créer le venv
```bash
python -m venv .venv
```

### 2. Activer le venv
PowerShell :
```powershell
.venv\Scripts\Activate.ps1
```

### 3. Mettre à jour pip
```bash
python -m pip install --upgrade pip setuptools wheel
```

### 4. Installer les dépendances du projet
```bash
pip install -r requirements.txt
```

### 5. Vérifier les imports critiques
```bash
python -c "import torch, torchvision, transformers, sentence_transformers; print('ok')"
```

## Si `torchvision` casse
Symptôme :
- `operator torchvision::nms does not exist`

Cela indique généralement :
- version de `torchvision` incompatible avec `torch`
- installation cassée
- wheel CPU/GPU incohérente

Approche recommandée :
- désinstaller proprement `torch`, `torchvision`, `torchaudio`
- les réinstaller ensemble, dans le même venv

Exemple :
```bash
pip uninstall -y torch torchvision torchaudio
```

Puis réinstallation cohérente :
```bash
pip install torch torchvision torchaudio
```

Si besoin, utiliser explicitement les wheels CPU officielles correspondant à la version choisie.

## Si `sentence-transformers` casse
Symptôme :
- `cannot import name 'PreTrainedModel' from 'transformers'`

Cela suggère en général :
- incompatibilité entre `sentence-transformers` et `transformers`
- version `transformers` trop récente ou non alignée

Approche recommandée :
- réinstaller `transformers` et `sentence-transformers` ensemble dans le venv
- éviter de conserver une installation globale héritée

## Ollama
Pour que le chat RAG fonctionne réellement côté génération :

### Service
Lancer :
```bash
ollama serve
```

### Modèle
Télécharger :
```bash
ollama pull llama3.2:3b
```

### Vérification
```bash
ollama list
```

## Données minimales pour la démo réelle

### Obligatoires
- `data/processed/annotated.parquet`

### Pour le vrai RAG
- `data/embeddings/faiss_index.faiss`
- `data/embeddings/faiss_index.json`
- `data/embeddings/bm25.pkl`

### Pour le fallback local de collecte
- au moins un fichier Parquet réel dans `data/demo/`

## Ordre de lancement recommandé
Une fois l'environnement propre :

```bash
python scripts/01_collect_data.py
python scripts/02_process_data.py
python scripts/03_classify_sentiment.py
python scripts/04_build_index.py
python scripts/05_run_demo.py
```

## Ce qui doit marcher dans un environnement sain

### Côté ML
- DziriBERT se charge sans fallback
- multilingual-e5-base se charge sans fallback
- les embeddings sont construits avec le vrai modèle
- la classification ne repose pas sur l'heuristique locale

### Côté app
- Dashboard sur vraies données
- Explorer sur vraies données
- What-If sur vraies données
- Chat RAG en mode live si Ollama + index disponibles

## Checklist de validation

### Environnement
- [ ] venv créé
- [ ] pip mis à jour
- [ ] requirements installés
- [ ] `import torch` OK
- [ ] `import torchvision` OK
- [ ] `import transformers` OK
- [ ] `import sentence_transformers` OK

### Modèles
- [ ] DziriBERT charge sans erreur
- [ ] E5 charge sans erreur
- [ ] Ollama répond
- [ ] `llama3.2:3b` présent localement

### Données
- [ ] `annotated.parquet` présent
- [ ] index FAISS construit
- [ ] BM25 construit
- [ ] fallback local présent dans `data/demo/` si nécessaire

### Application
- [ ] `scripts/05_run_demo.py` se lance
- [ ] Streamlit écoute sur le port prévu
- [ ] le chat n'affiche plus le mode démo si tout est prêt

## Position recommandée
Pour un usage sérieux de RamyPulse :
- utiliser un venv dédié
- éviter l'environnement Python global
- stabiliser le stack ML avant de juger les performances réelles du produit

## Note finale
Le repo est maintenant fonctionnel.

Mais pour que RamyPulse fonctionne comme prévu avec les vrais modèles, il faut un environnement cohérent, pas seulement le bon code.
