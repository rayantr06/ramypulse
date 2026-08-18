import json
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

path = r'g:\ramypulse\data\processed\synth_training_data.jsonl'

with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = [json.loads(line) for line in f if line.strip()]

out = []
out.append(f"Total processed samples: {len(lines)}\n")

for i, item in enumerate(lines[:3], 1):
    out.append(f"==================== EXEMPLE #{i} (Source: {item.get('source')}) ====================")
    out.append(item['text'])
    out.append("\n" + "="*70 + "\n")

result_str = "\n".join(out)
with open(r'g:\ramypulse\scripts\samples_output.txt', 'w', encoding='utf-8') as f:
    f.write(result_str)

print("Saved samples_output.txt successfully.")
