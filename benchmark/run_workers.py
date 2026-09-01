import asyncio
import logging

from .workers.runner import WorkerRunner
from .workers.dataset_loader import load_lmsys_queries


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


DATASET_DIRECTORY = "benchmark/datasets/lmsys-chat-1m"

MAX_QUERIES = 100

ENDPOINTS = [
    ("Hit Count", "http://127.0.0.1:8000/chat/hit_count_cache"),
]


async def main():

    queries = load_lmsys_queries(
        dataset_directory=DATASET_DIRECTORY,
        max_queries=MAX_QUERIES,
    )

    logger.info("Loaded %d queries", len(queries))

    for name, endpoint in ENDPOINTS:

        logger.info("")
        logger.info("=" * 70)
        logger.info("STARTING: %s", name)
        logger.info("ENDPOINT: %s", endpoint)
        logger.info("=" * 70)

        runner = WorkerRunner(
            endpoint=endpoint,
        )

        results = await runner.run(
            queries=queries,
        )

        successful = sum(
            r["status_code"] == 200
            for r in results
        )

        cache_hits = sum(
            r.get("cache_hit", False)
            for r in results
            if r["status_code"] == 200
        )

        hit_rate = (
            cache_hits / successful
            if successful
            else 0
        )

        logger.info("")
        logger.info(
            "%s COMPLETE | successful=%d/%d | hits=%d | hit_rate=%.2f%%",
            name,
            successful,
            len(results),
            cache_hits,
            hit_rate * 100,
        )


if __name__ == "__main__":
    asyncio.run(main())