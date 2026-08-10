#!/usr/bin/env python3
"""Annotation d'un lot par Gemini via Vertex AI Express.

Pourquoi ce script existe. Les passes precedentes ont ete faites par des agents
d'IDE, un lot a la fois, a la main. Cela ne monte pas a l'echelle des 94 000
textes disponibles. Ce client fait la meme chose par API, avec trois garanties
que la conduite manuelle n'offrait pas.

1. **Les vocabulaires sont lus dans le schema**, jamais recopies. Une fiche
   d'aide recopiee a la main avait deja ete livree avec des enums vides parce
   que les `$ref` n'avaient pas ete resolus. Ici la derive est impossible.
2. **`lecture_fr` est obligatoire.** C'est la seule intervention qui ait
   corrige le repli sur `neutre` en arabizi : 56 % -> 12 %. Une reponse sans ce
   champ est rejetee et redemandee.
3. **Un item, une requete.** Le modele lit et juge chaque commentaire seul.
   Un remplissage par gabarit a deja ete rejete sur ce projet ; envoyer vingt
   textes dans un meme appel invite exactement ce comportement.

L'API AI Studio (`generativelanguage.googleapis.com`) est bloquee sur le projet
porteur de la cle. On passe donc par `aiplatform.googleapis.com`, qui accepte la
meme cle en mode Express.

Usage :
  python scripts/annotate_vertex.py --input <dir_input> --output <dir_output> \
                                    --annotator G1 [--model gemini-3-flash-preview]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'docs/slm_v2/business_comment_annotation_v0.3.schema.json'
ENDPOINT = ('https://aiplatform.googleapis.com/v1/publishers/google/models/'
            '{model}:generateContent?key={key}')
#: Champs produits par le pipeline, jamais par l'annotateur (regle D2/D3).
INTERDITS = ('actionability', 'schema_version')


class Compteur:
    """Cumule les jetons consommes, appels rates compris.

    Sans ce relevé, impossible de projeter le cout d'une passe sur 14 697 avis
    autrement qu'en le devinant. Les jetons de reflexion sont comptes a part :
    ils sont factures comme de la sortie et representent l'essentiel du volume
    sur un modele a raisonnement.
    """

    def __init__(self) -> None:
        self.entree = self.sortie = self.reflexion = self.appels = 0
        self.interdits: Counter[str] = Counter()
        self._verrou = __import__('threading').Lock()

    def ajouter(self, entree: int, sortie: int, reflexion: int) -> None:
        with self._verrou:
            self.entree += entree
            self.sortie += sortie
            self.reflexion += reflexion
            self.appels += 1

    def champ_interdit(self, champ: str) -> None:
        with self._verrou:
            self.interdits[champ] += 1

    def resume(self, items: int) -> str:
        if not self.appels:
            return 'aucun appel comptabilise'
        total_sortie = self.sortie + self.reflexion
        texte = (f'appels {self.appels} · entree {self.entree:,} jetons · '
                 f'sortie {total_sortie:,} (dont reflexion {self.reflexion:,})\n'
                 f'  par item : {self.entree / max(items, 1):.0f} entree, '
                 f'{total_sortie / max(items, 1):.0f} sortie')
        if self.interdits:
            texte += f'\n  champs derives retires : {dict(self.interdits)}'
        return texte


COMPTEUR = Compteur()


def charger_cle() -> str:
    """Lit la cle dans l'environnement, sinon dans `.env` (non suivi par git)."""
    for var in ('VERTEX_EXPRESS_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_API_KEY'):
        if os.environ.get(var):
            return os.environ[var]
    env = ROOT / '.env'
    if env.exists():
        for ligne in env.read_text(encoding='utf-8').splitlines():
            if ligne.startswith('VERTEX_EXPRESS_API_KEY='):
                return ligne.split('=', 1)[1].strip()
    raise SystemExit('cle absente : definir VERTEX_EXPRESS_API_KEY')


def vocabulaires(schema: dict) -> str:
    """Extrait les enums du schema. Recopier ces listes a la main est la source
    d'erreur qui a deja livre une fiche d'aide avec des vocabulaires vides."""
    trouve: dict[str, list] = {}

    def marche(noeud, chemin=''):
        if not isinstance(noeud, dict):
            return
        if 'enum' in noeud and chemin:
            trouve[chemin] = noeud['enum']
        for cle, val in noeud.items():
            if cle in ('properties', '$defs'):
                for k, v in val.items():
                    marche(v, f'{chemin}.{k}' if chemin else k)
            elif cle == 'items':
                marche(val, chemin + '[]')

    marche(schema)
    lignes = []
    for chemin, valeurs in sorted(trouve.items()):
        propres = [v for v in valeurs if v is not None]
        nul = ' (ou null)' if None in valeurs else ''
        lignes.append(f'- `{chemin}` : {", ".join(propres)}{nul}')
    return '\n'.join(lignes)


REGLES_ARABIZI = """
### Dechiffrage de l'arabizi

L'arabizi transcrit l'arabe en caracteres latins avec des chiffres.

| Chiffre | Lettre | Exemples |
|---|---|---|
| `3` | ع | `3lik`, `3andi`, `ya3tik` |
| `7` | ح | `7abibi`, `mli7`, `7aja` |
| `9` | ق | `9alb`, `9olek`, `wa9t` |
| `2` | ء | `mo2amara` |
| `5` ou `kh` | خ | `5oya`, `khouya` |
| `8` ou `gh` | غ | `8ali`, `ghali` |

Reperes : `bzf` beaucoup · `nhabkoum` je vous aime · `mli7` bien · `khayb` mauvais ·
`walou` rien · `makach` il n'y a pas · `rouh` va-t'en · `ch7al` combien · `wach` quoi ·
`rabi` Dieu · `nchallah` si Dieu veut · `saha` merci · `zmar` ane, insulte ·
`9ahwa` cafe · `khdma` travail · `hgar` opprimer · `nedam` regime, systeme.
"""

REGLE_NEUTRE = """
### Regle sur `neutre`

`neutre` reste legitime : beaucoup de commentaires le sont vraiment. Mais des que tu
le choisis, ecris dans `notes` pourquoi, en t'appuyant sur ta traduction.

Sont neutres : une question factuelle, une mention simple, une information sans opinion.

Ne sont PAS neutres : affection, remerciement chaleureux, insulte, moquerie, colere,
deception, enthousiasme — meme brefs, meme en argot, meme avec des emojis pour seul indice.

Ne surcorrige pas. N'invente pas un sentiment pour eviter `neutre` : cela creerait le
defaut inverse, et il sera detecte.
"""


def construire_prompt(schema: dict) -> str:
    return f"""Tu es annotateur sur le corpus RamyPulse — veille marketing algerienne.
Tu recois UN commentaire et tu produis UNE annotation JSON.

## Methode imposee — l'etape de lecture

1. Ecris d'abord la traduction francaise dans `lecture_fr`, AVANT toute etiquette.
2. Annote ensuite a partir de ta traduction, pas du texte brut.

Ce champ est obligatoire et verifie. Les passes precedentes qui l'omettaient se
repliaient sur `neutre` dans plus de la moitie des cas en arabizi. Si un passage
reste indechiffrable, ecris-le entre crochets : `[indechiffrable : xyz]`. Ne devine pas.
{REGLES_ARABIZI}{REGLE_NEUTRE}
## Portee de surveillance

Le champ `monitoring_target` t'est donne. Il conditionne deux choses :

- `scope = espace_public` : `alerts` reste TOUJOURS vide, meme pour un contenu grave,
  et `business_relevance` ne peut pas etre `directe`. Les aspects restent possibles :
  c'est ainsi qu'on capture le signal. Une insulte reste exploitable et son sentiment
  doit refleter l'agressivite — non exploitable ne veut pas dire desagreable.
- `scope = organisation` : une alerte n'est justifiee que si elle vise l'entite surveillee.

## Vocabulaires fermes — aucune autre valeur n'est acceptee

{vocabulaires(schema)}

## Contraintes

- Un aspect n'est jamais `neutre` : s'il n'y a pas de polarite, il n'y a pas d'aspect.
- `alert.type = reputation_virale` exige un signe de PROPAGATION : appel au boycott,
  menace de rendre public, mention de partages, de presse ou de reseaux sociaux. Un
  avis simplement tres negatif n'est pas viral — sa severite se dit dans `severity`,
  pas en changeant le type d'alerte.

### Les preuves

- `evidence` est TOUJOURS un tableau, meme pour un seul extrait.
- Chaque extrait est une portion EXACTE et CONTINUE du texte original, jamais de ta
  traduction. Ne recolle pas deux morceaux avec des points de suspension : prends
  deux extraits separes, ou le passage entier qui les relie.
- Un extrait localise le passage qui justifie l'etiquette. Recopier tout le
  commentaire ne prouve rien : cite la portion decisive.
- Ne calcule aucun offset : le pipeline s'en charge.

## Champs a ne PAS produire

`actionability` et `schema_version` sont derives en aval. Ne les ecris pas, meme
partiellement : la file d'affectation et la priorite se calculent depuis les champs
que tu annotes, et une valeur ecrite ici serait ecrasee.

`entities` ne contient que des entites reellement nommees ou clairement designees.

## Sortie

Un unique objet JSON, sans texte autour, sans bloc de code :

{{"record_id":"...","lecture_fr":"...","monitoring_target":{{...}},"author_role":"consommateur",
"requires_parent_context":false,"is_exploitable":true,"non_exploitable_reason":null,
"business_relevance":"aucune","language":{{"dominant":"darija_arabizi","detected":["darija"],
"code_switching":false,"scripts":["latin","chiffres"]}},"entities":[],
"sentiment":{{"label":"positif","intensity":"forte","emotion":"joie","sarcasm":false,
"target_entity_ids":[],"evidence":["nhabkoum bzf"]}},"intents":["avis"],"aspects":[],
"alerts":[],"notes":""}}"""


def appeler(prompt: str, item: dict, modele: str, cle: str, temperature: float = 0.0,
            reflexion: str = 'low') -> dict:
    """Un appel, un item. Reessaie sur 429 et 5xx avec attente croissante.

    `maxOutputTokens` est large parce que les modeles a raisonnement imputent
    leurs jetons de reflexion sur ce budget : a 4096 la reponse JSON se trouvait
    tronquee en plein milieu, et un item a consomme 15 725 jetons de reflexion
    sur un emballement occasionnel.

    `reflexion='low'` est le defaut, et c'est une mesure, pas une economie de
    principe : sur les trois items dont on a la verite terrain humaine — ceux ou
    les deux annotateurs precedents avaient echoue — les deux reglages font 3/3.
    L'etape `lecture_fr` tient lieu de deliberation, avec l'avantage d'etre
    visible et verifiable. La reflexion interne pesait 93 % des jetons de sortie.
    """
    config = {'temperature': temperature, 'responseMimeType': 'application/json',
              'maxOutputTokens': 16384}
    if reflexion != 'defaut':
        config['thinkingConfig'] = {'thinkingLevel': reflexion}
    corps = json.dumps({
        'systemInstruction': {'parts': [{'text': prompt}]},
        'contents': [{'role': 'user', 'parts': [{'text': json.dumps(item, ensure_ascii=False)}]}],
        'generationConfig': config,
    }).encode('utf-8')
    url = ENDPOINT.format(model=modele, key=cle)
    derniere = ''
    for essai in range(5):
        try:
            requete = urllib.request.Request(
                url, data=corps, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(requete, timeout=180) as reponse:
                donnees = json.loads(reponse.read().decode('utf-8'))
            parts = donnees['candidates'][0]['content'].get('parts') or []
            texte = ''.join(p.get('text', '') for p in parts).strip()
            # Le modele encadre parfois sa reponse d'un bloc de code malgre la consigne.
            texte = re.sub(r'^```(?:json)?|```$', '', texte, flags=re.M).strip()
            resultat = json.loads(texte)
            # Comptabilite des jetons : c'est elle qui permet de projeter le cout
            # d'une passe a l'echelle avant de l'engager.
            usage = donnees.get('usageMetadata') or {}
            COMPTEUR.ajouter(usage.get('promptTokenCount', 0),
                             usage.get('candidatesTokenCount', 0),
                             usage.get('thoughtsTokenCount', 0))
            return resultat
        except urllib.error.HTTPError as err:
            derniere = f'HTTP {err.code}'
            if err.code not in (429, 500, 503, 504):
                derniere = f'HTTP {err.code} {err.read()[:200].decode("utf-8", "replace")}'
                break
        except Exception as err:                        # reseau, JSON tronque
            derniere = f'{type(err).__name__}: {err}'
        time.sleep(min(2 ** essai + random.random(), 30))
    raise RuntimeError(derniere)


def normaliser_preuves(bloc: dict) -> list[str]:
    """Ramene `evidence` a une liste de chaines.

    Le modele produit tantot une chaine nue, tantot une liste : 617 contre 680
    sur le pilote Maps. Une chaine nue traversait le controle sans etre vue,
    parce que `liste += "abc"` ajoute des caracteres isoles, tous presents dans
    le texte. Le defaut se corrige ici, une seule fois, pour tous les blocs.
    """
    evidence = bloc.get('evidence')
    if isinstance(evidence, str):
        evidence = [evidence] if evidence.strip() else []
        bloc['evidence'] = evidence
    return [e for e in (evidence or []) if isinstance(e, str) and e.strip()]


def verifier(sortie: dict, item: dict) -> str | None:
    """Controles bon marche appliques avant d'ecrire. Ce qui echoue est redemande."""
    if sortie.get('record_id') != item['record_id']:
        return 'record_id different'
    if not str(sortie.get('lecture_fr') or '').strip():
        return 'lecture_fr vide'
    # Ces champs sont derives en aval, qui les ecrase de toute facon. Jeter une
    # annotation par ailleurs correcte parce qu'elle en porte un serait
    # disproportionne : on les retire, en comptant combien de fois cela arrive.
    for champ in INTERDITS:
        if sortie.pop(champ, None) is not None:
            COMPTEUR.champ_interdit(champ)
    if any(a.get('sentiment') == 'neutre' for a in sortie.get('aspects') or []):
        return 'aspect neutre interdit'

    texte = item['text']
    blocs = ([sortie.get('sentiment') or {}] + (sortie.get('aspects') or [])
             + (sortie.get('alerts') or []))
    for bloc in blocs:
        for preuve in normaliser_preuves(bloc):
            if preuve not in texte:
                # Le modele recolle parfois deux fragments avec des points de
                # suspension. Ce n'est pas un extrait : le pipeline ne pourra
                # pas en resoudre les offsets.
                if '...' in preuve or '…' in preuve:
                    return f'preuve recollee avec des points de suspension : {preuve[:60]!r}'
                return f'preuve absente du texte : {preuve[:60]!r}'
            # Une preuve qui recouvre tout un long commentaire ne localise rien.
            # En dessous de ce seuil l'avis tient en une pensee : le texte entier
            # est alors legitimement le passage decisif.
            if len(texte) > 200 and len(preuve) >= 0.9 * len(texte):
                return f'preuve couvrant tout le texte : {preuve[:60]!r}'
    if (item.get('monitoring_target') or {}).get('scope') == 'espace_public':
        if sortie.get('alerts'):
            return 'alerte interdite en espace_public'
        if sortie.get('business_relevance') == 'directe':
            return 'business_relevance directe interdite en espace_public'
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='dossier des batch_XX.jsonl')
    ap.add_argument('--output', required=True, help='dossier des batch_XX.out.jsonl')
    ap.add_argument('--annotator', required=True, help='identifiant, ex. G1')
    ap.add_argument('--model', default=os.environ.get('VERTEX_ANNOTATION_MODEL',
                                                      'gemini-3-flash-preview'))
    ap.add_argument('--thinking', default='low', choices=('low', 'high', 'defaut'),
                    help='niveau de reflexion interne ; low par defaut, voir appeler()')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=None, help='n premiers items (essai)')
    args = ap.parse_args()

    cle = charger_cle()
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    prompt = construire_prompt(schema)
    entree, sortie_dir = Path(args.input), Path(args.output)
    sortie_dir.mkdir(parents=True, exist_ok=True)

    lots = sorted(entree.glob('batch_*.jsonl'))
    if not lots:
        print(f'aucun lot dans {entree}', file=sys.stderr)
        return 1

    total_ecrits = total_echecs = 0
    for lot in lots:
        cible = sortie_dir / f'{lot.stem}.out.jsonl'
        items = [json.loads(l) for l in lot.read_text(encoding='utf-8').splitlines() if l.strip()]
        if args.limit:
            items = items[:args.limit]
        # Reprise : un lot deja complet n'est pas repaye.
        if cible.exists():
            faits = {json.loads(l)['record_id']
                     for l in cible.read_text(encoding='utf-8').splitlines() if l.strip()}
            if faits >= {i['record_id'] for i in items}:
                print(f'{lot.name:18s} deja complet, ignore')
                continue

        def traiter(item: dict) -> tuple[dict | None, str | None]:
            for essai in range(3):
                # A temperature 0 un reessai reproduit la meme reponse, donc le
                # meme defaut. On desserre juste assez pour changer de trajectoire.
                try:
                    res = appeler(prompt, item, args.model, cle,
                                  temperature=0.0 + 0.2 * essai, reflexion=args.thinking)
                except RuntimeError as err:
                    return None, str(err)
                probleme = verifier(res, item)
                if probleme is None:
                    res['annotator'] = args.annotator
                    return res, None
                if essai == 2:
                    return None, probleme
            return None, 'inatteignable'

        debut = time.time()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            resultats = list(pool.map(traiter, items))

        bons = [r for r, _ in resultats if r]
        echecs = [(i['record_id'], e) for i, (r, e) in zip(items, resultats) if e]
        cible.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in bons),
                         encoding='utf-8')
        total_ecrits += len(bons)
        total_echecs += len(echecs)
        print(f'{lot.name:18s} {len(bons):3d}/{len(items):3d} en {time.time() - debut:5.0f}s'
              + (f'  echecs: {echecs[:2]}' if echecs else ''))

    print(f'\ntotal : {total_ecrits} annotes, {total_echecs} echecs')
    print(f'modele : {args.model}   annotateur : {args.annotator}')
    print(f'jetons : {COMPTEUR.resume(total_ecrits)}')
    return 1 if total_echecs else 0


if __name__ == '__main__':
    raise SystemExit(main())
