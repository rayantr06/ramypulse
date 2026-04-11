# RamyPulse — Collecteur de commentaires Facebook & Instagram

Script autonome pour récupérer les commentaires des pages Facebook et Instagram de **Ramy**, **Hamoud Boualem**, **Ifri** et **NCA Rouiba** via l'API [Apify](https://apify.com).

## Prérequis

- Python 3.9+
- Un compte Apify gratuit (10 000 commentaires/mois offerts)

## Installation

```bash
cd scraping/
pip install -r requirements.txt
cp .env.example .env
# Éditer .env et coller votre token Apify
```

## Utilisation

```bash
# Collecter toutes les marques (Facebook + Instagram)
python collect.py

# Collecter une seule marque
python collect.py --brand "Ramy"
python collect.py --brand "Ifri"

# Facebook uniquement
python collect.py --platform facebook

# Instagram uniquement
python collect.py --platform instagram

# Mode dry-run (vérifier la config sans appeler Apify)
python collect.py --dry-run
```

## Configuration

Toutes les pages cibles et paramètres sont dans **`targets.yaml`** :

- Ajouter/retirer des marques
- Spécifier des URLs de posts précis
- Régler le nombre max de commentaires par post
- Filtrer par date

## Sortie

```
output/
├── raw/
│   ├── ramy_20260411.csv
│   ├── hamoud_boualem_20260411.csv
│   ├── ifri_20260411.csv
│   └── nca_rouiba_20260411.csv
├── all_comments.csv          ← Fichier fusionné (toutes marques)
└── collection_stats.json     ← Statistiques de collecte
```

Chaque CSV contient les colonnes : `text`, `brand`, `platform`, `date`, `likes`, `replies_count`, `author`, `comment_url`, `post_url`, `is_reply`, `collected_at`.

## Structure

| Fichier | Rôle |
|---------|------|
| `collect.py` | Script principal de collecte |
| `targets.yaml` | Pages cibles et paramètres |
| `requirements.txt` | Dépendances Python |
| `.env.example` | Template pour le token Apify |

## Coût

| Plan Apify | Limite | Prix |
|------------|--------|------|
| Free | 10 000 commentaires/mois | 0$ |
| Starter | Illimité + proxies résidentiels | 49$/mois |

Pour un projet de recherche académique, le plan gratuit est suffisant pour la collecte initiale.
