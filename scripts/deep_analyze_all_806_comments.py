import pandas as pd
import re
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv('g:/ramypulse/scraping/output/all_comments.csv')

print(f"=== 🔬 ANALYSE DÉTAILLÉE EXHAUSTIVE DE L'ENSEMBLE DES 806 COMMENTAIRES ===\n")

# Topic Classifier
def classify_comment(text):
    t = str(text).lower()
    
    # 1. Distribution & Rupture
    if any(k in t for k in ['ثلاجات', 'ثلاجة', 'وفرولنا', 'روپتير', 'ريبيتير', 'rupture', 'indisponibilité', 'ماكانش', 'مكانش', 'ما لقيتش', 'malqitch', 'مفقود', 'السوق']):
        return "📦 Distribution & Rupture de stock"
        
    # 2. Recommandations Produit & Recettes (Goût, Saveurs, Bio, Ingrédients)
    elif any(k in t for k in ['ذوق', 'نكهة', 'نكهات', 'goût', 'saveur', 'عنب', 'أناناس', 'اناناس', 'bio', 'طبيعي', 'sans lactose', 'نقصو', 'سكر', 'sucre']):
        return "🍎 Ingrédients, Saveurs & Recettes"
        
    # 3. Prix & Pouvoir d'achat
    elif any(k in t for k in ['سعر', 'سعرها', 'غالي', 'بري', 'prix', 'cher', 'nzido']):
        return "💰 Prix & Rapport Qualité/Prix"
        
    # 4. Plaintes Qualité / Problème Sanitaire / Emballage
    elif any(k in t for k in ['خاسر', 'حامض', 'فاسد', 'ريح', 'ri7a', 'périmé', 'perime', 'bouchon', 'emballage', 'محقورة']):
        return "⚠️ Plaintes Qualité & Service Client"
        
    # 5. Sponsorship, Social & RSE / Employés
    elif any(k in t for k in ['العمال', 'تكرمو', 'اليتامى', 'الطلبة', 'مبروك', 'bravo', 'soutien', 'المناسبات']):
        return "🤝 RSE, Événements & Relation Employés"
        
    # 6. Éloge Général / Compliment marque
    elif any(k in t for k in ['روعة', 'طوب', 'احسن', 'meilleur', 'ما شاء الله', 'ماشاء الله', 'بنين', 'متميز', 'القمة', 'top', 'machallah', 'machaallah']):
        return "❤️ Éloge & Satisfaction Marque"
        
    return "💬 Echanges Généraux & Remarques Diverses"

df['topic'] = df['text'].apply(classify_comment)

print("--- 1. VENTILATION THÉMATIQUE DES 806 COMMENTAIRES ---")
print(df['topic'].value_counts())
print("\n" + "="*70 + "\n")

print("--- 2. ANALYSE PROFONDE PAR MARQUE & THÉMATIQUE ---")

for brand in ['Ramy', 'Hamoud Boualem', 'Soummam', 'Candia Algérie']:
    print(f"\n==================== 🏢 MARQUE : {brand} ====================")
    b_df = df[df['brand'] == brand]
    print(f"Total commentaires : {len(b_df)}")
    print(b_df['topic'].value_counts())
    print("\n--- Verbatims Clés Extraits ---")
    
    # Show samples from different topics
    topics = b_df['topic'].unique()
    for top in topics:
        subset = b_df[(b_df['topic'] == top) & (b_df['text'].str.len() > 15)]
        if not subset.empty:
            print(f"\n📌 Category: {top}")
            samples = subset['text'].head(4).tolist()
            for i, s in enumerate(samples, 1):
                print(f"  {i}. \"{s}\"")
