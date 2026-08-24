import asyncio
import logging
from typing import Any

from .worker import Worker


logger = logging.getLogger(__name__)


class WorkerRunner:
    def __init__(
        self,
        endpoints: list[str],
        workers_per_endpoint: int = 1,
        timeout: float = 100,
    ):
        if not endpoints:
            raise ValueError("At least one endpoint is required")

        if workers_per_endpoint <= 0:
            raise ValueError(
                "workers_per_endpoint must be greater than 0"
            )

        self.endpoints = endpoints
        self.workers_per_endpoint = workers_per_endpoint
        self.timeout = timeout

        # Each tuple contains:
        # (Worker instance, endpoint assigned to that worker)
        self.workers: list[tuple[Worker, str]] = []

        worker_id = 0

        for endpoint in endpoints:
            for _ in range(workers_per_endpoint):

                worker = Worker(
                    worker_id=worker_id,
                    timeout=timeout,
                )

                self.workers.append(
                    (worker, endpoint)
                )

                worker_id += 1

        logger.info(
            "Initialized WorkerRunner with %d workers across %d endpoints",
            len(self.workers),
            len(self.endpoints),
        )

        for endpoint in self.endpoints:
            count = sum(
                1
                for _, worker_endpoint in self.workers
                if worker_endpoint == endpoint
            )

            logger.info(
                "Endpoint %s -> %d workers",
                endpoint,
                count,
            )

    async def _worker_loop(
        self,
        worker: Worker,
        endpoint: str,
        queries: list[str],
        results: list[dict[str, Any]],
    ) -> None:

        logger.info(
            "Worker %d started | endpoint=%s | queries=%d",
            worker.worker_id,
            endpoint,
            len(queries),
        )

        for query in queries:

            result = await worker.ask(
                question=query,
                link=endpoint,
            )

            results.append(result)

            logger.info(
                "Worker %d | endpoint=%s | status=%s | hit=%s | latency=%.3fs",
                worker.worker_id,
                endpoint,
                result.get("status_code"),
                result.get("cache_hit"),
                result.get("latency_sec", 0),
            )

        logger.info(
            "Worker %d finished | endpoint=%s",
            worker.worker_id,
            endpoint,
        )

    def _distribute_queries(
        self,
        queries: list[str],
    ) -> list[list[str]]:

        number_of_workers = len(self.workers)

        worker_queries: list[list[str]] = [
            []
            for _ in range(number_of_workers)
        ]

        # Round-robin distribution.
        #
        # Example with 6 workers:
        #
        # query 0 -> worker 0
        # query 1 -> worker 1
        # query 2 -> worker 2
        # query 3 -> worker 3
        # ...
        # query 6 -> worker 0
        #
        for index, query in enumerate(queries):

            worker_index = index % number_of_workers

            worker_queries[worker_index].append(query)

        return worker_queries

    async def run(
        self,
        queries: list[str],
    ) -> list[dict[str, Any]]:

        if not queries:
            logger.warning("No queries provided")
            return []

        logger.info(
            "Starting workload | queries=%d | workers=%d",
            len(queries),
            len(self.workers),
        )

        worker_queries = self._distribute_queries(queries)

        results: list[dict[str, Any]] = []

        tasks = []

        for index, (worker, endpoint) in enumerate(self.workers):

            queries_for_worker = worker_queries[index]

            if not queries_for_worker:
                continue

            task = asyncio.create_task(
                self._worker_loop(
                    worker=worker,
                    endpoint=endpoint,
                    queries=queries_for_worker,
                    results=results,
                )
            )

            tasks.append(task)

        try:

            await asyncio.gather(*tasks)

        finally:

            await self.close()

        logger.info(
            "Workload completed | results=%d",
            len(results),
        )

        return results

    async def close(self) -> None:

        if not self.workers:
            return

        logger.info(
            "Closing %d workers",
            len(self.workers),
        )

        await asyncio.gather(
            *(
                worker.close()
                for worker, _ in self.workers
            ),
            return_exceptions=True,
        )

        logger.info("All workers closed")