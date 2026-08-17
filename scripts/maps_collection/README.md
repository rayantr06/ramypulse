# Collecte Google Maps — à lancer sur le PC de calcul

Scraper : [`gosom/google-maps-scraper`](https://github.com/gosom/google-maps-scraper), MIT,
binaire Windows autonome. Aucune dépendance à installer.

## Ce que la collecte doit produire

Le corpus actuel n'a **aucune source en scope `organisation`** hors agroalimentaire, et
seulement 16 événements d'alerte distincts. Les avis Maps règlent les deux : un lieu est
une organisation, sa catégorie donne le secteur, et 31 % des avis sont à 1 ou 2 étoiles.

## Préparation

Télécharger le binaire depuis les
[releases](https://github.com/gosom/google-maps-scraper/releases) — `windows-amd64.exe`,
58 Mo. Le placer dans ce dossier sous le nom `gms.exe`.

## Palier 1 — calibrage, 3 villes

102 requêtes couvrant 9 familles de secteurs sur Alger, Oran et Constantine.

**Deux passes de langue.** Le paramètre `-lang` filtre la collecte : une passe `fr` seule
donne 143 avis français pour 1 arabe. C'est un artefact du paramètre, pas la réalité du
terrain.

```powershell
.\gms.exe -input requetes_palier1.txt -results out_fr.json -json -lang fr `
          -extra-reviews -depth 2 -c 8 -exit-on-inactivity 5m

.\gms.exe -input requetes_palier1.txt -results out_ar.json -json -lang ar `
          -extra-reviews -depth 2 -c 8 -exit-on-inactivity 5m
```

Ajuster `-c` selon la machine. Sur un portable 8 Go, rester à 2. Sur une configuration
avec bon processeur, 8 à 16 conviennent.

Ordre de grandeur attendu : ~2 000 lieux et ~15 000 avis **par passe**.

## Palier 2 — extension, 7 villes

À lancer seulement après avoir vérifié le palier 1. Mêmes commandes avec
`requetes_palier2.txt`.

## Ingestion

Ne pas verser les fichiers bruts dans le corpus. Passer par :

```powershell
python scripts\ingest_maps_reviews.py --input scripts\maps_collection\out_fr.json `
                                       --input scripts\maps_collection\out_ar.json
```

L'ingestion fait quatre choses que la sortie brute ne fait pas :

1. **Supprime les données personnelles.** Le scraper renvoie `Name`, `ProfilePicture` et
   `author_url` pour chaque avis, sans option pour les désactiver. Contrairement à
   l'acteur Apify qui expose `scrapeReviewsPersonalData: False`, ici le retrait est à
   notre charge.
2. **Déduplique sur `review_id`**, indispensable puisque les deux passes de langue
   ramènent les mêmes lieux.
3. **Écarte les traductions.** Le champ `text_translated` signale un avis traduit vers la
   langue demandée : ce n'est pas le texte d'origine et il ne doit pas entrer dans un
   corpus d'entraînement.
4. **Assigne `monitoring_target`** en scope `organisation`, le lieu étant l'entité
   surveillée, et conserve la catégorie comme secteur.

## Champs disponibles dans la sortie brute

Par lieu : `title`, `category`, `categories`, `address`, `complete_address`,
`review_rating`, `reviews_per_rating`, `cid`, `link`.

Par avis : `text_original`, `Rating`, `language`, `translated_lang`, `text_translated`,
`published_at`, `review_id`, `When`.

`Rating` sert d'étiquette faible : un avis 1 étoile annoté `positif` est un signal
d'erreur détectable automatiquement, à l'échelle de milliers d'items.

## Limites connues

- Pas de filtre de fraîcheur, contrairement à Apify qui a `reviewsStartDate`. Filtrer sur
  `published_at` à l'ingestion.
- Environ 300 avis maximum par lieu.
- L'arabizi reste rare dans les avis Maps — 7 sur 144 lors du test. Cette langue vient de
  Facebook et Instagram, pas d'ici.
