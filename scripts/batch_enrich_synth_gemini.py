import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
model_name = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')

if not api_key:
    print("Error: Neither GEMINI_API_KEY nor GOOGLE_API_KEY found in .env")
    sys.exit(1)

from google import genai

INPUT_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'master_seed_7k.jsonl'
BATCH_REQUESTS_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'batch_requests.jsonl'
OUTPUT_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'batch_synth_training_data.jsonl'

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

def prepare_batch_file(limit=0):
    print(f"Preparing batch request file for Gemini Batch API ({model_name})...")
    seeds = []
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                seeds.append(json.loads(line))

    if limit > 0:
        seeds = seeds[:limit]

    print(f"Total seeds to prepare for batch: {len(seeds)}")
    BATCH_REQUESTS_JSONL.parent.mkdir(parents=True, exist_ok=True)

    with open(BATCH_REQUESTS_JSONL, 'w', encoding='utf-8') as out_f:
        for i, item in enumerate(seeds):
            text = item['text']
            custom_id = f"seed_{i}_{hash(text) & 0x7fffffff}"
            request_obj = {
                "custom_id": custom_id,
                "request": {
                    "contents": [
                        {"parts": [{"text": f"{SYSTEM_PROMPT}\n\nCommentaire :\n\"{text}\""}]}
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "topP": 0.95,
                        "maxOutputTokens": 2500
                    }
                }
            }
            out_f.write(json.dumps(request_obj, ensure_ascii=False) + '\n')

    print(f"Batch request JSONL created successfully: {BATCH_REQUESTS_JSONL}")

def submit_batch_job():
    if not BATCH_REQUESTS_JSONL.exists():
        print("Error: Batch request file does not exist. Run with --prepare first.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    print(f"Uploading batch file {BATCH_REQUESTS_JSONL.name} to Gemini Files API...")
    uploaded_file = client.files.upload(
        file=str(BATCH_REQUESTS_JSONL),
        config={'mime_type': 'text/plain'}
    )
    print(f"Uploaded file URI: {uploaded_file.name}")

    print(f"Submitting Batch Job for model {model_name} (50% discount mode)...")
    batch_job = client.batches.create(
        model=model_name,
        src=uploaded_file.name
    )

    print("\n=======================================================")
    print(f"BATCH JOB CREATED SUCCESSFULLY!")
    print(f"Job Name / ID: {batch_job.name}")
    print(f"State: {batch_job.state}")
    print("=======================================================\n")
    print(f"To check job status later, run:\npython scripts/batch_enrich_synth_gemini.py --status {batch_job.name}")

def check_status(job_name):
    client = genai.Client(api_key=api_key)
    print(f"Checking status for batch job: {job_name}")
    job = client.batches.get(name=job_name)
    print(f"Job State: {job.state}")
    if hasattr(job, 'error') and job.error:
        print(f"Error details: {job.error}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gemini Batch API Pipeline (50% Cost Discount)")
    parser.add_argument("--prepare", action="store_true", help="Prepare batch JSONL file")
    parser.add_argument("--submit", action="store_true", help="Upload batch file and submit job")
    parser.add_argument("--status", type=str, help="Check status of a submitted batch job ID")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of items for batch")
    args = parser.parse_args()

    if args.status:
        check_status(args.status)
        return

    if args.prepare:
        prepare_batch_file(args.limit)

    if args.submit:
        submit_batch_job()

    if not args.prepare and not args.submit and not args.status:
        parser.print_help()

if __name__ == "__main__":
    main()
