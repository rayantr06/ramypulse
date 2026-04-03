"""Point d'entree CLI pour la construction de l'index FAISS et BM25."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_index_04 import build_index


def main() -> None:
    """Execute la construction d'index avec bootstrap du repo."""
    if os.getenv("RAMYPULSE_BUILD_INDEX_DRY_RUN") == "1":
        print("DRY_RUN_OK")
        return
    build_index()


if __name__ == "__main__":
    main()
