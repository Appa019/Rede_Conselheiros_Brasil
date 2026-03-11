"""CLI script to compute and save graph metrics."""

import argparse
import asyncio
import logging
import sys

sys.path.insert(0, ".")

from app.graph.neo4j_client import Neo4jClient
from app.graph.metrics import compute_and_save_metrics


async def main() -> None:
    parser = argparse.ArgumentParser(description="Compute graph metrics")
    parser.add_argument("--year", type=int, default=None, help="Filter by year")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    async with Neo4jClient() as client:
        results = await compute_and_save_metrics(client, year=args.year)

    print("\nMetrics Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
