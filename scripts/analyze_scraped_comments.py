import pandas as pd
import re
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv('g:/ramypulse/scraping/output/all_comments.csv')

print(f"=== 📊 ANALYSE DU DATASET SCRAPÉ ({len(df)} COMMENTAIRES) ===\n")

print("--- 1. DISTRIBUTION PAR MARQUE ---")
print(df['brand'].value_counts())
print("\n" + "="*50 + "\n")

df['len'] = df['text'].astype(str).str.len()
df['words'] = df['text'].astype(str).str.split().str.len()

print("--- 2. QUALITÉ & LONGEUR DES TEXTES ---")
print(f"Nombre total de commentaires : {len(df)}")
print(f"Longueur moyenne (caractères) : {df['len'].mean():.1f}")
print(f"Longueur moyenne (mots)       : {df['words'].mean():.1f}")
short_cnt = len(df[df['words'] <= 2])
rich_cnt = len(df[df['words'] > 5])
print(f"Commentaires ultra-courts (1-2 mots, ex: 'روعة', 'top') : {short_cnt} ({short_cnt/len(df)*100:.1f}%)")
print(f"Commentaires riches (> 5 mots)                      : {rich_cnt} ({rich_cnt/len(df)*100:.1f}%)")
print("\n" + "="*50 + "\n")

def detect_script(text):
    text_str = str(text)
    has_arabic = bool(re.search(r'[\u0600-\u06FF]', text_str))
    has_latin = bool(re.search(r'[a-zA-Z]', text_str))
    if has_arabic and has_latin:
        return 'Code-Switching (Arabe + Latin)'
    elif has_arabic:
        return 'Arabe Script (Darija/Arabe)'
    elif has_latin:
        return 'Latin (Arabizi / Français)'
    return 'Emojis / Symboles'

df['script'] = df['text'].apply(detect_script)
print("--- 3. DISTRIBUTION DES REGISTRES LINGUISTIQUES ---")
print(df['script'].value_counts(normalize=True) * 100)
print("\n" + "="*50 + "\n")

print("--- 4. ÉCHANTILLONS DE COMMENTAIRES DENSES ET PERTINENTS PAR MARQUE ---")
for brand in df['brand'].unique():
    print(f"\n🏷️ MARQUE : {brand}")
    sub = df[df['brand'] == brand]
    rich_comments = sub[sub['words'] >= 5]['text'].head(5).tolist()
    for i, t in enumerate(rich_comments, 1):
        print(f"  [{i}] \"{t}\"")
