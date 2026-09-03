import asyncio
import logging
from typing import Any

from .worker import Worker


logger = logging.getLogger(__name__)


class WorkerRunner:
    def __init__(
        self,
        endpoint: str,
        worker_count: int = 10,
        timeout: float = 120,
    ):
        if not endpoint:
            raise ValueError("An endpoint is required")
        if worker_count < 1:
            raise ValueError("worker_count must be at least 1")

        self.endpoint = endpoint
        self.workers = [
            Worker(worker_id=worker_id, timeout=timeout)
            for worker_id in range(worker_count)
        ]

    async def _run_worker(
        self,
        worker: Worker,
        queries: list[tuple[int, str]],
    ) -> list[tuple[int, dict[str, Any]]]:
        results = []

        for query_index, query in queries:
            result = await worker.ask(
                question=query,
                link=self.endpoint,
            )
            results.append((query_index, result))

        return results

    async def run(
        self,
        queries: list[str],
    ) -> list[dict[str, Any]]:

        if not queries:
            logger.warning("No queries provided")
            return []

        try:
            assigned_queries = [[] for _ in self.workers]
            for query_index, query in enumerate(queries):
                assigned_queries[query_index % len(self.workers)].append(
                    (query_index, query)
                )

            worker_results = await asyncio.gather(
                *(
                    self._run_worker(worker, worker_queries)
                    for worker, worker_queries in zip(
                        self.workers,
                        assigned_queries,
                    )
                    if worker_queries
                )
            )
            indexed_results = [
                item
                for worker_result in worker_results
                for item in worker_result
            ]
            indexed_results.sort(key=lambda item: item[0])
            results = [result for _, result in indexed_results]

            for query_number, result in enumerate(results, start=1):
                logger.info(
                    "Endpoint=%s | query=%d/%d | worker=%s | status=%s | hit=%s | latency=%.3fs",
                    self.endpoint,
                    query_number,
                    len(queries),
                    result.get("worker_id"),
                    result.get("status_code"),
                    result.get("cache_hit"),
                    result.get("latency_sec", 0),
                )

        finally:
            await self.close()

        return results

    async def close(self):
        await asyncio.gather(*(worker.close() for worker in self.workers))