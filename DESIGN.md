# LIDAL Pulse Design System

<!-- impeccable:design-schema 1 -->

## Direction

**Preuve Terrain** est le monde visuel unique de LIDAL Pulse. La plateforme doit ressembler à un système de décision fondé sur des observations vérifiables, pas à un cockpit, un chatbot ou un laboratoire médical.

La promesse visible est : **un constat n'existe jamais sans ses verbatims, sa source, sa fraîcheur et son niveau de confiance**.

## Decision Rationale

- Les clients visés sont d'abord les directions marketing, qualité, expérience client et communication d'entreprises algériennes moyennes ou grandes.
- Leur tâche prioritaire est de repérer ce qui change, comprendre pourquoi, vérifier les preuves puis affecter une action.
- Les plateformes internationales couvrent déjà les tableaux de bord, alertes, résumés IA et assistants. LIDAL Pulse se différencie par la compréhension de la darija, de l'arabizi, de l'arabe, du français et du code-switching, ainsi que par la traçabilité métier et le déploiement local visé.
- Le design doit donc rendre l'avantage linguistique et la preuve plus visibles que l'IA elle-même.

## Signature Interaction

La **Piste de preuve** relie fonctionnellement :

`Signal → Verbatims → Interprétation → Recommandation → Action`

Elle n'est jamais un trait décoratif. Chaque étape est ouvrable, possède un état et expose sa provenance. Sur les écrans étroits, elle devient une séquence verticale. Sur les pages analytiques, un panneau de preuve contextuel évite de perdre le filtre ou le sujet en cours.

Sur la Situation du jour, cette piste prend la forme d'une chaîne opérationnelle compacte : **Signal détecté → Ce que cela signifie → Décision proposée**. Elle précède la file de traitement et les métriques secondaires afin que la valeur du produit soit comprise avant ses chiffres.

## Visual Foundations

### Palette

- Mineral Canvas — `#F8FAF7`
- Pure Evidence — `#FFFFFF`
- Deep Petrol — `#183D47`
- Field Teal — `#0F766E`
- Control Cobalt — `#4F6EF7`
- Mineral Line — `#D8E4DE`

La couleur encode une fonction stable :

- **Bleu — Surveiller** : collecte, sujets suivis, sélection et contexte.
- **Rouge — Risque** : alertes critiques, dérives et actions urgentes.
- **Violet — Comprendre** : recherche, verbatims, analyses et campagnes.
- **Vert — Agir** : recommandations validables, résolution et réussite.
- **Gris minéral — Configurer** : sources, accès et opérations techniques.

Une couleur est toujours accompagnée d'un libellé et d'une icône. Aucun orange de marque, fond noir, halo néon ou gradient décoratif.

### Materials

- surfaces minérales claires et mates ;
- séparateurs fins inspirés des fiches de contrôle ;
- pochettes de preuve légèrement teintées pour regrouper un verbatim et ses métadonnées ;
- encre cobalt pour les annotations et actions, teal pour la validation et la provenance.

### Typography

- Titres : Manrope, poids 650 à 800, usage parcimonieux.
- Interface et lecture : Inter, poids 400 à 650.
- Données : chiffres tabulaires Inter ; monospace uniquement pour identifiants, requêtes ou données techniques.
- Les textes arabes utilisent une pile système compatible et `dir="auto"` au niveau du verbatim.

### Geometry

- Rayons contenus : 8 à 14 px selon la taille ; pas de pilules pour les conteneurs.
- Bordures : 1 px, contraste modéré ; l'élévation vient d'abord de la hiérarchie de surface.
- Ombres : rares, petites et neutres ; aucune lueur.
- Grille : densité desktop assumée, mais une seule question métier dominante par section.

## Information Architecture

### Navigation métier

1. **Surveiller** — Situation du jour, Sujets surveillés, Alertes à traiter.
2. **Comprendre** — Explorer les avis, Impact des campagnes.
3. **Agir** — Actions recommandées.
4. **Configurer** — Sources de données et accès.

`Créer une surveillance` est l'action globale persistante. Les mêmes verbes, couleurs et icônes sont conservés dans la navigation, les en-têtes et les états vides.

### Two Reading Modes

- **Briefing** : destiné à la direction ; trois priorités maximum, évolution, risque, recommandation et prochaine action.
- **Analyse** : destiné au marketing, à la qualité et aux analystes ; filtres, verbatims, aspects, langues, provenance et comparaison.

Le produit n'affiche pas la même densité à tous les utilisateurs. Le détail se révèle sans changer de contexte.

## Component Language

- `Finding`: constat prioritaire, impact, fraîcheur et confiance.
- `EvidenceSample`: verbatim avec langue, source, date, auteur anonymisé et surlignage de la preuve.
- `ProvenanceBlock`: périmètre, sources, volume, dernière collecte et limites.
- `Recommendation`: action proposée, justification, propriétaire, échéance et statut.
- `ProofTrail`: séquence interactive reliant les objets ci-dessus.
- `DataTable`: dense, triable, sans cartes imbriquées.
- `StatusTag`: compact et sémantique ; jamais utilisé comme décoration.

## Motion

Les animations servent exclusivement la compréhension :

- apparition de page : opacité + translation de 4 px, 180 à 240 ms ;
- panneau de preuve : entrée depuis le bord le plus proche, 220 à 300 ms ;
- changement d'état : couleur/bordure, 140 à 180 ms ;
- progression d'une collecte : mouvement continu seulement pendant une exécution réelle ;
- graphiques : transition uniquement entre deux périodes comparables ;
- respect strict de `prefers-reduced-motion`.

Éviter les rebonds, les délais en cascade sur les éléments fréquents, les hover qui déplacent la mise en page et toute animation décorative permanente.

## Content Rules

- Dire ce qui change avant de montrer un score.
- Toute conclusion IA indique confiance, fraîcheur et accès à la preuve.
- Ne jamais employer « vérité », « certain » ou « client acquis » sans preuve.
- Utiliser `Surveiller`, `Avis`, `Preuve`, `Alerte`, `Action recommandée` et `Source de données` de manière stable.
- Préférer le résultat métier au nom interne du module : « Alertes à traiter » plutôt que « Console d'alertes », « Explorer les avis » plutôt que « Recherche augmentée ».
- Montrer les limites du modèle dans le contexte de la décision, pas dans une page juridique isolée.

## Accessibility

- WCAG 2.2 AA minimum.
- Focus visible cobalt et non dépendant de la couleur seule.
- Cibles interactives de 40 px minimum, 44 px sur mobile.
- États des graphiques doublés par labels, motifs ou texte.
- `dir="auto"` pour les contenus utilisateurs et architecture prête pour le RTL.
- Aucun sens transmis uniquement par une animation.

## Do Not

- Ne pas recréer un cockpit sombre.
- Ne pas utiliser une grille de KPI comme premier message de la page.
- Ne pas faire de l'assistant IA le centre du produit.
- Ne pas employer une esthétique médicale, clinique ou scientifique littérale.
- Ne pas masquer les verbatims derrière un score de confiance.
- Ne pas appliquer la Piste de preuve là où il n'existe pas de relation de provenance réelle.
