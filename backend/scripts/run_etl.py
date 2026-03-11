"""CLI script to run the CVM board-member ETL pipeline."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `app.*` imports resolve.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.etl.orchestrator import run_etl  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the CVM board-member network ETL pipeline.",
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=None,
        help="Years to download (default: 2021-2026). Example: --years 2023 2024",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force re-download of cached files.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    summary = await run_etl(years=args.years, force_download=args.force)
    print("\n── ETL Summary ──")
    print(json.dumps(summary, indent=2, default=str))

    if summary.get("errors"):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(_main())
