import os
import sys
import pandas as pd

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def inspect_v1_csv():
    path = r"g:\ramypulse\data\scrapimauelle\dataset_ramy_sentiment.csv"
    print(f"==================================================")
    print(f"1. AUDIT: dataset_ramy_sentiment.csv ({path})")
    print(f"==================================================")
    df = pd.read_csv(path)
    print(f"Nombre total de lignes : {len(df)}")
    print(f"Colonnes : {list(df.columns)}")
    print("\n-- Répartition des Marques --")
    print(df['brand'].value_counts(dropna=False))
    print("\n-- Répartition des Sentiments --")
    print(df['sentiment'].value_counts(dropna=False))
    
    print("\n-- Échantillons de commentaires réels --")
    for brand in df['brand'].unique():
        print(f"\n>>> Marque : {brand}")
        sub = df[df['brand'] == brand]
        samples = sub.sample(min(5, len(sub)), random_state=42)
        for i, row in samples.iterrows():
            print(f"[{row['sentiment']}] {row['text']}")

def inspect_tenant_parquets():
    paths = [
        r"g:\ramypulse\data\tenants\ramy_client_001\processed\annotated.parquet",
        r"g:\ramypulse\data\tenants\demo-expo-2026\processed\annotated.parquet",
        r"g:\ramypulse\data\tenants\civital\processed\annotated.parquet"
    ]
    print(f"\n==================================================")
    print(f"2. AUDIT: Datasets Tenants (data/tenants/)")
    print(f"==================================================")
    for path in paths:
        if not os.path.exists(path):
            continue
        df = pd.read_parquet(path)
        print(f"\n--- Fichier : {os.path.basename(os.path.dirname(os.path.dirname(path)))} ({len(df)} lignes) ---")
        print(f"Colonnes : {list(df.columns)}")
        if 'sentiment_label' in df.columns:
            print("Sentiments:", df['sentiment_label'].value_counts(dropna=False).to_dict())
        if 'aspect' in df.columns:
            print("Aspects:", df['aspect'].value_counts(dropna=False).to_dict())
        
        print("Échantillon:")
        samples = df.sample(min(3, len(df)), random_state=42)
        for i, row in samples.iterrows():
            text = row.get('text', '')
            sent = row.get('sentiment_label', '')
            aspect = row.get('aspect', '')
            print(f" [{sent} | {aspect}] {text}")

if __name__ == "__main__":
    inspect_v1_csv()
    inspect_tenant_parquets()
