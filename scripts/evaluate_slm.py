#!/usr/bin/env python3
"""Confronte des predictions a une reference, porte par porte.

Ce banc n'existait pas : les seuils de `acceptance_gates_v0.4.json` avaient ete
calibres mais jamais appliques, faute d'un modele a mesurer. Il sert aux deux
usages, et c'est deliberé — le professeur passe par le meme banc que l'eleve.
Un professeur qui echoue a une porte ne peut pas produire un jeu d'entrainement
qui la fera passer.

Trois choix de mesure, repris du scorer de campagne pour rester comparables aux
plafonds mesures :

- `macro_f1` pour les champs a valeur unique, moyenne non ponderee sur les
  classes : une classe rare pese autant qu'une classe frequente, ce qui empeche
  un modele qui ne dit jamais `mixte` de bien scorer.
- `micro_f1` pour les champs a valeurs multiples — intents, aspects, alertes,
  entites — comparees comme des ensembles.
- **Une sortie absente ou invalide compte comme fausse**, jamais comme absente.
  C'est la politique inscrite dans le fichier de portes ; l'ignorer laisserait un
  modele ameliorer son score en refusant de repondre.

L'evaluation est aussi conduite **par langue**. L'accord global surestime la
qualite sur l'arabizi : c'est mesure, pas suppose.

Usage :
  python scripts/evaluate_slm.py --reference <ref.jsonl|dir> --predictions <pred.jsonl|dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATES_PATH = ROOT / 'docs/slm_v2/gold_v0.1/baselines/acceptance_gates_v0.4.json'


def charger(chemin: str) -> dict:
    rows: dict[str, dict] = {}
    p = Path(chemin)
    fichiers = sorted(p.glob('*.jsonl')) if p.is_dir() else [p]
    for f in fichiers:
        for ligne in f.read_text(encoding='utf-8').splitlines():
            if ligne.strip():
                r = json.loads(ligne)
                rows[r['record_id']] = r
    return rows


def macro_f1(paires: list[tuple]) -> float:
    """Moyenne non ponderee des F1 par classe.

    Les classes presentes uniquement dans la prediction comptent : sans cela un
    modele pourrait inventer une classe absente de la reference sans penalite.
    """
    classes = {a for a, _ in paires} | {b for _, b in paires}
    scores = []
    for c in classes:
        tp = sum(a == c and b == c for a, b in paires)
        fp = sum(a != c and b == c for a, b in paires)
        fn = sum(a == c and b != c for a, b in paires)
        if tp + fn == 0 and tp + fp == 0:
            continue
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * p * r / (p + r) if p + r else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def micro_f1(paires: list[tuple]) -> float:
    tp = fp = fn = 0
    for a, b in paires:
        sa, sb = set(a), set(b)
        tp += len(sa & sb)
        fn += len(sa - sb)
        fp += len(sb - sa)
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return 2 * p * r / (p + r) if p + r else 1.0


#: Champ -> (extracteur, metrique). Une prediction manquante est remplacee par
#: une valeur sentinelle qui ne peut coincider avec aucune classe reelle.
ABSENT = '__absent__'


def scalaire(chemin: str):
    def lire(row: dict):
        courant = row
        for morceau in chemin.split('.'):
            courant = (courant or {}).get(morceau)
        return ABSENT if courant is None else str(courant)
    return lire


def ensemble_aspects(row: dict) -> set:
    """Compare au niveau `family+sentiment` : l'attribut est un detail que la
    politique d'evaluation exclut explicitement."""
    return {(a.get('family'), a.get('sentiment')) for a in row.get('aspects') or []}


CHAMPS = {
    'is_exploitable.macro_f1': (scalaire('is_exploitable'), macro_f1),
    'business_relevance.macro_f1': (scalaire('business_relevance'), macro_f1),
    'sentiment.macro_f1': (scalaire('sentiment.label'), macro_f1),
    'language.macro_f1': (scalaire('language.dominant'), macro_f1),
    'author_role.macro_f1': (scalaire('author_role'), macro_f1),
    'requires_parent_context.macro_f1': (scalaire('requires_parent_context'), macro_f1),
    'alert_present.macro_f1': (lambda r: str(bool(r.get('alerts'))), macro_f1),
    'intents.micro_f1': (lambda r: set(r.get('intents') or []), micro_f1),
    'aspects_family_sentiment.micro_f1': (ensemble_aspects, micro_f1),
    'entities_type_name.micro_f1': (
        lambda r: {(e.get('type'), (e.get('name') or '').lower())
                   for e in r.get('entities') or []}, micro_f1),
    'alerts_type.micro_f1': (
        lambda r: {a.get('type') for a in r.get('alerts') or []}, micro_f1),
    'alerts_type_severity.micro_f1': (
        lambda r: {(a.get('type'), a.get('severity')) for a in r.get('alerts') or []},
        micro_f1),
}


def evaluer(ref: dict, pred: dict, textes: dict | None = None) -> dict:
    ids = sorted(ref)
    resultats: dict[str, float] = {}

    # Une sortie absente compte comme fausse : c'est la politique du fichier de
    # portes. Sans cela, un modele ameliore son score en refusant de repondre.
    resultats['valid_output_rate'] = sum(i in pred for i in ids) / max(len(ids), 1)

    if textes:
        total = ancrees = 0
        for i in ids:
            r = pred.get(i)
            if not r:
                continue
            texte = textes.get(i, '')
            for bloc in ([r.get('sentiment') or {}] + (r.get('aspects') or [])
                         + (r.get('alerts') or [])):
                for e in bloc.get('evidence') or []:
                    extrait = e.get('text') if isinstance(e, dict) else e
                    if isinstance(extrait, str) and extrait:
                        total += 1
                        ancrees += extrait in texte
        resultats['evidence_grounding_rate'] = ancrees / total if total else 1.0

    for nom, (lire, metrique) in CHAMPS.items():
        vide = set() if metrique is micro_f1 else ABSENT
        paires = [(lire(ref[i]), lire(pred[i]) if i in pred else vide) for i in ids]
        resultats[nom] = metrique(paires)
        if metrique is macro_f1:
            # Une macro-F1 moyenne les classes sans les ponderer : une classe a
            # un seul item y pese autant qu'une classe a cent. Sur `is_exploitable`,
            # 121 accords sur 122 donnaient 0,498 parce que la classe minoritaire
            # comptait un item. Sans ces deux chiffres, l'artefact se lit comme un
            # echec de qualite.
            resultats[nom + ' :accord'] = sum(a == b for a, b in paires) / max(len(paires), 1)
            resultats[nom + ' :support_min'] = min(Counter(a for a, _ in paires).values())
    return resultats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--reference', required=True)
    ap.add_argument('--predictions', required=True)
    ap.add_argument('--texts', action='append', default=None,
                    help='textes source, pour mesurer l ancrage des preuves')
    ap.add_argument('--par-langue', action='store_true',
                    help="evaluer aussi separement par langue dominante de reference")
    args = ap.parse_args()

    gates = json.loads(GATES_PATH.read_text(encoding='utf-8'))
    ref, pred = charger(args.reference), charger(args.predictions)
    communs = set(ref) & set(pred)
    if not ref:
        print('reference vide', file=sys.stderr)
        return 1

    textes = None
    if args.texts:
        textes = {}
        for d in args.texts:
            for rid, r in charger(d).items():
                if 'text' in r:
                    textes[rid] = r['text']

    print(f'reference {len(ref)} · predictions {len(pred)} · communs {len(communs)}\n')
    resultats = evaluer(ref, pred, textes)

    echecs = critiques = 0
    print(f"{'porte':36s} {'mesure':>8s} {'seuil':>7s} {'plafond':>8s}  verdict")
    for nom, porte in gates['gates'].items():
        if nom not in resultats:
            continue
        valeur, seuil = resultats[nom], porte['threshold']
        ok = valeur >= seuil if porte['operator'] == '>=' else valeur > seuil
        plafond = porte.get('ceiling_observed')
        marque = 'OK' if ok else ('ECHEC CRITIQUE' if porte.get('critical') else 'echec')
        if not ok:
            echecs += 1
            critiques += bool(porte.get('critical'))
        # Depasser le plafond mesure n'est pas un exploit mais un signal : la
        # reference elle-meme n'est pas plus coherente que cela.
        note = '  (au-dessus du plafond mesure)' if plafond and valeur > plafond else ''
        accord = resultats.get(nom + ' :accord')
        support = resultats.get(nom + ' :support_min')
        if accord is not None:
            note += f'  accord brut {accord:.1%}'
            if support is not None and support < 5:
                note += f' — classe la plus rare : {support} item(s), macro non interpretable'
        print(f'{nom:36s} {valeur:8.3f} {seuil:7.2f} {str(plafond):>8s}  {marque}{note}')

    non_couvertes = [n for n in gates['gates'] if n not in resultats]
    if non_couvertes:
        print(f'\nportes non couvertes par ce banc : {", ".join(non_couvertes)}')

    if args.par_langue:
        print('\n=== par langue dominante (reference) ===')
        groupes = defaultdict(list)
        for i in ref:
            groupes[(ref[i].get('language') or {}).get('dominant') or 'inconnu'].append(i)
        for langue, ids in sorted(groupes.items(), key=lambda x: -len(x[1])):
            if len(ids) < 20:
                continue
            sous = evaluer({i: ref[i] for i in ids},
                           {i: pred[i] for i in ids if i in pred})
            neutre = sum((pred.get(i, {}).get('sentiment') or {}).get('label') == 'neutre'
                         for i in ids) / len(ids)
            print(f'  {langue:20s} n={len(ids):5d}  sentiment {sous["sentiment.macro_f1"]:.3f}'
                  f'  aspects {sous["aspects_family_sentiment.micro_f1"]:.3f}'
                  f'  taux neutre {neutre:.0%}')

    print(f'\n{echecs} porte(s) en echec, dont {critiques} critique(s)')
    return 1 if critiques else 0


if __name__ == '__main__':
    raise SystemExit(main())
