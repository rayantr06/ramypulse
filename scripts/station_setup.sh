#!/usr/bin/env bash
# Installation et entrainement sur la station GPU.
# A copier avec les donnees, puis : bash station_setup.sh
#
# Le script n'utilise jamais `python` nu : il appelle l'interpreteur du venv par
# son chemin. L'environnement conda `proto` de la station est actif par defaut et
# ne porte pas torch ; s'en remettre a `source activate` a deja fait echouer deux
# lancements, parce que l'activation ne survit pas a un nouveau shell.
set -e

cd "$(dirname "$0")"
VENV="$PWD/.venv"
PY="$VENV/bin/python"

echo "=== 1. Environnement ==="
if [ ! -x "$PY" ]; then
  python3 -m venv "$VENV"
fi
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q torch --index-url https://download.pytorch.org/whl/cu121
"$PY" -m pip install -q transformers datasets accelerate peft bitsandbytes

echo "=== 2. Verification du GPU ==="
"$PY" -c "import torch; print('GPU  :', torch.cuda.get_device_name(0)); \
print('VRAM :', round(torch.cuda.get_device_properties(0).total_memory/1e9), 'Go'); \
print('CUDA :', torch.version.cuda)"

echo
echo "=== 3. Entrainement AVEC raisonnement ==="
"$PY" train_slm.py --data sft_trace_json --racine . --sortie runs/trace_s1 --seed 1

echo
echo "=== 4. Entrainement SANS raisonnement (temoin de comparaison) ==="
"$PY" train_slm.py --data sft_json_only --racine . --sortie runs/json_s1 --seed 1

echo
echo "Termine. Deux modeles dans runs/trace_s1 et runs/json_s1."
echo "Pour relancer une seule etape :"
echo "  $PY train_slm.py --data sft_trace_json --racine . --sortie runs/trace_s1 --seed 1"
