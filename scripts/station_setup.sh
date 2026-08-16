#!/usr/bin/env bash
# Installation et entrainement sur la station GPU.
# A copier avec les donnees, puis : bash station_setup.sh
set -e

cd "$(dirname "$0")"

echo "=== 1. Environnement ==="
pip install -q --upgrade transformers datasets accelerate peft bitsandbytes

echo "=== 2. Verification du GPU ==="
python -c "import torch; print('GPU :', torch.cuda.get_device_name(0)); \
print('VRAM :', round(torch.cuda.get_device_properties(0).total_memory/1e9), 'Go')"

echo "=== 3. Entrainement AVEC raisonnement ==="
python train_slm.py --data sft_trace_json --racine . --sortie runs/trace_s1 --seed 1

echo "=== 4. Entrainement SANS raisonnement (temoin de comparaison) ==="
python train_slm.py --data sft_json_only --racine . --sortie runs/json_s1 --seed 1

echo
echo "Termine. Deux modeles dans runs/trace_s1 et runs/json_s1."
echo "Recuperer les deux dossiers pour la suite."
