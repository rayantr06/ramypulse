---
name: "LIDAL Pulse"
description: "Clarté modulaire en Operate UI compact pour transformer les signaux clients en décisions vérifiables."
colors:
  electric-violet: "hsl(253 100% 58%)"
  violet-wash: "hsl(253 100% 94%)"
  risk-red: "hsl(353 67% 42%)"
  risk-wash: "hsl(352 82% 96%)"
  insight-purple: "hsl(275 84% 52%)"
  insight-wash: "hsl(275 90% 96%)"
  action-green: "hsl(151 67% 31%)"
  action-wash: "hsl(150 50% 94%)"
  warning-amber: "hsl(36 72% 42%)"
  pearl-ground: "hsl(0 0% 94%)"
  surface-white: "hsl(0 0% 100%)"
  surface-soft: "hsl(0 0% 97%)"
  surface-neutral: "hsl(0 0% 93%)"
  surface-pressed: "hsl(0 0% 90%)"
  ink: "hsl(240 8% 9%)"
  ink-muted: "hsl(240 4% 42%)"
  outline-soft: "hsl(0 0% 86%)"
typography:
  display:
    fontFamily: "Urbanist, sans-serif"
    fontSize: "clamp(2rem, 3.4vw, 3.35rem)"
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Urbanist, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Urbanist, Inter, sans-serif"
    fontSize: "1.45rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Inter, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, sans-serif"
    fontSize: "0.625rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "normal"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  stat: "20px"
  "2xl": "24px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  "2xl": "24px"
  "3xl": "28px"
  "4xl": "32px"
components:
  button-primary:
    backgroundColor: "{colors.electric-violet}"
    textColor: "{colors.surface-white}"
    typography: "{typography.body}"
    rounded: "{rounded.full}"
    padding: "8px 16px"
    height: "36px"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.full}"
    padding: "8px 16px"
    height: "36px"
  top-stage-active:
    backgroundColor: "{colors.electric-violet}"
    textColor: "{colors.surface-white}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "8px 16px"
  search-field:
    backgroundColor: "{colors.surface-neutral}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.full}"
    padding: "0 48px 0 40px"
    height: "44px"
    width: "32rem"
  panel:
    backgroundColor: "{colors.surface-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.2xl}"
    padding: "20px"
  dashboard-stat:
    backgroundColor: "{colors.surface-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.stat}"
    padding: "15.2px"
  alert-row:
    backgroundColor: "{colors.surface-white}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    padding: "13.6px 20px"
    height: "72px"
  decision-summary-step:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    padding: "14.4px"
  rail-item-active:
    backgroundColor: "{colors.electric-violet}"
    textColor: "{colors.surface-white}"
    rounded: "{rounded.xl}"
    size: "44px"
  status-chip:
    backgroundColor: "{colors.surface-neutral}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "4px 10px"
---

# Design System: LIDAL Pulse

## Overview

**Creative North Star: "Clarté modulaire"**

LIDAL Pulse est un espace de veille lumineux, dense et directement opératoire. Son expression « Operate UI » organise les signaux dans une succession de modules compacts : indicateurs essentiels, file d’alertes, analyse du jour, résumé de décision et détails de répartition. La toile perle crée du calme, les panneaux blancs structurent le travail et le violet électrique identifie la marque, l’état actif et l’action principale.

La hiérarchie repose sur l’alignement, la densité maîtrisée, les surfaces tonales et les libellés explicites. Aucun module spectaculaire ne doit dominer la preuve : chaque signal reste relié à sa fraîcheur, à sa confiance, à sa provenance et à une voie de vérification. Sur mobile, la même logique s’empile dans l’ordre de priorité sans changer de langage visuel.

**Key Characteristics:**

- Toile perle, panneaux blancs et subdivisions gris très clair.
- Violet électrique réservé à l’identité, à l’actif, au focus et à l’action primaire.
- Quatre KPI compacts en ouverture, lisibles en grille 4×1 ou 2×2.
- File d’alertes dense et actionnable, associée à une analyse du jour distincte.
- Résumé linéaire Signal → Interprétation → Décision avant validation humaine.
- Rail desktop compact, étapes en pilules dans l’en-tête et navigation mobile arrimée.
- Urbanist pour la hiérarchie et les chiffres, Inter pour la lecture, les preuves et les métadonnées.

## Colors

La palette presque monochrome laisse les accents sémantiques porter l’état sans concurrencer le contenu.

### Primary

- **Violet électrique LIDAL** (`electric-violet`) : identité, navigation active, appels à l’action primaires, focus et progression.
- **Brume violette** (`violet-wash`) : fond d’icône, profil, sélection ou état primaire discret.

### Secondary

- **Rouge risque** (`risk-red`) et **voile risque** (`risk-wash`) : alertes critiques, erreurs et contrôle requis.
- **Violet interprétation** (`insight-purple`) et **voile interprétation** (`insight-wash`) : analyse, explication et données à comprendre.
- **Vert action** (`action-green`) et **voile action** (`action-wash`) : décision proposée, évolution positive, collecte connectée et succès.

### Tertiary

- **Ambre vigilance** (`warning-amber`) : état intermédiaire qui demande attention sans être critique.

### Neutral

- **Perle de travail** (`pearl-ground`) : fond général de l’application.
- **Blanc panneau** (`surface-white`) : KPI, files, analyses, cartes et navigation.
- **Blanc doux** (`surface-soft`) : étapes de synthèse et encarts internes.
- **Gris module** (`surface-neutral`) : recherche, pilules inactives et surfaces secondaires.
- **Gris pressé** (`surface-pressed`) : survols, rails de progression et subdivisions plus denses.
- **Encre** (`ink`) : titres, valeurs et contenu principal.
- **Encre atténuée** (`ink-muted`) : descriptions, horodatages et métadonnées.
- **Contour doux** (`outline-soft`) : séparateurs de lignes et bordures de panneaux.

### Named Rules

**The White Workspace Rule.** Toutes les surfaces de travail restent claires ; la hiérarchie vient de la densité, des regroupements et des accents sémantiques, pas de grands aplats sombres.

**The Semantic Accent Rule.** Rouge, violet d’interprétation, vert et ambre gardent un sens stable et sont toujours doublés d’un texte, d’une icône ou d’un statut.

## Typography

**Display Font:** Urbanist (avec repli sans-serif)

**Body Font:** Inter (avec repli sans-serif)

**Label/Mono Font:** Inter pour les libellés ; ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas pour les raccourcis et identifiants techniques.

**Character:** Urbanist apporte une autorité compacte aux titres et aux chiffres. Inter garde les files, preuves, descriptions et contenus multilingues sobres et faciles à balayer.

### Hierarchy

- **Display** (600, échelle fluide, interligne 0,98) : titre de page court comme « Situation du jour ».
- **Headline** (700, 1 rem, interligne 1,25) : titres de panneau comme « Alertes prioritaires » ou « Analyse du jour ».
- **Title** (800, 1,45 rem, interligne 1) : valeurs KPI, avec chiffres tabulaires lorsque nécessaire.
- **Body** (400, 0,875 rem, interligne 1,5) : descriptions, alertes, analyses et verbatims ; viser une largeur de lecture de 65–75 caractères.
- **Label** (600, 0,625 rem, interligne 1,2) : intitulés KPI, dates, périodes, confiance et provenance.

### Named Rules

**The Two-Voice Rule.** Urbanist parle pour la hiérarchie et la décision ; Inter parle pour la preuve et l’interface.

**The Honest Density Rule.** Les tailles de 9–10 px sont réservées aux métadonnées courtes et ne portent jamais seules une information critique.

## Layout

Le contenu est centré dans un conteneur fluide plafonné à 1580 px, avec 16 px de marge mobile, 24 px dès les petits écrans et 32 px sur desktop. L’en-tête collant mesure au moins 84 px. À partir de 1024 px, un rail fixe de 88 px libère la largeur de travail ; sous ce seuil, le rail devient un panneau de 304 px et une navigation inférieure à cinq emplacements prend le relais.

Le dashboard suit une séquence stable. Les KPI utilisent deux colonnes par défaut et quatre à partir de 1024 px. La zone principale empile les blocs jusqu’à 1280 px, puis associe la file d’alertes et l’analyse du jour selon un rapport 1,55 / 0,75. Le résumé « Du signal à la décision » reste un panneau unique : ses trois étapes s’empilent, puis passent en trois colonnes égales à partir de 1024 px. Les panneaux produit et région utilisent une grille 1,1 / 0,9 sur desktop.

Le rythme s’appuie principalement sur 8, 12, 16, 20, 24, 28 et 32 px. Les lignes d’alerte ont une hauteur minimale de 72 px pour préserver la densité sans comprimer la cible. Sur mobile, l’ordre reste KPI, alertes, analyse, décision, détails ; le contenu conserve une marge basse suffisante pour la navigation fixe. Les textes arabes ou mixtes utilisent une direction automatique et l’architecture doit rester compatible avec un futur miroir RTL.

## Elevation & Depth

Le système utilise des couches claires : bordures douces pour segmenter, tonalités gris clair pour imbriquer, ombres diffuses pour détacher les panneaux du fond perle. Les KPI reçoivent une ombre plus courte que les grands panneaux. La lueur violette est limitée aux actions et états actifs. Les lignes d’alerte changent de fond au survol, sans déplacement ni modification de hauteur.

### Shadow Vocabulary

- **Stat:** `0 10px 28px hsl(var(--shadow-color) / 0.055)` — KPI compact.
- **Panel:** `0 14px 38px hsl(var(--shadow-color) / 0.07)` — file, analyse et résumé de décision.
- **Ambient:** `0 18px 48px hsl(var(--shadow-color) / 0.09)` — navigation mobile, menus et cartes flottantes.
- **Pulse glow:** `0 10px 24px hsl(var(--primary) / 0.22)` — bouton primaire et état actif.

### Named Rules

**The Stable Rows Rule.** Les files et synthèses restent immobiles au survol ; la profondeur s’exprime par le fond, la bordure ou la flèche d’action.

## Shapes

Les contrôles brefs utilisent des pilules complètes. Les icônes s’inscrivent dans des carrés adoucis de 32 à 38 px avec des rayons de 12 à 14,4 px. Les étapes de synthèse emploient 16 px, les KPI 20 px et les grands panneaux 24 px. Les bordures sont fines, continues et peu contrastées ; les séparateurs horizontaux structurent les files denses.

Les blocs restent strictement alignés au flux et à la grille. Les relations entre modules sont exprimées par l’ordre, l’espacement, les fonds tonals et les séparateurs continus.

## Components

### Buttons

Les boutons sont compacts, tactiles et explicites.

- **Shape:** pilule complète ; hauteur 36 px par défaut, 32 px en petit et 40 px en grand.
- **Primary:** violet électrique, texte blanc, 16 px de padding horizontal et lueur Pulse.
- **Hover / Focus:** translation maximale de 2 px réservée aux boutons, pression à 0,98 et anneau violet visible de 2 px.
- **Outline / Secondary / Ghost:** bordure Contour doux ou fond neutre, sans lueur persistante.
- **Action métier:** le bouton de décision peut devenir vert Action tout en gardant le contour de focus violet.

### Chips

Les pilules d’étape, de période et de statut sont des repères compacts.

- **Style:** fond neutre ou voile sémantique, texte 9–10 px, graisse 600–700 et padding 4 × 10 px.
- **State:** l’étape active devient violette avec texte blanc ; une confiance inconnue reste « à confirmer » et un résultat indisponible devient « Contrôle requis ».

### Cards / Containers

Les panneaux sont blancs, alignés et organisés par en-têtes, séparateurs et subdivisions tonales.

- **Corner Style:** 24 px pour les panneaux majeurs, 20 px pour les KPI, 16 px pour les étapes internes.
- **Background:** blanc panneau sur perle ; blanc doux pour les encarts et étapes.
- **Shadow Strategy:** ombre Stat sur les KPI, Panel sur les grands blocs et Ambient uniquement pour le flottant.
- **Border:** Contour doux à opacité réduite, continu.
- **Internal Padding:** 15,2 px sur les KPI ; 20 px sur mobile et 24 px dès les petits écrans pour les panneaux.

### Inputs / Fields

Les champs ressemblent à des outils intégrés à l’espace de travail.

- **Style:** fond Gris module, rayon complet pour la recherche globale, hauteur 44 px, icône à gauche et raccourci à droite.
- **Focus:** bordure violette légère et anneau violet translucide ; jamais de suppression du focus visible.
- **Error / Disabled:** rouge risque avec message associé ; opacité 50 % seulement si l’état est aussi exprimé fonctionnellement.

### Navigation

Le rail desktop est un axe compact de 88 px avec cibles carrées de 44 px, icônes seules et infobulles. L’élément actif devient violet avec texte blanc. L’en-tête expose les trois étapes métier sous forme de pilules et maintient la recherche au centre. Sur mobile, le rail devient un panneau libellé et la navigation inférieure réserve le centre à la création d’une surveillance.

### DashboardStat

Le KPI associe une icône sémantique dans un carré teinté, un libellé Inter de 10 px et une valeur Urbanist de 1,45 rem. Quatre cartes ouvrent la situation : perception, évolution, avis analysés et alertes à traiter. La valeur n’utilise jamais la couleur seule pour communiquer sa tendance.

### AlertQueue

Le panneau « Alertes prioritaires » possède un en-tête avec action « Tout afficher », puis jusqu’à quatre lignes de 72 px minimum. Chaque ligne montre une icône de risque, un titre, un résumé, une gravité, un horodatage et une flèche. Sur mobile, gravité et heure passent sous le texte ; les résumés sont tronqués sans cacher le titre ni l’accès à la fiche.

### AnalysisCard

« Analyse du jour » montre la période, une synthèse, le signal le mieux étayé, la confiance et le nombre d’avis, puis un bouton « Voir les preuves ». La confiance absente reste « à confirmer » ; la carte ne transforme jamais une synthèse en certitude.

### DecisionSummary

Le panneau « Du signal à la décision » aligne trois étapes claires dans des encarts Blanc doux : signal détecté avec preuve, interprétation avec résumé, décision proposée avec confiance ou contrôle requis. Les étapes sont en trois colonnes sur desktop et s’empilent sur mobile. La décision reste soumise à validation humaine.

## Do's and Don'ts

### Do:

- **Do** ouvrir la situation par quatre KPI compacts qui cadrent le volume, la tendance et l’urgence.
- **Do** garder le fond général perle et réserver les surfaces blanches aux modules de travail.
- **Do** montrer la source, la fraîcheur, la confiance ou « à confirmer », et un accès aux preuves au point où une conclusion est présentée.
- **Do** utiliser le violet électrique pour l’identité, l’actif, le focus et l’action primaire.
- **Do** conserver l’ordre Signal → Interprétation → Décision et la validation humaine.
- **Do** préserver des cibles d’au moins 40 px, et 44 px sur mobile.
- **Do** neutraliser les transitions et animations non essentielles avec `prefers-reduced-motion`.

### Don't:

- **Don't** introduire de rupture visuelle spectaculaire dans le parcours décisionnel.
- **Don't** désaligner les modules ou interrompre le flux régulier de la grille.
- **Don't** agrandir un signal au point d’écraser la file, l’analyse ou la synthèse de décision.
- **Don't** inventer une source, une fraîcheur, une confiance, une recommandation ou une certitude absente.
- **Don't** faire dépendre un état de la couleur seule, ni mélanger des styles d’icônes dans une même surface.
- **Don't** masquer le début du bloc suivant sous la navigation mobile fixe.
