import os
import sys
import json
import re
import pandas as pd

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

MASSINISSA_CSV = r"C:\Users\AZ\.cache\kagglehub\datasets\massinissaissighid\algerian-corpus-algerian-dataset\versions\1\total.csv"
V1_CSV = r"g:\ramypulse\data\scrapimauelle\dataset_ramy_sentiment.csv"
TENANT_DEMO_PARQUET = r"g:\ramypulse\data\tenants\demo-expo-2026\processed\annotated.parquet"
TENANT_RAMY_PARQUET = r"g:\ramypulse\data\tenants\ramy_client_001\processed\annotated.parquet"

OUTPUT_JSONL = r"g:\ramypulse\data\processed\master_seed_7k.jsonl"

def is_spam_or_tag_list(text):
    if not isinstance(text, str):
        return True
    text = text.strip()
    if len(text) < 6:
        return True
    # Detect tag lists (multiple capitalized names or @ handles without natural words)
    words = text.split()
    if len(words) > 5 and sum(1 for w in words if w.istitle()) / len(words) > 0.7:
        return True
    if text.count('@') > 2:
        return True
    if 'shared text' in text.lower():
        return True
    return False

def clean_massinissa():
    print("Processing Massinissa dataset...")
    df = pd.read_csv(MASSINISSA_CSV)
    # Exclude politics
    df = df[df['Topic'] != 'politic']
    
    cleaned = []
    sentiment_map = {-1: 'negatif', 0: 'neutre', 1: 'positif'}
    
    for _, row in df.iterrows():
        text = str(row['comment']).strip()
        if is_spam_or_tag_list(text):
            continue
        pol = row['pol']
        sentiment = sentiment_map.get(pol, 'neutre')
        topic = str(row['Topic']).strip().lower()
        
        cleaned.append({
            "text": text,
            "sentiment_label": sentiment,
            "source": "massinissa_algerian_corpus",
            "topic": topic,
            "brand": None,
            "aspect": None
        })
    print(f"  -> Massinissa cleaned: {len(cleaned)} items (from {len(df)})")
    return cleaned

def clean_v1_csv():
    print("Processing V1 Scraped CSV (Ramy & Hamoud)...")
    df = pd.read_csv(V1_CSV)
    cleaned = []
    sentiment_map = {'positive': 'positif', 'negative': 'negatif', 'neutral': 'neutre', 'mixed': 'mixte'}
    
    for _, row in df.iterrows():
        text = str(row['text']).strip()
        if is_spam_or_tag_list(text):
            continue
        raw_sent = str(row['sentiment']).lower()
        sentiment = sentiment_map.get(raw_sent, 'neutre')
        brand = str(row['brand']).strip()
        
        cleaned.append({
            "text": text,
            "sentiment_label": sentiment,
            "source": "ramypulse_v1_facebook",
            "topic": "fmcg_beverages",
            "brand": brand,
            "aspect": None
        })
    print(f"  -> V1 CSV cleaned: {len(cleaned)} items (from {len(df)})")
    return cleaned

def clean_tenants():
    print("Processing Tenant Parquets...")
    cleaned = []
    
    if os.path.exists(TENANT_DEMO_PARQUET):
        df_demo = pd.read_parquet(TENANT_DEMO_PARQUET)
        sentiment_map = {'positif': 'positif', 'négatif': 'negatif', 'negatif': 'negatif', 'neutre': 'neutre', 'très_négatif': 'negatif'}
        for _, row in df_demo.iterrows():
            text = str(row['text']).strip()
            if is_spam_or_tag_list(text):
                continue
            raw_sent = str(row.get('sentiment_label', '')).lower()
            sent = sentiment_map.get(raw_sent, 'neutre')
            aspect = row.get('aspect', '')
            brand = row.get('brand', '')
            
            cleaned.append({
                "text": text,
                "sentiment_label": sent,
                "source": "tenant_demo_expo",
                "topic": "fmcg_beverages",
                "brand": brand if brand else None,
                "aspect": aspect if aspect else None
            })
            
    if os.path.exists(TENANT_RAMY_PARQUET):
        df_ramy = pd.read_parquet(TENANT_RAMY_PARQUET)
        for _, row in df_ramy.iterrows():
            text = str(row['text']).strip()
            if is_spam_or_tag_list(text):
                continue
            raw_sent = str(row.get('sentiment_label', '')).lower()
            sent = 'negatif' if 'neg' in raw_sent else 'neutre'
            aspect = row.get('aspect', '')
            
            cleaned.append({
                "text": text,
                "sentiment_label": sent,
                "source": "tenant_ramy_client",
                "topic": "fmcg_beverages",
                "brand": "Ramy",
                "aspect": aspect if aspect else None
            })
            
    print(f"  -> Tenant datasets cleaned: {len(cleaned)} items")
    return cleaned

def main():
    os.makedirs(os.path.dirname(OUTPUT_JSONL), exist_ok=True)
    all_seeds = []
    
    all_seeds.extend(clean_massinissa())
    all_seeds.extend(clean_v1_csv())
    all_seeds.extend(clean_tenants())
    
    # Deduplicate by text
    unique_texts = set()
    dedup_seeds = []
    for item in all_seeds:
        norm_text = re.sub(r'\s+', ' ', item['text'].lower())
        if norm_text not in unique_texts:
            unique_texts.add(norm_text)
            dedup_seeds.append(item)
            
    print(f"\nTotal Unique Master Seeds: {len(dedup_seeds)}")
    
    # Save to JSONL
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for item in dedup_seeds:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"Master seed corpus successfully written to: {OUTPUT_JSONL}")

if __name__ == "__main__":
    main()
