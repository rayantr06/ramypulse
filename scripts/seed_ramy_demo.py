"""Seed and prepare the Ramy demo tenant for expo runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from core.demo.ramy_seed import (
    issue_demo_api_key,
    resolve_ramy_seed_dataset_path,
    seed_ramy_demo,
    write_frontend_env_file,
)


def _default_dataset_path() -> Path:
    return resolve_ramy_seed_dataset_path()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the Ramy expo tenant from the manual dataset.")
    parser.add_argument("--csv-path", default=str(_default_dataset_path()))
    parser.add_argument("--client-id", default=config.SAFE_EXPO_CLIENT_ID)
    parser.add_argument("--client-name", default="Ramy Demo")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--issue-api-key", action="store_true")
    parser.add_argument("--write-frontend-env", action="store_true")
    parser.add_argument("--frontend-env-path", default=str(PROJECT_ROOT / "frontend" / ".env.local"))
    parser.add_argument("--show-api-key", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    summary = seed_ramy_demo(
        csv_path=Path(args.csv_path),
        client_id=args.client_id,
        client_name=args.client_name,
        reset=args.reset,
    )

    api_key_info: dict[str, str] | None = None
    if args.issue_api_key or args.write_frontend_env:
        api_key_info = issue_demo_api_key(client_id=args.client_id)
        summary["api_key_label"] = api_key_info["label"]
        summary["api_key_key_id"] = api_key_info["key_id"]
        if args.write_frontend_env:
            env_path = write_frontend_env_file(
                api_key=api_key_info["api_key"],
                client_id=args.client_id,
                env_path=Path(args.frontend_env_path),
            )
            summary["frontend_env_path"] = str(env_path)
        if args.show_api_key:
            summary["api_key"] = api_key_info["api_key"]

    if args.as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return

    print(f"client_id={summary['client_id']}")
    print(f"documents_seeded={summary['documents_seeded']}")
    print(f"sources_count={summary['sources_count']}")
    print(f"watchlists_count={summary['watchlists_count']}")
    print(f"campaigns_count={summary['campaigns_count']}")
    print(f"alerts_created={summary['alerts_created']}")
    print(f"recommendations_created={summary['recommendations_created']}")
    if "frontend_env_path" in summary:
        print(f"frontend_env_path={summary['frontend_env_path']}")
    if api_key_info and args.show_api_key:
        print(f"api_key={api_key_info['api_key']}")


if __name__ == "__main__":
    main()
