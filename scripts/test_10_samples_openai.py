import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env")
    sys.exit(1)

import openai
client = openai.OpenAI(api_key=api_key)

SYSTEM_PROMPT = """Tu es un annotateur expert en linguistique et analyse du sentiment consommateur algérien (Darija, Arabizi, Français, Arabe).
Ton rôle est de générer un exemple d'entraînement au format ChatML enrichi d'une TRACE DE RAISONNEMENT EN 5 ÉTAPES (`<think>`) selon la méthodologie SYNTH (Pleïas).

Pour le commentaire consommateur donné, tu dois produire EXACTEMENT ce format :

<|im_start|>user
Analyse ce commentaire consommateur algérien et extrais les informations structurées :

"[TEXTE_BRUT]"
<|im_end|>
<|im_start|>assistant
<think>
### 1. Décomposition Linguistique
- Langue dominante : [Darija / Arabizi / Français / Arabe / Mixte]
- Mots-clés & Expressions : [Lister les expressions clés et leurs sens]
- Code-switching / Emprunts : [Mots français ou arabes empruntés]

### 2. Analyse Sentimentale & Intensité
- Signal : [● POSITIF / ● NÉGATIF / ○ NEUTRE / ◐ MIXTE]
- Tonalité : [Ironie, Sarcasme, Éloge, Déception, Colère, etc.]

### 3. Extraction d'Entités (Marque & Produit)
- Marque : [Nom de la marque ou "Non mentionnée"]
- Produit : [Catégorie de produit ou "Non mentionné"]

### 4. Extraction d'Aspects (Qualité, Prix, SAV, Goût, Emballage, etc.)
- [Aspect 1] : [Extrait] -> [POSITIF / NÉGATIF / NEUTRE]

### 5. Évaluation de Criticité
- Alerte Qualité / Sanitaire : [OUI / NON]
- Niveau de sévérité : [Faible / Moyen / Élevé / Critique]
</think>

{
  "sentiment": "[positif | negatif | neutre | mixte]",
  "confiance_sentiment": [0.0 à 1.0],
  "est_sarcastique": [true | false],
  "marque": [string ou null],
  "produit": [string ou null],
  "aspects": [
    {"aspect": "[nom_aspect]", "sentiment": "[positif|negatif|neutre]", "extrait": "[extrait]"}
  ],
  "alerte_qualite": [true | false],
  "langue_dominante": "[darija_arabizi | darija_arabe | francais | arabe_msa | mixte]",
  "resume": "[Résumé en 1 phrase en français]"
}
<|im_end|>
"""

# 10 Interesting and representative test comments (Diverse languages, sentiments, alerts, brands)
TEST_SAMPLES = [
    {"id": 1, "category": "Darija Arabizi + Alerte Qualité + SAV", "text": "Wallah le yaourt Soummam ta3 lyoum fassad, ri7a kharjna w le goût 7amad. Dert reclamation f la page ta3hom w ma jabounich, hchouma 3lihoum."},
    {"id": 2, "category": "Arabe DZ + Éloge Marque Ramy", "text": "ياغورت رامي عصير الرمان بزاف بنين وصحي، جودة ممتازة وسعر في المتناول، برافو رامي"},
    {"id": 3, "category": "Code-Switching + Hausse de Prix", "text": "Le jus Hamoud top goût كعادتهم mais franchement les prix rahom yzido kol mois c'est abusé pour le consommateur."},
    {"id": 4, "category": "Plainte Produit Périmé / Sanitaire", "text": "شريت قرعة حليب صومام لقيتها خاسرة ومكتوب فيها تاريخ اليوم، ردو بالكم يا خاوتي قبل ما تشروا."},
    {"id": 5, "category": "Sarcasme / Ironie Darija", "text": "يعطيهم الصحة صومام، نقصو فالحجم وزادو فالبري، خدمة احترافية ما شاء الله 👏"},
    {"id": 6, "category": "Français pur + Packaging", "text": "J'adore le nouvel emballage des boissons Ramy, très pratique et moderne mais le bouchon est parfois difficile à ouvrir."},
    {"id": 7, "category": "Arabizi + Rupture de Stock", "text": "Ma lqitsh Hamoud Selecto f les superérettes ta3 Bab Ezzouar, dima rupture de stock f les week-ends !"},
    {"id": 8, "category": "Critique Neutre / Comparaison", "text": "المنتج عادي جدا مقارنة بالمنافسين، لا جديد يذكر ولا قديم يعاد."},
    {"id": 9, "category": "Plainte Service Client / Réclamation", "text": "Envoyé un message au service consommateur Candia depuis une semaine sans aucune réponse. Zero suivi client."},
    {"id": 10, "category": "Positif + Rapport Qualité/Prix", "text": "Meilleur rapport qualité prix f le marché algérien, le goût fraise ta3 Ramy reste le meilleur."}
]

def main():
    OUTPUT_FILE = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'test_10_results.md'
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("Executing synchronous quality test on 10 diverse Algerian consumer comments...")
    
    results_md = ["# 🧪 Test de Qualité SYNTH (Pleïas) sur 10 Exemples Consommateurs Algériens\n"]
    results_md.append("> Généré via l'API OpenAI Direct (`gpt-4o-mini`)\n\n---\n")

    for sample in TEST_SAMPLES:
        print(f"[{sample['id']}/10] Processing ({sample['category']})...")
        try:
            res = client.chat.completions.create(
                model="gpt-5.4-mini",
                max_completion_tokens=2500,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Génère la trace SYNTH pour ce commentaire :\n\"{sample['text']}\""}
                ]
            )
            output_text = res.choices[0].message.content.strip()
            
            results_md.append(f"## 📌 Exemple #{sample['id']} — {sample['category']}\n")
            results_md.append(f"**Texte brut :** `\"{sample['text']}\"`\n")
            results_md.append("### Résultat ChatML + Trace `<think>` :\n")
            results_md.append("```xml\n" + output_text + "\n```\n\n---\n")
            
        except Exception as e:
            print(f"Error on sample {sample['id']}: {e}")

    final_content = "\n".join(results_md)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"\nTest complete! Results saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
