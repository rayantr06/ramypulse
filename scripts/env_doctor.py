"""Fail-fast environment validation for the Ramy expo demo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.demo.ramy_seed import RAMY_FACEBOOK_PAGE_URL, RAMY_INSTAGRAM_PROFILE_URL
from core.runtime.env_doctor import assert_startup_ready, collect_startup_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Ramy demo runtime before startup.")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--skip-services", action="store_true")
    parser.add_argument("--skip-urls", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = collect_startup_validation(
        service_checks=[] if args.skip_services else None,
        public_urls=[] if args.skip_urls else [RAMY_FACEBOOK_PAGE_URL, RAMY_INSTAGRAM_PROFILE_URL],
        timeout=args.timeout,
    )

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok={report['ok']}")
        for item in report["required_env"]:
            print(f"env {item['key']} ok={item['ok']} detail={item['detail']}")
        for item in report["services"]:
            print(
                f"service {item['id']} ok={item['ok']} "
                f"status={item['status_code']} detail={item['detail']}"
            )
        for item in report.get("urls", []):
            print(
                f"url {item['url']} ok={item['ok']} "
                f"status={item['status_code']} detail={item['detail']}"
            )
        print(f"database ok={report['database']['ok']} detail={report['database']['detail']}")

    assert_startup_ready(report)


if __name__ == "__main__":
    main()
