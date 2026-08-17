import os
import sys
import pandas as pd

# Set UTF-8 encoding for stdout
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

csv_path = r"C:\Users\AZ\.cache\kagglehub\datasets\massinissaissighid\algerian-corpus-algerian-dataset\versions\1\total.csv"

def main():
    print(f"Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Total Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}\n")

    print("=== Sentiment Polarity ('pol') Distribution ===")
    print(df['pol'].value_counts(dropna=False))

    print("\n=== Topic Distribution ('Topic') ===")
    print(df['Topic'].value_counts(dropna=False))

    print("\n=== Crosstab: Topic vs Polarity ===")
    print(pd.crosstab(df['Topic'], df['pol'], margins=True))

    print("\n=== Echantillon de commentaires par Categorie ===")
    for topic in df['Topic'].unique():
        print(f"\n--- Topic: {topic} ---")
        sub_df = df[df['Topic'] == topic]
        sample = sub_df.sample(min(3, len(sub_df)), random_state=42)
        for idx, row in sample.iterrows():
            print(f"[{row['pol']}] {row['comment']}")

if __name__ == "__main__":
    main()
