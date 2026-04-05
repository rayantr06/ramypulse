"""CLI one-shot pour le runtime d'automatisation RamyPulse."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from core.database import DatabaseManager
from core.runtime.automation_runtime import run_automation_cycle


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute un cycle one-shot du runtime RamyPulse.")
    parser.add_argument("--client-id", default=config.DEFAULT_CLIENT_ID)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--now", default=None)
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-normalization", action="store_true")
    parser.add_argument("--skip-health", action="store_true")
    parser.add_argument("--skip-alerts", action="store_true")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    database = DatabaseManager()
    database.create_tables()
    database.close()

    result = run_automation_cycle(
        client_id=args.client_id,
        run_sync=not args.skip_sync,
        run_normalization=not args.skip_normalization,
        run_health=not args.skip_health,
        run_alerts=not args.skip_alerts,
        batch_size=args.batch_size,
        now=args.now,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
