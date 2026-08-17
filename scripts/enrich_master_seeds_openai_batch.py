import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables with override=True to ensure fresh key from .env
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    print("Error: OPENAI_API_KEY not found in .env")
    sys.exit(1)

import openai
client = openai.OpenAI(api_key=api_key)

INPUT_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'master_seed_7k.jsonl'
BATCH_REQUESTS_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'openai_batch_requests.jsonl'
OUTPUT_JSONL = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'openai_synth_training_data.jsonl'

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

def prepare_openai_batch_file(offset=0, limit=0, model="gpt-5.4-mini"):
    print(f"Preparing OpenAI Batch JSONL file for model '{model}' (offset={offset}, limit={limit})...")
    seeds = []
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                seeds.append(json.loads(line))

    if offset > 0:
        seeds = seeds[offset:]
    if limit > 0:
        seeds = seeds[:limit]

    print(f"Total seeds in this sub-batch: {len(seeds)}")
    BATCH_REQUESTS_JSONL.parent.mkdir(parents=True, exist_ok=True)

    with open(BATCH_REQUESTS_JSONL, 'w', encoding='utf-8') as out_f:
        for i, item in enumerate(seeds):
            text = item['text']
            custom_id = f"req_{i}_{hash(text) & 0x7fffffff}"
            
            body = {
                "model": model,
                "max_completion_tokens": 2500,
                "messages": [
                    {"role": "user", "content": f"{SYSTEM_PROMPT}\n\nCommentaire :\n\"{text}\""}
                ]
            }

            request_obj = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": body
            }
            out_f.write(json.dumps(request_obj, ensure_ascii=False) + '\n')

    print(f"OpenAI Batch File created successfully: {BATCH_REQUESTS_JSONL}")

def submit_openai_batch_job():
    if not BATCH_REQUESTS_JSONL.exists():
        print("Error: Batch file does not exist. Run with --prepare first.")
        sys.exit(1)

    print(f"1. Uploading batch file '{BATCH_REQUESTS_JSONL.name}' to OpenAI Files API...")
    with open(BATCH_REQUESTS_JSONL, 'rb') as f:
        batch_file = client.files.create(file=f, purpose="batch")
    
    print(f"   -> Uploaded File ID: {batch_file.id}")

    print("2. Submitting Batch Job (50% Cost Discount, 24h completion window)...")
    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    print("\n=======================================================")
    print("OPENAI BATCH JOB SUBMITTED SUCCESSFULLY! 🎉")
    print(f"Batch Job ID: {batch_job.id}")
    print(f"Status: {batch_job.status}")
    print(f"Input File ID: {batch_job.input_file_id}")
    print("=======================================================\n")
    print(f"To check status, run:\npython scripts/enrich_master_seeds_openai_batch.py --status {batch_job.id}")

def check_status(job_id):
    job = client.batches.retrieve(job_id)
    print(f"\n--- OpenAI Batch Job {job.id} ---")
    print(f"Status: {job.status}")
    print(f"Progress: {job.request_counts.completed} / {job.request_counts.total} completed (Failed: {job.request_counts.failed})")
    print(f"Output File ID: {job.output_file_id}")
    print(f"Error File ID: {job.error_file_id}")
    
    if hasattr(job, 'errors') and job.errors:
        print("\n=== BATCH ERRORS ===")
        print(job.errors)

    if job.error_file_id:
        print(f"\nDownloading error file: {job.error_file_id}...")
        content = client.files.content(job.error_file_id)
        err_file_path = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'batch_error_log.jsonl'
        with open(err_file_path, 'wb') as f:
            f.write(content.read())
        print(f"Error log saved to: {err_file_path}")

    if job.status == "completed" and job.output_file_id:
        print(f"\nBatch Completed! Downloading output file: {job.output_file_id}...")
        content = client.files.content(job.output_file_id)
        with open(OUTPUT_JSONL, 'wb') as f:
            f.write(content.read())
        print(f"Output saved to: {OUTPUT_JSONL}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenAI Batch API Pipeline for SYNTH Dataset Generation")
    parser.add_argument("--prepare", action="store_true", help="Prepare batch JSONL file")
    parser.add_argument("--submit", action="store_true", help="Upload batch file and submit job")
    parser.add_argument("--status", type=str, help="Check status of a submitted OpenAI batch job ID")
    parser.add_argument("--offset", type=int, default=0, help="Offset start index for batch")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of items for batch")
    parser.add_argument("--model", type=str, default="gpt-5.4-mini", help="Model to use (e.g., gpt-5.4-mini, gpt-4o-mini)")
    args = parser.parse_args()

    if args.status:
        check_status(args.status)
        return

    if args.prepare:
        prepare_openai_batch_file(offset=args.offset, limit=args.limit, model=args.model)

    if args.submit:
        submit_openai_batch_job()

    if not args.prepare and not args.submit and not args.status:
        prepare_openai_batch_file(offset=args.offset, limit=args.limit, model=args.model)
        submit_openai_batch_job()

if __name__ == "__main__":
    main()
