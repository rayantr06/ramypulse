#!/usr/bin/env python3
"""Construit l'echantillon d'annotation V0.2 et les lots aveugles.

Principes :
  - `monitoring_target` est assigne par regle depuis le contexte de collecte,
    jamais infere par un annotateur (decision D1).
  - Les 100 commentaires du gold V0.1 sont reintegres pour permettre une
    comparaison avant/apres a texte identique.
  - Les items arabizi viennent du split DEV de Mendeley, jamais de TRAIN,
    afin de ne creer aucune fuite vers l'adaptation linguistique.
  - Les fichiers produits ne contiennent aucune annotation.

Usage : python scripts/build_v02_annotation_sample.py
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / 'data/processed/slm_v2_corpora/v0.1/normalized/ramypulse_business_seed_pool.jsonl'
MENDELEY = ROOT / 'data/processed/slm_v2_corpora/v0.1/normalized/dz_sentiment_mendeley_45k.jsonl'
GOLD_V1 = ROOT / 'data/processed/slm_v2_gold/business_comments_gold_candidate_v0.1.jsonl'
OUT = ROOT / 'data/processed/slm_v2_gold/campaign_v0.2'
SEED = 20260730
BATCH_SIZE = 25

ALERT_CUES = [
    'فاسد', 'خايب', 'مضروب', 'سم', 'مرض', 'تسمم', 'صحة', 'مكانش', 'مكاش', 'نظاف', 'وسخ',
    'حشرة', 'ذبان', 'كذب', 'نصب', 'غش', 'مصداقية', 'قانون', 'عدالة', 'محكمة', 'شكوى',
    'avari', 'périm', 'perim', 'moisi', 'arnaq', 'tromp', 'plainte', 'danger',
]
ARABIZI = re.compile(r'\b(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*[2379])[A-Za-z0-9]{3,}\b')
LATIN = re.compile(r'[A-Za-z]')
ARABIC = re.compile(r'[؀-ۿ]')


def load(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def scope_for(brand: str | None) -> dict:
    """Regle D1 : le scope vient de la configuration de veille, pas du texte.

    Le pool ne contient aucune veille sectorielle reelle. Le scope `secteur`
    reste donc defini dans le schema mais non teste par cette campagne.
    """
    if brand:
        return {'scope': 'organisation', 'entity_name': brand, 'entity_type': 'marque'}
    return {'scope': 'espace_public', 'entity_name': None, 'entity_type': None}


def has_alert_cue(text: str) -> bool:
    low = text.lower()
    return any(cue.lower() in low for cue in ALERT_CUES)


def main() -> int:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'input').mkdir(exist_ok=True)
    (OUT / 'output').mkdir(exist_ok=True)

    gold_v1 = load(GOLD_V1)
    gold_texts = {r['text'] for r in gold_v1}
    pool = [r for r in load(POOL) if r['text'] not in gold_texts]

    items: list[dict] = []
    seen: set[str] = set()

    def add(text: str, brand, topic, source, strate: str, origin: str) -> bool:
        if text in seen or text in gold_texts and origin != 'gold_v0.1':
            return False
        seen.add(text)
        items.append({
            'record_id': f'v02_{len(items) + 1:04d}',
            'text': text,
            'monitoring_target': scope_for(brand),
            'context': {'source': source, 'topic': topic, 'brand': brand},
            '_strate': strate,
            '_origine': origin,
        })
        return True

    # 1. Controle avant/apres : les 100 du gold V0.1, textes identiques.
    for r in gold_v1:
        c = r['context']
        seen.add(r['text'])
        items.append({
            'record_id': f'v02_{len(items) + 1:04d}',
            'text': r['text'],
            'monitoring_target': scope_for(c.get('brand')),
            'context': {'source': c.get('source'), 'topic': c.get('topic'), 'brand': c.get('brand')},
            '_strate': 'controle_avant_apres',
            '_origine': 'gold_v0.1',
        })

    org = [r for r in pool if r['metadata']['context'].get('brand')]
    pub = [r for r in pool if not r['metadata']['context'].get('brand')]

    # 2. Tous les candidats-alerte disponibles : ressource la plus rare du pool.
    cues = [r for r in org if has_alert_cue(r['text'])]
    rng.shuffle(cues)
    for r in cues:
        c = r['metadata']['context']
        add(r['text'], c['brand'], c['topic'], c['source'], 'organisation_alerte_probable', 'pool')

    # 3. Tout l'arabizi disponible cote organisation.
    for r in org:
        if ARABIZI.search(r['text']):
            c = r['metadata']['context']
            add(r['text'], c['brand'], c['topic'], c['source'], 'organisation_arabizi', 'pool')

    # 4. Complement organisation, equilibre par marque.
    by_brand: dict[str, list] = defaultdict(list)
    for r in org:
        if r['text'] not in seen:
            by_brand[r['metadata']['context']['brand']].append(r)
    for v in by_brand.values():
        rng.shuffle(v)
    target_org = 140
    idx = 0
    while sum(1 for i in items if i['_strate'].startswith('organisation')) < target_org:
        brands = [b for b in by_brand if idx < len(by_brand[b])]
        if not brands:
            break
        for b in brands:
            if sum(1 for i in items if i['_strate'].startswith('organisation')) >= target_org:
                break
            r = by_brand[b][idx]
            c = r['metadata']['context']
            add(r['text'], c['brand'], c['topic'], c['source'], 'organisation_general', 'pool')
        idx += 1

    # 5. Espace public depuis le pool, stratifie par thematique.
    by_topic: dict[str, list] = defaultdict(list)
    for r in pub:
        by_topic[r['metadata']['context']['topic']].append(r)
    for v in by_topic.values():
        rng.shuffle(v)
    topics = ['social', 'economy', 'health', 'education', 'sport', 'religious', 'media']
    per = 30 // len(topics) + 1
    for t in topics:
        for r in by_topic.get(t, [])[:per]:
            c = r['metadata']['context']
            add(r['text'], None, c['topic'], c['source'], 'espace_public_pool', 'pool')

    # 6. Arabizi : le pool n'en a pas. Uniquement le split DEV de Mendeley,
    #    jamais TRAIN, pour ne pas polluer l'adaptation linguistique.
    men_dev = [r for r in load(MENDELEY)
               if r.get('split') == 'dev' and ARABIZI.search(r['text'])
               and 20 <= len(r['text']) <= 300]
    rng.shuffle(men_dev)
    promoted = []
    for r in men_dev[:30]:
        if add(r['text'], None, 'general', 'dz_sentiment_mendeley_45k',
               'espace_public_arabizi', 'mendeley_dev'):
            promoted.append(r['record_id'])

    rng.shuffle(items)
    for n, it in enumerate(items, 1):
        it['record_id'] = f'v02_{n:04d}'

    # Aucune annotation ne doit fuiter dans les lots.
    banned = ['"annotation"', 'is_exploitable', 'business_relevance', '"aspects"',
              '"alerts"', '"intents"', 'legacy_weak', 'sentiment_label', 'gold_dev', 'gold_test']
    public = [{k: v for k, v in it.items() if not k.startswith('_')} for it in items]
    blob = json.dumps(public, ensure_ascii=False)
    leaks = [b for b in banned if b in blob]
    if leaks:
        print(f'FUITE DETECTEE : {leaks}', file=sys.stderr)
        return 1

    for i in range(0, len(public), BATCH_SIZE):
        p = OUT / 'input' / f'batch_{i // BATCH_SIZE + 1:02d}.jsonl'
        p.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n'
                             for x in public[i:i + BATCH_SIZE]), encoding='utf-8')

    (OUT / 'sample_manifest.json').write_text(json.dumps({
        'version': '0.2', 'seed': SEED, 'total': len(items),
        'batches': (len(public) + BATCH_SIZE - 1) // BATCH_SIZE, 'batch_size': BATCH_SIZE,
        'strates': dict(Counter(i['_strate'] for i in items)),
        'origines': dict(Counter(i['_origine'] for i in items)),
        'scopes': dict(Counter(i['monitoring_target']['scope'] for i in items)),
        'marques': dict(Counter(i['context']['brand'] for i in items if i['context']['brand'])),
        'mendeley_dev_promus_en_gold': promoted,
        'note_fuite': ("Les record_id Mendeley ci-dessus proviennent du split DEV et doivent etre "
                       "retires de la vue DEV lors du prochain passage de prepare_slm_v2_corpora.py."),
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    (OUT / 'sample_full.jsonl').write_text(
        ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in items), encoding='utf-8')

    print(f'total          : {len(items)}')
    print(f'lots           : {(len(public) + BATCH_SIZE - 1) // BATCH_SIZE} x {BATCH_SIZE}')
    for k, v in sorted(Counter(i['_strate'] for i in items).items()):
        print(f'  {k:34s} {v}')
    print('scopes         :', dict(Counter(i['monitoring_target']['scope'] for i in items)))
    print('arabizi total  :', sum(bool(ARABIZI.search(i['text'])) for i in items))
    print('latin ou mixte :', sum(bool(LATIN.search(i['text'])) for i in items))
    print('mendeley DEV promus (a exclure du DEV) :', len(promoted))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
