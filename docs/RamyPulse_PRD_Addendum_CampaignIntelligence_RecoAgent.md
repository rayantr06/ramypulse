# RamyPulse — PRD Addendum : Campaign Intelligence & AI Recommendation Agent

---

| Champ | Valeur |
|---|---|
| Document | Addendum au PRD Technique v2.0 |
| Version | 1.0 — 30 mars 2026 |
| Statut | Spécification active — à intégrer dans le PRD v2.0 après validation |
| Périmètre | Deux nouveaux modules : Campaign Intelligence (Wave 5.3) + AI Recommendation Agent (Wave 5.4) |
| Dépendance | PRD v2.0 complet — ces modules s'appuient sur les tables Wave 5.1 et 5.2 |

---

## Contexte et motivation

Le PRD v2.0 couvre le cycle suivant :

```
Collecter → Normaliser → Surveiller → Détecter → Alerter
```

Ce cycle est nécessaire. Il n'est pas suffisant.

Un client comme Ramy doit aussi répondre à deux questions que le système actuel ne peut pas encore adresser explicitement :

**Question 1 — Attribution**
"On a lancé une campagne Instagram avec un influenceur en mars. Est-ce que ça a eu un impact réel sur les avis, le NSS, et la perception du packaging dans l'est ? Combien ?"

**Question 2 — Action**
"Le NSS livraison Oran est en chute depuis 3 semaines. Le système l'a détecté. Maintenant, qu'est-ce que je fais concrètement ? Quelle action marketing ?"

Ces deux questions définissent les deux modules de cet addendum.

**Module A — Campaign Intelligence**
Suivi structuré d'un événement marketing (campagne, sponsoring, pub, influenceur) avec mesure d'impact réel avant / pendant / après sur les métriques RamyPulse.

**Module B — AI Recommendation Agent**
Agent intelligent appelé via clé API, qui reçoit le contexte complet (RAG + watchlists + alertes actives + historique campagnes) et génère des recommandations marketing actionnables : type de campagne, profil influenceur, hooks créatifs, script adapté, timing.

Ces deux modules sont complémentaires et forment ensemble une couche décisionnelle au-dessus de la couche de surveillance.

---

## Module A — Campaign Intelligence

### A.1 Définition

Un événement marketing dans RamyPulse est une entité structurée représentant :
- une campagne publicitaire
- un partenariat influenceur
- un sponsoring
- un lancement produit
- une promotion temporaire
- tout autre action commerciale dont on veut mesurer l'impact sur les signaux collectés

Le module Campaign Intelligence n'est pas un CRM. Il ne gère pas les budgets, les briefs créatifs, ou les relations partenaires. Sa responsabilité unique est de relier un événement marketing aux données de perception collectées, pour permettre de mesurer l'uplift réel.

### A.2 Concept central — Fenêtre d'attribution

La mesure d'impact repose sur la définition de trois fenêtres temporelles autour d'un événement :

```
─────────────────────────────────────────────────────────────────►  Temps
│                    │                         │                  │
│   PRE-CAMPAIGN     │      ACTIVE             │   POST-CAMPAIGN  │
│   (baseline)       │      (en cours)         │   (impact)       │
│                    │                         │                  │
└────────────────────┴─────────────────────────┴──────────────────┘
    start_date - N jours      start_date             end_date + M jours
    (configurable, défaut 14)                         (configurable, défaut 14)
```

**Fenêtre PRE (baseline)** : période de référence avant la campagne. Calcule le NSS de base, le volume de base, la distribution des aspects avant tout effet de la campagne.

**Fenêtre ACTIVE** : période de la campagne en cours. Calcule les métriques en temps réel pendant la campagne pour détecter les effets immédiats.

**Fenêtre POST** : période d'observation après la fin de la campagne. Mesure l'effet résiduel, la durabilité de l'impact, le retour à la baseline.

### A.3 Dimensions d'attribution

Pour chaque campagne, l'utilisateur configure les dimensions de filtrage qui vont délimiter le périmètre des signaux attribués :

| Dimension | Exemple | Logique |
|---|---|---|
| `platform` | instagram | Filtrer les signaux de ce canal |
| `target_region` | [Oran, Tlemcen, Sidi Bel Abbès] | Périmètre géographique ciblé |
| `target_aspect` | [packaging, goût] | Aspects surveillés |
| `target_segment` | gen_z | Segment audience (influenceur Gen Z → audience présumée jeune) |
| `keywords` | ["ramy", "jus", "bouteille"] | Mots-clés spécifiques à détecter dans les signaux |
| `influencer_handle` | @handle_insta | Handle pour filtrer les mentions directes dans les commentaires |

La logique d'attribution applique ces filtres sur `enriched_signals` dans la fenêtre temporelle concernée.

**Note importante** : L'attribution est corrélative, pas causale. RamyPulse ne peut pas prouver qu'une hausse du NSS est causée par la campagne — il peut mesurer la coïncidence temporelle et spatiale entre la campagne et les métriques. C'est à l'utilisateur d'interpréter.

### A.4 Modèle de données — Module Campaign Intelligence

#### Table `campaigns`

```sql
CREATE TABLE campaigns (
    campaign_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id               UUID NOT NULL REFERENCES clients(client_id),
    campaign_name           VARCHAR(255) NOT NULL,
    campaign_type           VARCHAR(50) NOT NULL,    -- influencer, paid_ad, sponsoring, launch, promotion, organic
    platform                VARCHAR(50) NOT NULL,    -- instagram, facebook, youtube, tiktok, offline, multi_platform
    description             TEXT,
    influencer_handle       VARCHAR(255),            -- @handle, optionnel
    influencer_tier         VARCHAR(30),             -- nano (<10k), micro (10k-100k), macro (100k-1M), mega (>1M)
    target_segment          VARCHAR(100),            -- gen_z, millennial, family, women_25_35, etc.
    target_aspects          TEXT[],                  -- ['packaging', 'gout', 'disponibilite']
    target_regions          TEXT[],                  -- ['oran', 'tlemcen']
    keywords                TEXT[],                  -- mots-clés à tracker
    budget_dza              BIGINT,                  -- budget en dinars algériens, optionnel
    start_date              DATE NOT NULL,
    end_date                DATE NOT NULL,
    pre_window_days         INTEGER NOT NULL DEFAULT 14,
    post_window_days        INTEGER NOT NULL DEFAULT 14,
    status                  VARCHAR(30) NOT NULL DEFAULT 'planned',  -- planned, active, completed, cancelled
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT campaign_dates CHECK (end_date >= start_date)
);
```

#### Table `campaign_metrics_snapshots`

Snapshots calculés des métriques par phase de campagne. Recalculé à chaque cycle du job de monitoring campagne.

```sql
CREATE TABLE campaign_metrics_snapshots (
    snapshot_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID NOT NULL REFERENCES campaigns(campaign_id),
    phase               VARCHAR(20) NOT NULL,   -- pre, active, post
    metric_date         DATE NOT NULL,
    nss_filtered        FLOAT,      -- NSS sur les signaux filtrés par les dimensions de la campagne
    nss_baseline        FLOAT,      -- NSS pre-campaign (répété pour comparaison facile)
    nss_uplift          FLOAT,      -- nss_filtered - nss_baseline
    volume_filtered     INTEGER,    -- volume de signaux filtrés dans cette fenêtre
    volume_baseline     INTEGER,    -- volume moyen baseline (répété pour comparaison)
    volume_lift_pct     FLOAT,      -- % de variation volume vs baseline
    aspect_breakdown    JSONB,      -- {goût: {nss: 45, volume: 120}, packaging: {nss: 62, volume: 89}}
    sentiment_breakdown JSONB,      -- {très_positif: 0.25, positif: 0.40, neutre: 0.20, ...}
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(campaign_id, phase, metric_date)
);
```

#### Table `campaign_signal_links`

Lien explicite entre un signal et une campagne (attribution dans la fenêtre temporelle et le périmètre).

```sql
CREATE TABLE campaign_signal_links (
    link_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID NOT NULL REFERENCES campaigns(campaign_id),
    signal_id           UUID NOT NULL REFERENCES enriched_signals(signal_id),
    phase               VARCHAR(20) NOT NULL,   -- pre, active, post
    attribution_score   FLOAT,                  -- 0 à 1 — confiance de l'attribution (keywords match, handle mention, etc.)
    attributed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_campaign_signal_links_campaign ON campaign_signal_links(campaign_id, phase);
```

### A.5 Algorithme de calcul d'impact campagne

```python
async def compute_campaign_impact(campaign_id: str) -> dict:
    campaign = await db.fetchrow(
        "SELECT * FROM campaigns WHERE campaign_id = :id", {"id": campaign_id}
    )

    # Définir les fenêtres temporelles
    pre_start  = campaign.start_date - timedelta(days=campaign.pre_window_days)
    pre_end    = campaign.start_date - timedelta(days=1)
    active_start = campaign.start_date
    active_end   = campaign.end_date
    post_start = campaign.end_date + timedelta(days=1)
    post_end   = campaign.end_date + timedelta(days=campaign.post_window_days)

    phases = {
        "pre":    (pre_start, pre_end),
        "active": (active_start, active_end),
        "post":   (post_start, post_end),
    }

    results = {}
    for phase_name, (start, end) in phases.items():
        # Construction dynamique du filtre SQL selon les dimensions de la campagne
        signals = await fetch_signals_for_campaign(
            client_id=campaign.client_id,
            start=start,
            end=end,
            platform=campaign.platform,
            target_regions=campaign.target_regions,
            target_aspects=campaign.target_aspects,
            keywords=campaign.keywords,
            influencer_handle=campaign.influencer_handle,
        )

        if not signals:
            results[phase_name] = {"nss": None, "volume": 0}
            continue

        df = pd.DataFrame(signals)
        nss = nss_calculator.calculate(df)
        aspect_breakdown = nss_calculator.calculate_by_aspect(df)
        sentiment_breakdown = nss_calculator.calculate_distribution(df)

        # Calculer l'attribution_score pour chaque signal
        for signal in signals:
            score = compute_attribution_score(signal, campaign)
            await db.execute(
                INSERT_campaign_signal_link,
                {"campaign_id": campaign_id, "signal_id": signal.signal_id,
                 "phase": phase_name, "attribution_score": score}
            )

        results[phase_name] = {
            "nss": nss,
            "volume": len(signals),
            "aspect_breakdown": aspect_breakdown,
            "sentiment_breakdown": sentiment_breakdown,
        }

    # Calculer l'uplift
    pre_nss  = results.get("pre", {}).get("nss")
    post_nss = results.get("post", {}).get("nss")
    uplift   = round(post_nss - pre_nss, 2) if pre_nss is not None and post_nss is not None else None

    return {
        "campaign_id": campaign_id,
        "phases": results,
        "uplift_nss": uplift,
        "uplift_volume_pct": compute_volume_lift(results.get("pre"), results.get("post")),
    }


def compute_attribution_score(signal: dict, campaign: dict) -> float:
    """
    Score entre 0 et 1 indiquant la confiance de l'attribution du signal à la campagne.
    Basé sur les dimensions correspondantes.
    """
    score = 0.3  # Base : fenêtre temporelle et plateforme correspondent déjà

    text = signal.get("text", "").lower()

    # Mention du handle influenceur dans le texte
    if campaign.get("influencer_handle") and campaign["influencer_handle"].lower() in text:
        score += 0.4

    # Correspondance de keywords
    keywords = campaign.get("keywords", [])
    matched_kw = sum(1 for kw in keywords if kw.lower() in text)
    score += min(0.2, matched_kw * 0.05)

    # Correspondance d'aspect
    if signal.get("aspect") in (campaign.get("target_aspects") or []):
        score += 0.1

    return round(min(score, 1.0), 3)
```

### A.6 Vue dashboard Campaign Intelligence

**Page `pages/05_campaigns.py`**

Cette page expose :

**Section 1 — Liste des campagnes**
- Tableau : nom, type, plateforme, période, statut, NSS uplift calculé, volume lift
- Bouton "Créer une campagne" (formulaire inline)
- Filtres : statut, plateforme, période

**Section 2 — Vue détaillée d'une campagne**

Sélectionner une campagne → afficher :

- **Timeline visuelle** : bande colorée pré / active / post avec les dates
- **KPI cards** :
  - NSS pré-campagne (baseline)
  - NSS post-campagne
  - Uplift NSS (delta + flèche directionnelle colorée)
  - Volume lift en %
  - Volume total de signaux attribués
- **Graphique évolution NSS** : courbe NSS jour par jour avec zones colorées pré/active/post + ligne de baseline pointillée
- **Matrice ABSA avant/après** : deux heatmaps côte à côte — aspects × sentiments pré vs post
- **Top signaux attribués** : les 10 commentaires les plus représentatifs avec score d'attribution

**Section 3 — Comparaison multi-campagnes**
- Si > 1 campagne disponible : bar chart comparatif des uplifts NSS par campagne
- Scatter : uplift NSS vs volume lift — pour identifier les campagnes "signal fort"

**Critères d'acceptation** :
- NSS uplift calculé correctement sur au moins 3 scénarios de test
- Fenêtre temporelle configurable (les 14 jours par défaut sont modifiables)
- Zéro inter-client (filtrage `client_id` strict sur toutes les queries)
- La page charge en < 4 secondes
- Scénario "campagne sans données" géré proprement (message + invitation à importer)

### A.7 Intégration avec le moteur d'alertes

Les campagnes s'intègrent avec les alertes existantes via deux mécanismes :

**Alerte type `campaign_impact_positive`**
Déclenchée si l'uplift NSS dépasse un seuil défini dans `alert_rules` pendant la fenêtre active ou post.
Exemple : "La campagne Influenceur Instagram Oran a généré un uplift NSS packaging de +12 points."

**Alerte type `campaign_underperformance`**
Déclenchée si la campagne est active depuis > 7 jours et l'uplift est négatif ou nul, avec volume de signaux suffisant (> 50) pour être statistiquement significatif.
Exemple : "La campagne Instagram Gen Z est active depuis 8 jours. NSS packaging inchangé. Volume attribué : 63 signaux."

**Lien watchlist → campagne**
Si une watchlist détecte une dérive pendant une période de campagne active, l'alerte générée inclut dans `alert_payload` une référence à la campagne en cours, pour contextualiser l'information.

```json
{
  "alert_payload": {
    "metric_current": 38,
    "metric_previous": 47,
    "delta": -9,
    "active_campaigns": [
      {
        "campaign_id": "uuid",
        "campaign_name": "Influenceur Instagram Oran Mars 2026",
        "phase": "active",
        "current_uplift": -2.3
      }
    ],
    "context": "Cette baisse survient pendant une campagne active sur le même périmètre."
  }
}
```

### A.8 Placement dans la roadmap

Campaign Intelligence est ajouté en **Wave 5.3**, en parallèle des watchlists.

Justification : les watchlists définissent les périmètres à surveiller. Les campagnes définissent les événements à mesurer. Les deux partagent la même logique de filtrage par dimensions (produit, région, canal, aspect) et les mêmes tables sous-jacentes (`enriched_signals`).

**Livrables Wave 5.3 additionnels** :
- Tables `campaigns`, `campaign_metrics_snapshots`, `campaign_signal_links`
- Fonction `compute_campaign_impact` avec job périodique (toutes les heures si campagne active)
- Page `pages/05_campaigns.py` complète
- Intégration alertes `campaign_impact_positive` et `campaign_underperformance`

**Critère de sortie Wave 5.3** :
Un utilisateur peut créer une campagne "Influenceur Instagram packaging Oran, 1–15 mars", configurer sa fenêtre pré/post, et voir l'uplift NSS calculé automatiquement avec les signaux attribués.

---

## Module B — AI Recommendation Agent

### B.1 Définition

L'AI Recommendation Agent est un module de génération de recommandations marketing actionnables, appelé via clé API externe, qui reçoit un contexte structuré construit à partir des données RamyPulse et produit des recommandations concrètes.

Ce n'est pas une interface de chat libre.

C'est une boucle fermée et structurée :

```
CONTEXTE ASSEMBLÉ (RamyPulse)
      ↓
   API KEY (OpenAI / Anthropic / Ollama)
      ↓
   AGENT INTELLIGENT
      ↓
RECOMMANDATIONS STRUCTURÉES (JSON)
      ↓
  UI RECOMMENDATIONS CENTER
```

La différence avec le chat RAG existant est fondamentale :

| Chat RAG | AI Recommendation Agent |
|---|---|
| Répond à une question de l'utilisateur | Génère des recommandations sans question |
| Contexte = chunks vectoriels | Contexte = watchlists + alertes + campagnes + RAG |
| Output = texte libre | Output = JSON structuré (type, cible, hooks, script, timing) |
| Logique pull | Logique push |
| Explicatif | Prescriptif |

### B.2 Déclencheurs

Le Recommendation Agent peut être appelé de trois façons :

**Déclenchement manuel**
L'utilisateur clique sur "Générer des recommandations" depuis n'importe quelle vue (watchlist, alerte, campagne). Le système assemble le contexte lié à ce périmètre et appelle l'agent.

**Déclenchement automatique sur alerte critique**
Quand une alerte de sévérité `critical` ou `high` est créée, le système peut automatiquement appeler l'agent pour générer des recommandations liées à cette alerte. Les recommandations sont stockées et affichées dans le centre d'alertes à côté de l'alerte concernée.

Ce comportement est configurable par client (activé ou désactivé dans les préférences).

**Déclenchement planifié**
Un job hebdomadaire génère un rapport de recommandations global à partir de l'état courant de toutes les watchlists actives. Livré par notification (e-mail ou Slack).

### B.3 Architecture du Context Builder

L'assembleur de contexte est la pièce la plus critique du module. Sa responsabilité est de construire un payload riche et pertinent à partir des données RamyPulse avant d'appeler l'API externe.

```python
async def build_recommendation_context(
    client_id: str,
    trigger_type: str,           # manual, alert_triggered, scheduled
    trigger_id: Optional[str],   # alert_id ou watchlist_id ou campaign_id
    max_tokens: int = 3000       # Limite le contexte pour rester dans les limites API
) -> dict:

    context = {
        "client_profile": await get_client_profile(client_id),
        "current_state": {},
        "active_alerts": [],
        "campaign_context": [],
        "rag_insights": [],
        "trigger": {"type": trigger_type, "id": trigger_id}
    }

    # 1. État actuel des watchlists (top 5 watchlists par criticité)
    watchlists = await db.fetch_all("""
        SELECT w.watchlist_name, w.scope_type,
               latest_metric.nss_value, latest_metric.volume,
               latest_metric.delta_vs_previous
        FROM watchlists w
        JOIN (
            SELECT DISTINCT ON (watchlist_id)
                   watchlist_id, nss_value, volume, delta_vs_previous
            FROM watchlist_metric_snapshots
            ORDER BY watchlist_id, computed_at DESC
        ) latest_metric ON latest_metric.watchlist_id = w.watchlist_id
        WHERE w.client_id = :client_id AND w.is_active = true
        ORDER BY ABS(latest_metric.delta_vs_previous) DESC NULLS LAST
        LIMIT 5
    """, {"client_id": client_id})
    context["current_state"]["watchlists"] = [dict(w) for w in watchlists]

    # 2. Alertes actives (non résolues, triées par sévérité)
    active_alerts = await db.fetch_all("""
        SELECT title, description, severity, detected_at, alert_payload
        FROM alerts
        WHERE client_id = :client_id
          AND status IN ('new', 'acknowledged', 'investigating')
        ORDER BY
            CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                          WHEN 'medium' THEN 3 ELSE 4 END,
            detected_at DESC
        LIMIT 10
    """, {"client_id": client_id})
    context["active_alerts"] = [dict(a) for a in active_alerts]

    # 3. Contexte campagnes actives ou récentes (< 30 jours)
    campaigns = await db.fetch_all("""
        SELECT c.campaign_name, c.campaign_type, c.platform,
               c.influencer_tier, c.target_segment, c.target_aspects,
               c.target_regions, c.status,
               latest_snap.nss_uplift, latest_snap.volume_lift_pct
        FROM campaigns c
        LEFT JOIN (
            SELECT DISTINCT ON (campaign_id)
                   campaign_id, nss_uplift, volume_lift_pct
            FROM campaign_metrics_snapshots
            ORDER BY campaign_id, computed_at DESC
        ) latest_snap ON latest_snap.campaign_id = c.campaign_id
        WHERE c.client_id = :client_id
          AND (c.status IN ('active', 'completed') AND c.end_date > NOW() - INTERVAL '30 days')
        ORDER BY c.start_date DESC
        LIMIT 5
    """, {"client_id": client_id})
    context["campaign_context"] = [dict(c) for c in campaigns]

    # 4. Insights RAG — Top 10 chunks les plus pertinents selon le contexte du déclencheur
    trigger_query = await build_trigger_query(trigger_type, trigger_id)
    if trigger_query:
        rag_chunks = await retriever.search(trigger_query, top_k=10)
        context["rag_insights"] = [
            {"text": chunk.text, "channel": chunk.channel, "timestamp": str(chunk.timestamp)}
            for chunk in rag_chunks
        ]

    # Estimation tokens et troncature si nécessaire
    context = truncate_context_to_budget(context, max_tokens)

    return context
```

### B.4 Construction du prompt système

Le prompt système est la définition du rôle de l'agent. Il est fixe, versionné, et ne doit pas être modifiable par l'utilisateur final.

```python
RECOMMENDATION_AGENT_SYSTEM_PROMPT = """
Tu es un expert en stratégie marketing digital pour le marché algérien, spécialisé dans l'industrie agroalimentaire et les boissons.

Tu vas recevoir des données structurées issues d'une plateforme d'analyse de sentiment (RamyPulse) pour la marque Ramy.

Ton travail est de générer des recommandations marketing concrètes et actionnables basées UNIQUEMENT sur ces données.

RÈGLES STRICTES :
- Ne génère JAMAIS de recommandations sans base dans les données fournies
- Chaque recommandation doit être liée à un signal, une métrique, ou une alerte spécifique
- Adapte toujours le ton et le style au canal et au segment cible
- Le marché algérien a ses spécificités culturelles : respecte-les (Darija, références locales, contexte socio-culturel)
- Si les données sont insuffisantes pour une recommandation fiable, indique-le explicitement

FORMAT DE RÉPONSE :
Réponds UNIQUEMENT en JSON valide. Aucun texte avant ou après.

Structure obligatoire :
{
  "analysis_summary": "string — 2-3 phrases résumant la situation détectée",
  "recommendations": [
    {
      "id": "rec_001",
      "priority": "critical|high|medium|low",
      "type": "influencer_campaign|paid_ad|content_organic|community_response|product_action|distribution_action",
      "title": "string — titre court et actionnable",
      "rationale": "string — pourquoi cette recommandation, liée aux données",
      "target_platform": "instagram|facebook|youtube|tiktok|offline|multi_platform",
      "target_segment": "string — ex: gen_z_18_25, famille_algéroise, hommes_actifs",
      "target_regions": ["string"],
      "target_aspects": ["string"],
      "timing": {
        "urgency": "immediate|within_week|within_month",
        "best_moment": "string — ex: weekend matin, période ramadan, après-match"
      },
      "influencer_profile": {
        "tier": "nano|micro|macro|mega|none",
        "niche": "string — ex: lifestyle algérien, food content, sport",
        "tone": "string — ex: authentique darija, humoristique, aspirationnel",
        "engagement_focus": "string"
      },
      "content": {
        "hooks": ["string", "string", "string"],
        "script_outline": "string — 3-5 phrases décrivant la structure du contenu",
        "key_messages": ["string"],
        "visual_direction": "string — direction créative visuelle",
        "call_to_action": "string"
      },
      "kpi_to_track": ["string"],
      "data_basis": "string — référence explicite aux données RamyPulse ayant motivé cette recommandation"
    }
  ],
  "watchlist_priorities": ["string — watchlists à surveiller en priorité après ces actions"],
  "confidence_score": 0.0,
  "data_quality_note": "string — qualité et quantité des données disponibles pour cette analyse"
}
"""
```

### B.5 Appel API externe

Le module supporte plusieurs providers via une interface unifiée.

```python
class RecommendationAgentClient:
    """
    Interface unifiée pour l'appel à un LLM externe (OpenAI, Anthropic, ou Ollama local).
    Le provider est sélectionné selon la configuration client dans `client_agent_config`.
    """

    async def generate(
        self,
        context: dict,
        client_id: str
    ) -> dict:
        config = await get_client_agent_config(client_id)

        user_prompt = self._build_user_prompt(context)

        if config.provider == "anthropic":
            return await self._call_anthropic(
                api_key=decrypt_secret(config.api_key_encrypted),
                model=config.model or "claude-sonnet-4-20250514",
                system=RECOMMENDATION_AGENT_SYSTEM_PROMPT,
                user=user_prompt,
                max_tokens=2000
            )
        elif config.provider == "openai":
            return await self._call_openai(
                api_key=decrypt_secret(config.api_key_encrypted),
                model=config.model or "gpt-4o",
                system=RECOMMENDATION_AGENT_SYSTEM_PROMPT,
                user=user_prompt,
                max_tokens=2000
            )
        elif config.provider == "ollama_local":
            return await self._call_ollama(
                model=config.model or "qwen2.5:14b",
                system=RECOMMENDATION_AGENT_SYSTEM_PROMPT,
                user=user_prompt
            )
        else:
            raise ValueError(f"Provider non supporté : {config.provider}")

    def _build_user_prompt(self, context: dict) -> str:
        return f"""
Voici les données de la plateforme RamyPulse pour cette analyse :

CLIENT : {context['client_profile']['client_name']}
DÉCLENCHEUR : {context['trigger']['type']} — {context['trigger'].get('id', 'global')}

=== ÉTAT ACTUEL DES WATCHLISTS ===
{json.dumps(context['current_state']['watchlists'], ensure_ascii=False, indent=2)}

=== ALERTES ACTIVES ({len(context['active_alerts'])} alertes non résolues) ===
{json.dumps(context['active_alerts'], ensure_ascii=False, indent=2)}

=== CAMPAGNES RÉCENTES ===
{json.dumps(context['campaign_context'], ensure_ascii=False, indent=2)}

=== EXTRAITS SOURCES PERTINENTS ===
{json.dumps(context['rag_insights'], ensure_ascii=False, indent=2)}

Génère les recommandations marketing les plus actionnables pour cette situation.
Réponds UNIQUEMENT en JSON selon le format défini.
"""

    async def _call_anthropic(self, api_key, model, system, user, max_tokens) -> dict:
        import httpx
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}]
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            raw_text = data["content"][0]["text"]
            return self._parse_json_response(raw_text)

    async def _call_ollama(self, model, system, user) -> dict:
        import httpx
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": False,
            "format": "json"  # Forcer JSON output si Ollama le supporte
        }
        async with httpx.AsyncClient(timeout=120, base_url=OLLAMA_BASE_URL) as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return self._parse_json_response(data["message"]["content"])

    def _parse_json_response(self, raw_text: str) -> dict:
        """Parse le JSON avec fallback robuste."""
        try:
            # Tenter un parse direct
            return json.loads(raw_text)
        except json.JSONDecodeError:
            # Nettoyer les fences markdown si présentes
            cleaned = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                # Si le JSON est invalide, retourner une structure d'erreur exploitable
                return {
                    "analysis_summary": "Erreur de parsing de la réponse agent.",
                    "recommendations": [],
                    "confidence_score": 0.0,
                    "data_quality_note": f"JSON parse error: {str(e)}",
                    "raw_response": raw_text[:500]
                }
```

### B.6 Modèle de données — Module Recommendation Agent

#### Table `client_agent_config`

```sql
CREATE TABLE client_agent_config (
    config_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id               UUID NOT NULL REFERENCES clients(client_id) UNIQUE,
    provider                VARCHAR(30) NOT NULL DEFAULT 'ollama_local',  -- anthropic, openai, ollama_local
    model                   VARCHAR(100),
    api_key_encrypted       TEXT,           -- Chiffré via vault — jamais en clair
    auto_trigger_on_alert   BOOLEAN NOT NULL DEFAULT FALSE,
    auto_trigger_severity   VARCHAR(20) DEFAULT 'critical',  -- Seuil minimum pour déclenchement auto
    weekly_report_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
    weekly_report_day       INTEGER DEFAULT 1,   -- 1=Lundi ... 7=Dimanche
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table `recommendations`

```sql
CREATE TABLE recommendations (
    recommendation_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID NOT NULL REFERENCES clients(client_id),
    trigger_type        VARCHAR(30) NOT NULL,   -- manual, alert_triggered, scheduled
    trigger_id          UUID,                   -- alert_id ou watchlist_id ou campaign_id
    alert_id            UUID REFERENCES alerts(alert_id),
    analysis_summary    TEXT,
    recommendations     JSONB NOT NULL,         -- Array des recommandations structurées
    watchlist_priorities TEXT[],
    confidence_score    FLOAT,
    data_quality_note   TEXT,
    provider_used       VARCHAR(30),
    model_used          VARCHAR(100),
    context_tokens      INTEGER,                -- Estimation tokens du contexte envoyé
    generation_ms       INTEGER,                -- Temps de génération en millisecondes
    status              VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, archived, dismissed
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recommendations_client_recent
    ON recommendations(client_id, created_at DESC);

CREATE INDEX idx_recommendations_trigger
    ON recommendations(trigger_id)
    WHERE trigger_id IS NOT NULL;
```

### B.7 Recommendation Center — Page `pages/06_recommendations.py`

**Layout de la page :**

**Section 1 — Générer maintenant**

- Selectbox : "Générer pour..." → Global / Watchlist spécifique / Alerte spécifique / Campagne spécifique
- Sélection du périmètre si pertinent
- Bouton "Générer les recommandations"
- Spinner pendant la génération avec message : "Analyse en cours — assemblage du contexte, appel à l'agent..."

**Section 2 — Recommandations actives**

Pour chaque recommandation générée, carte expandable :

```
┌──────────────────────────────────────────────────────────────────┐
│  🔴 CRITICAL  │  Influenceur micro-taille, Instagram, Oran       │
│  Campagne influenceur  │  Généré il y a 2h                       │
├──────────────────────────────────────────────────────────────────┤
│  POURQUOI                                                         │
│  NSS livraison Oran en baisse de 14 pts sur Google Maps.         │
│  Volume négatif +38% vs baseline. 3 semaines consécutives.       │
├──────────────────────────────────────────────────────────────────┤
│  CIBLE : Gen Z 18–25 · Oran · Instagram · Aspect : disponibilité │
├──────────────────────────────────────────────────────────────────┤
│  PROFIL INFLUENCEUR                                               │
│  Tier : Micro (20k–80k) · Niche : Lifestyle algérien / food      │
│  Ton : Authentique Darija, humoristique                           │
├──────────────────────────────────────────────────────────────────┤
│  HOOKS                                                            │
│  • "Fin ki t7eb tramy w ma tlgahach 😤"                          │
│  • "RamyPulse dit Ramy manque à Oran — est-ce que c'est vrai ?"  │
│  • "3 endroits à Oran où RamyPulse est toujours là 🧃"           │
├──────────────────────────────────────────────────────────────────┤
│  OUTLINE DU SCRIPT                                                │
│  Ouvrir avec la frustration de ne pas trouver Ramy. Montrer      │
│  une recherche dans 3 épiceries. Trouver Ramy. Réaction positive.│
│  Call-to-action : commenter son quartier dans les commentaires.   │
├──────────────────────────────────────────────────────────────────┤
│  KPIs À SUIVRE : NSS disponibilité Oran · Volume Google Maps Oran│
├──────────────────────────────────────────────────────────────────┤
│  [Marquer utile ✓]  [Archiver]  [Créer une campagne depuis cette reco]│
└──────────────────────────────────────────────────────────────────┘
```

**Section 3 — Historique des recommandations**

Tableau paginé : date, déclencheur, nb recommandations, confidence_score, provider, statut.

**Section 4 — Configuration de l'agent**

- Provider sélectionné (Anthropic / OpenAI / Ollama local)
- Modèle (champ texte)
- Saisie clé API (masquée, stockée chiffrée)
- Toggle : auto-trigger sur alertes critical/high
- Toggle : rapport hebdomadaire avec sélection du jour

**Critères d'acceptation de la page** :
- La génération produit un JSON valide dans 100% des cas (le fallback `_parse_json_response` gère les erreurs)
- Les hooks sont en Darija ou Français selon la cible (pas en MSA formel)
- Le champ `data_basis` dans chaque recommandation est systématiquement rempli (pas de recommandation orpheline de données)
- La clé API n'apparaît jamais dans les logs, le front, ou les payloads de debug
- Le bouton "Créer une campagne depuis cette reco" pré-remplit le formulaire de création de campagne avec les dimensions de la recommandation

### B.8 Flux complet — Alerte → Recommandation automatique

```
1. alert_detection_job crée une alerte severity='critical' (ex: NSS livraison Oran -14 pts)

2. Alert post-processor vérifie la config client :
   - auto_trigger_on_alert = true ?
   - severity >= auto_trigger_severity ?

3. Si oui : job async `trigger_recommendation_agent`
   a. build_recommendation_context(client_id, trigger_type='alert_triggered', trigger_id=alert_id)
   b. RecommendationAgentClient.generate(context, client_id)
   c. INSERT INTO recommendations avec alert_id lié

4. L'alerte dans la DB est mise à jour :
   UPDATE alerts SET alert_payload = alert_payload || '{"has_recommendations": true, "recommendation_id": "uuid"}'

5. Dans le centre d'alertes, l'alerte affiche un badge :
   "🤖 Recommandations générées — voir les actions proposées"

6. L'utilisateur clique → navigation vers recommendations/uuid
```

### B.9 Intégration dans le rapport hebdomadaire (Wave 5.5)

Si `weekly_report_enabled = true`, un job le jour sélectionné :

1. Assemble un contexte global (toutes les watchlists actives + alertes de la semaine + campagnes en cours)
2. Appelle l'agent avec un prompt légèrement adapté : "Génère le bilan de la semaine et les priorités d'action pour la semaine prochaine."
3. Formate le résultat en rapport e-mail structuré
4. Envoie via SMTP ou Slack webhook

### B.10 Placement dans la roadmap

**Wave 5.4** — Recommandation Agent (ajout aux livrables existants de Wave 5.4)

Justification : le module d'alertes doit être opérationnel avant de pouvoir déclencher des recommandations. Campaign Intelligence (Wave 5.3) enrichit le contexte disponible — il est préférable de l'avoir avant de lancer l'agent.

**Livrables Wave 5.4 additionnels** :
- Tables `client_agent_config`, `recommendations`
- Module `core/recommendation_agent/context_builder.py`
- Module `core/recommendation_agent/agent_client.py` (providers Anthropic, OpenAI, Ollama)
- Module `core/recommendation_agent/prompt_manager.py` (versions du prompt système)
- Page `pages/06_recommendations.py`
- Alert post-processor avec déclenchement auto configurable
- Intégration du lien alerte ↔ recommandation dans le centre d'alertes

**Critère de sortie Wave 5.4** :
Un utilisateur avec une clé API Anthropic configurée peut cliquer sur une alerte "NSS livraison Oran en chute" et recevoir en < 60 secondes 3 recommandations concrètes avec hooks en Darija, profil influenceur, et outline de script.

---

## Synthèse — Impact sur le PRD v2.0

### Nouvelles tables à ajouter (Section 8 — Modèle de données)

| Table | Wave | Dépendance |
|---|---|---|
| `campaigns` | 5.3 | `clients` |
| `campaign_metrics_snapshots` | 5.3 | `campaigns`, `enriched_signals` |
| `campaign_signal_links` | 5.3 | `campaigns`, `enriched_signals` |
| `client_agent_config` | 5.4 | `clients` |
| `recommendations` | 5.4 | `clients`, `alerts` (optionnel) |

### Nouveaux types d'alertes (Section 12 — Moteur d'alertes)

| Type | Déclencheur |
|---|---|
| `campaign_impact_positive` | Uplift NSS campagne dépasse seuil |
| `campaign_underperformance` | Campagne active > 7j, uplift nul ou négatif, volume > 50 |

### Nouvelles pages Streamlit (Section 9 — Composants existants)

| Page | Description |
|---|---|
| `pages/05_campaigns.py` | Campaign Intelligence — création, suivi, impact |
| `pages/06_recommendations.py` | Recommendation Center — génération, affichage, config |

### Mise à jour de la roadmap (Section 15)

**Wave 5.3** reçoit : livrables Campaign Intelligence (tables + compute + UI + intégration alertes).

**Wave 5.4** reçoit : livrables Recommendation Agent (tables + context builder + agent client + UI + déclenchement auto).

### Mise à jour des packages (Section 16.2)

```
httpx>=0.27     # Déjà présent — utilisé aussi pour les appels API externes
openai>=1.30    # Wave 5.4 — provider OpenAI optionnel
anthropic>=0.25 # Wave 5.4 — provider Anthropic optionnel (si préféré à httpx direct)
```

### Mise à jour du glossaire (Section 19)

| Terme | Définition |
|---|---|
| Campaign Intelligence | Module de suivi d'événements marketing avec mesure d'impact avant/pendant/après sur les métriques RamyPulse |
| Fenêtre d'attribution | Période temporelle définie autour d'une campagne pour mesurer les signaux corrélés |
| Uplift NSS | Différence de NSS entre la phase post-campagne et la phase pré-campagne (baseline) |
| Attribution Score | Score 0–1 de confiance de l'attribution d'un signal à une campagne, basé sur keywords, handle, aspect, fenêtre temporelle |
| Recommendation Agent | Module de génération de recommandations marketing actionnables via appel à un LLM externe |
| Context Builder | Composant assemblant watchlists + alertes + campagnes + RAG en un payload structuré pour l'agent |
| Recommendation Center | Interface utilisateur exposant les recommandations générées avec hooks, scripts, et profils influenceurs |
| Provider | LLM utilisé par le Recommendation Agent — Anthropic, OpenAI, ou Ollama local |

---

*Ce document est un addendum au PRD Technique RamyPulse v2.0.*
*Il doit être lu en conjonction avec le PRD v2.0 — pas en standalone.*
*Version 1.0 — 30 mars 2026*
