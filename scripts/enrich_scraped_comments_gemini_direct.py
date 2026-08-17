import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("Error: GOOGLE_API_KEY / GEMINI_API_KEY not found in .env")
    sys.exit(1)

from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)

INPUT_CSV = Path(__file__).resolve().parent.parent / 'scraping' / 'output' / 'all_comments.csv'
OUTPUT_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'scraped_comments_synth_gemini.jsonl'

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
  "resume": "[Résumé en 1 phrase en français]"
}
<|im_end|>
"""

def main():
    if not INPUT_CSV.exists():
        print(f"Error: Scraped CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} scraped comments from {INPUT_CSV}")

    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    # Check already processed items
    processed_count = 0
    processed_texts = set()
    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        processed_texts.add(data.get('raw_text', ''))
                        processed_count += 1
                    except:
                        pass
        print(f"Resume mode: {processed_count} comments already enriched in output.")

    # Select model
    model_name = "gemini-2.5-flash"
    print(f"Starting direct Gemini API enrichment using model '{model_name}'...")

    success_count = 0
    error_count = 0

    with open(OUTPUT_JSONL, 'a', encoding='utf-8') as out_f:
        for idx, row in df.iterrows():
            text = str(row.get('text', '')).strip()
            brand = row.get('brand', '')
            platform = row.get('platform', '')
            
            if not text or text in processed_texts:
                continue

            print(f"[{idx+1}/{len(df)}] Processing ({brand} / {platform}): \"{text[:40]}...\"", flush=True)

            prompt = f"{SYSTEM_PROMPT}\n\nCommentaire consommateur algérien :\n\"{text}\""
            
            retries = 3
            while retries > 0:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                            top_p=0.95,
                            max_output_tokens=2500
                        )
                    )
                    
                    synth_output = response.text.strip()
                    record = {
                        "raw_text": text,
                        "brand": brand,
                        "platform": platform,
                        "synth_output": synth_output,
                        "timestamp": row.get('date', '')
                    }
                    
                    out_f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    out_f.flush()
                    processed_texts.add(text)
                    success_count += 1
                    break

                except Exception as e:
                    retries -= 1
                    err_msg = str(e)
                    print(f"   ⚠️ Error: {err_msg[:100]}... (Retries left: {retries})")
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        print("   ⏳ Rate limit hit. Pausing 10s...")
                        time.sleep(10)
                    else:
                        time.sleep(2)
            else:
                error_count += 1

            # Pacing pause to avoid hitting free-tier 15 RPM rate limits
            time.sleep(4.5)

    print(f"\n=======================================================")
    print(f"GEMINI DIRECT ENRICHMENT COMPLETE! 🎉")
    print(f"Successfully enriched: {success_count} comments")
    print(f"Errors: {error_count}")
    print(f"Output saved to: {OUTPUT_JSONL}")
    print(f"=======================================================")

if __name__ == "__main__":
    main()
