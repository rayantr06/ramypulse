import json
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

file_path = 'g:/ramypulse/data/processed/openai_synth_training_data.jsonl'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = [json.loads(line) for line in f if line.strip()]

print(f"=== 💎 EXTRACTION DE 10 EXEMPLES QUALITATIFS DU LOT 1 COMPLÉTÉ (TOTAL : {len(lines)} EXEMPLES) ===\n")

# Filter items with reasoning and diverse content
sample_indices = [0, 25, 100, 250, 500, 750, 1000, 1500, 2000, 2500]

for idx_num, i in enumerate(sample_indices, 1):
    if i < len(lines):
        item = lines[i]
        req_body = item.get('response', {}).get('body', {})
        choices = req_body.get('choices', [])
        content = choices[0].get('message', {}).get('content', '') if choices else ''
        
        custom_id = item.get('custom_id', '')
        
        print(f"======================================================================")
        print(f"📌 EXEMPLE #{idx_num} (Custom ID: {custom_id})")
        print(f"======================================================================")
        print(content)
        print("\n")
