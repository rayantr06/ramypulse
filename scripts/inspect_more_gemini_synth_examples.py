import json
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

path = 'g:/ramypulse/data/processed/scraped_comments_synth_gemini.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    lines = [json.loads(line) for line in f if line.strip()]

print(f"=== 🔍 PROGRESSION & INSPECTION DE PLUSIEURS EXEMPLES GÉNÉRÉS ({len(lines)} / 806) ===\n")

# Select interesting examples with length > 20 characters
rich_items = [item for item in lines if len(item.get('raw_text', '')) > 25]

print(f"Trouvé {len(rich_items)} exemples riches parmi les {len(lines)} générés.\n")

for i, item in enumerate(rich_items[:6], 1):
    print(f"----------------------------------------------------------------------")
    print(f"📌 EXEMPLE DE TEST #{i} | Marque : {item.get('brand')} | Plateforme : {item.get('platform')}")
    print(f"Commentaire Brut : \"{item.get('raw_text')}\"")
    print("----------------------------------------------------------------------")
    print(item.get('synth_output'))
    print("\n")
