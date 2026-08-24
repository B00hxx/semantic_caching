import asyncio
import logging

from .workers.runner import WorkerRunner
from .workers.dataset_loader import load_lmsys_queries


logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


DATASET_DIRECTORY = "benchmark/datasets/lmsys-chat-1m"
MAX_QUERIES = 10000

ENDPOINTS = [
    "http://localhost:8000/chat/ttl_cache",
    "http://localhost:8000/chat/inactivity_cache",
    "http://localhost:8000/chat/hit_count_cache",
]

WORKERS_PER_ENDPOINT = 2


async def main():

    queries = load_lmsys_queries(
        dataset_directory=DATASET_DIRECTORY,
        max_queries=MAX_QUERIES,
    )

    logger.info(
        "Loaded %d queries",
        len(queries),
    )

    runner = WorkerRunner(
        endpoints=ENDPOINTS,
        workers_per_endpoint=WORKERS_PER_ENDPOINT,
    )

    results = await runner.run(
        queries=queries,
    )

    successful = sum(
        result["status_code"] == 200
        for result in results
    )

    cache_hits = sum(
        result.get("cache_hit", False)
        for result in results
    )

    logger.info(
        "Finished: %d/%d successful requests",
        successful,
        len(results),
    )

    logger.info(
        "Cache hits: %d",
        cache_hits,
    )

    if results:
        hit_rate = cache_hits / len(results)

        logger.info(
            "Overall cache hit rate: %.2f%%",
            hit_rate * 100,
        )


if __name__ == "__main__":
    asyncio.run(main())