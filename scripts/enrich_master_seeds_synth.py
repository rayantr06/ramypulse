import os
import sys
import json
import time
import re
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

if not api_key:
    print("Error: Neither GEMINI_API_KEY nor GOOGLE_API_KEY found in .env")
    sys.exit(1)

import google.generativeai as genai
genai.configure(api_key=api_key)

INPUT_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'master_seed_7k.jsonl'
OUTPUT_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'synth_training_data.jsonl'

SYSTEM_PROMPT = """Tu es un annotateur expert en linguistique et analyse du sentiment consommateur algérien (Darija, Arabizi, Français, Arabe).
Ton rôle est de générer un exemple d'entraînement au format ChatML enrichi d'une TRACE DE RAISONNEMENT EN 5 ÉTAPES (`<think>`) selon la méthodologie SYNTH (Pleïas).

Pour le commentaire consommateur donné, tu dois produire EXACTEMENT ce format :

<|im_start|>user
Analyse ce commentaire consommateur algérien et extrais les informations structurées :

"[TEXTE_BRUT]"
<|im_end|>
<|im_start|>assistant
<think>
### 1. Décomposition Linguistique
- Langue dominante : [Darija / Arabizi / Français / Arabe / Mixte]
- Mots-clés & Expressions : [Lister les expressions clés et leurs sens]
- Code-switching / Emprunts : [Mots français ou arabes empruntés]

### 2. Analyse Sentimentale & Intensité
- Signal : [● POSITIF / ● NÉGATIF / ○ NEUTRE / ◐ MIXTE]
- Tonalité : [Ironie, Sarcasme, Éloge, Déception, Colère, etc.]

### 3. Extraction d'Entités (Marque & Produit)
- Marque : [Nom de la marque ou "Non mentionnée"]
- Produit : [Catégorie de produit ou "Non mentionné"]

### 4. Extraction d'Aspects (Qualité, Prix, SAV, Goût, Emballage, etc.)
- [Aspect 1] : [Extrait] -> [POSITIF / NÉGATIF / NEUTRE]

### 5. Évaluation de Criticité
- Alerte Qualité / Sanitaire : [OUI / NON]
- Niveau de sévérité : [Faible / Moyen / Élevé / Critique]
</think>

{
  "sentiment": "[positif | negatif | neutre | mixte]",
  "confiance_sentiment": [0.0 à 1.0],
  "est_sarcastique": [true | false],
  "marque": [string ou null],
  "produit": [string ou null],
  "aspects": [
    {"aspect": "[nom_aspect]", "sentiment": "[positif|negatif|neutre]", "extrait": "[extrait]"}
  ],
  "alerte_qualite": [true | false],
  "langue_dominante": "[darija_arabizi | darija_arabe | francais | arabe_msa | mixte]",
  "resume": "[Résumé en 1 sentence en français]"
}
<|im_end|>
"""

def process_single_seed_with_retry(model, item, max_retries=3):
    text = item['text']
    for attempt in range(1, max_retries + 1):
        try:
            response = model.generate_content(
                f"{SYSTEM_PROMPT}\n\nCommentaire :\n\"{text}\"",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    top_p=0.95,
                    max_output_tokens=2500
                )
            )
            generated_text = response.text.strip()
            return {
                "query_id": hash(text) & 0x7fffffff,
                "source": item.get('source', 'unknown'),
                "raw_text": text,
                "text": generated_text
            }
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Quota" in err_str or "ResourceExhausted" in err_str:
                wait_time = 15 * attempt
                print(f"Rate limited (429). Retrying in {wait_time}s... (Attempt {attempt}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Error processing item '{text[:30]}...': {e}")
                return None
    return None

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Enrich Master Seed Corpus with Pleias SYNTH traces")
    parser.add_argument("--limit", type=int, default=50, help="Number of seeds to process (default 50)")
    args = parser.parse_args()

    if not INPUT_JSONL.exists():
        print(f"Input file not found: {INPUT_JSONL}")
        sys.exit(1)

    processed_texts = set()
    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        processed_texts.add(data.get('raw_text'))
                    except Exception:
                        pass
        print(f"Resuming pipeline... Already processed: {len(processed_texts)} items")

    seeds = []
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                seeds.append(json.loads(line))

    remaining_seeds = [s for s in seeds if s['text'] not in processed_texts]
    if args.limit > 0:
        remaining_seeds = remaining_seeds[:args.limit]

    print(f"Total Master Seeds: {len(seeds)} | Processing batch of: {len(remaining_seeds)}")

    if not remaining_seeds:
        print("All target seeds already processed!")
        return

    model_name = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')
    print(f"Initializing Gemini Model: {model_name}...")
    model = genai.GenerativeModel(model_name)

    batch_count = 0
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSONL, 'a', encoding='utf-8') as out_f:
        for i, item in enumerate(remaining_seeds, 1):
            res = process_single_seed_with_retry(model, item)
            if res:
                out_f.write(json.dumps(res, ensure_ascii=False) + '\n')
                out_f.flush()
                batch_count += 1
                print(f"[{i}/{len(remaining_seeds)}] Enriched item #{i}")
            
            # Pacing pause to avoid 429 quota burst limits
            time.sleep(2.0)

    print(f"\nPipeline finished! Total enriched training items saved to: {OUTPUT_JSONL}")

if __name__ == "__main__":
    main()
