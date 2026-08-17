import json
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

path = 'g:/ramypulse/data/processed/scraped_comments_synth_gemini.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    lines = [json.loads(line) for line in f if line.strip()]

print(f"=== 🔍 INSPECTION DES RÉSULTATS GÉNÉRÉS GEMINI ({len(lines)} / 806) ===\n")

for i, item in enumerate(lines[:3], 1):
    print(f"--- 📌 Exemple #{i} ({item.get('brand')} / {item.get('platform')}) ---")
    print(f"Commentaire Brut : \"{item.get('raw_text')}\"")
    print("\n--- Sortie SYNTH Générée (`<think>` + JSON) ---")
    print(item.get('synth_output'))
    print("\n" + "="*70 + "\n")
