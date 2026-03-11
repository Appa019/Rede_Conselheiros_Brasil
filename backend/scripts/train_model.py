"""CLI script to run ML training pipeline."""

import asyncio
import logging
import sys

sys.path.insert(0, ".")

import argparse

from app.graph.neo4j_client import Neo4jClient
from app.ml.train import run_training_pipeline


async def main() -> None:
    parser = argparse.ArgumentParser(description="Train ML models")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    async with Neo4jClient() as client:
        results = await run_training_pipeline(client)

    print("\nTraining Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
