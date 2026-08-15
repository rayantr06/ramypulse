import json
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

path = 'g:/ramypulse/data/processed/scraped_comments_synth_gemini.jsonl'

if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = [json.loads(l) for l in f if l.strip()]

    print(f"=== 🔍 VÉRIFICATION DU TRAVAIL DE GEMINI ({len(lines)} / 806) ===\n")
    
    # Print the last 4 items
    for i, item in enumerate(lines[-4:], 1):
        print(f"======================================================================")
        print(f"📌 EXEMPLE GEMINI #{len(lines)-4+i} | Marque : {item.get('brand')} | Date : {item.get('timestamp')}")
        print(f"Commentaire Brut : \"{item.get('raw_text')}\"")
        print("----------------------------------------------------------------------")
        print(item.get('synth_output'))
        print("\n")
else:
    print("Fichier non trouvé.")
