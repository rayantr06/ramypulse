"""Measure tenant indexing runtime."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.tenancy.artifact_refresh import refresh_tenant_artifacts


def main() -> None:
    """Run a tenant refresh and emit a JSON timing summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    summary = refresh_tenant_artifacts(client_id=args.client_id, force=True)
    elapsed = time.perf_counter() - started
    print(json.dumps({"client_id": args.client_id, "docs": summary["documents"], "index_seconds": round(elapsed, 3)}))


if __name__ == "__main__":
    main()
