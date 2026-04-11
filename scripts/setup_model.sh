#!/usr/bin/env bash
# ============================================================================
# setup_model.sh — Télécharge les fichiers lourds du modèle DziriBERT
# ============================================================================
#
# Usage:
#   bash scripts/setup_model.sh
#
# Ce script télécharge model.safetensors (475 Mo)
# depuis Google Drive vers models/dziribert-sentiment/.
# Les autres fichiers (config, tokenizer, vocab) sont déjà dans git.
#
# Prérequis: gdown (pip install gdown) OU curl
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODEL_DIR="$PROJECT_ROOT/models/dziribert-sentiment"

# Google Drive file ID (dossier RamyPulse/models/dziribert-sentiment/)
# Pour mettre à jour cet ID: ouvrir le fichier dans Drive → Partager → Copier le lien
# Le lien contient l'ID: https://drive.google.com/file/d/<FILE_ID>/view
MODEL_SAFETENSORS_ID="${MODEL_SAFETENSORS_ID:-REMPLACER_PAR_FILE_ID}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------------------------------------------------------------------------
# Vérification préalable
# ---------------------------------------------------------------------------
mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_DIR/model.safetensors" ]; then
    SAFETENSORS_SIZE=$(wc -c < "$MODEL_DIR/model.safetensors")
    if [ "$SAFETENSORS_SIZE" -gt 400000000 ]; then
        info "model.safetensors ($(numfmt --to=iec "$SAFETENSORS_SIZE")) déjà présent."
        info "Pour forcer le re-téléchargement: rm models/dziribert-sentiment/model.safetensors"
        exit 0
    fi
fi

# ---------------------------------------------------------------------------
# Méthode 1: gdown (recommandé — gère les gros fichiers Google Drive)
# ---------------------------------------------------------------------------
download_with_gdown() {
    local file_id="$1"
    local output="$2"
    local desc="$3"

    info "Téléchargement de $desc via gdown..."
    gdown "https://drive.google.com/uc?id=$file_id" -O "$output" --fuzzy
}

# ---------------------------------------------------------------------------
# Méthode 2: curl fallback
# ---------------------------------------------------------------------------
download_with_curl() {
    local file_id="$1"
    local output="$2"
    local desc="$3"

    info "Téléchargement de $desc via curl..."
    # Première requête pour obtenir le token de confirmation
    local confirm_url="https://drive.google.com/uc?export=download&id=$file_id"
    local confirm_code
    confirm_code=$(curl -sc /tmp/gdrive_cookie "$confirm_url" | \
        grep -oP 'confirm=\K[^&]+' || true)

    if [ -n "$confirm_code" ]; then
        curl -Lb /tmp/gdrive_cookie \
            "${confirm_url}&confirm=$confirm_code" -o "$output"
    else
        # Fichier petit, pas de confirmation nécessaire
        curl -L "$confirm_url" -o "$output"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if [ "$MODEL_SAFETENSORS_ID" = "REMPLACER_PAR_FILE_ID" ]; then
    warn "Le file ID Google Drive n'est pas encore configuré."
    echo ""
    echo "  Option A — Copier manuellement depuis Google Drive:"
    echo "    1. Ouvrir: https://drive.google.com (dossier RamyPulse/models/dziribert-sentiment/)"
    echo "    2. Télécharger model.safetensors (475 Mo)"
    echo "    3. Copier dans: $MODEL_DIR/"
    echo ""
    echo "  Option B — Configurer le file ID:"
    echo "    1. Clic droit sur model.safetensors dans Drive → 'Obtenir le lien'"
    echo "    2. Extraire l'ID du lien (entre /d/ et /view)"
    echo "    3. Relancer: MODEL_SAFETENSORS_ID=xxx bash scripts/setup_model.sh"
    echo ""
    exit 1
fi

# Choisir la méthode de téléchargement
if command -v gdown &> /dev/null; then
    DOWNLOAD_FN=download_with_gdown
else
    warn "gdown non trouvé. Installation recommandée: pip install gdown"
    warn "Fallback sur curl (peut échouer pour les gros fichiers)."
    DOWNLOAD_FN=download_with_curl
fi

# Télécharger model.safetensors (475 Mo)
if [ ! -f "$MODEL_DIR/model.safetensors" ] || [ "$(wc -c < "$MODEL_DIR/model.safetensors")" -lt 400000000 ]; then
    $DOWNLOAD_FN "$MODEL_SAFETENSORS_ID" "$MODEL_DIR/model.safetensors" "model.safetensors (475 Mo)"
else
    info "model.safetensors déjà présent, skip."
fi

# ---------------------------------------------------------------------------
# Vérification post-téléchargement
# ---------------------------------------------------------------------------
echo ""
info "=== Vérification du dossier modèle ==="
ls -lh "$MODEL_DIR/"

SAFETENSORS_SIZE=$(wc -c < "$MODEL_DIR/model.safetensors" 2>/dev/null || echo 0)
if [ "$SAFETENSORS_SIZE" -lt 400000000 ]; then
    error "model.safetensors semble corrompu ($(numfmt --to=iec "$SAFETENSORS_SIZE")). Attendu: ~475 Mo."
fi

info "Modèle DziriBERT-sentiment prêt dans $MODEL_DIR/"
info "Lancer l'app: uvicorn main:app --reload"
