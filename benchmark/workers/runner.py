import asyncio
import logging
from typing import Any

from .worker import Worker


logger = logging.getLogger(__name__)


class WorkerRunner:
    def __init__(self, endpoint: str):
        if not endpoint:
            raise ValueError("An endpoint is required")

        self.endpoint = endpoint

        self.worker = Worker(
            worker_id=0,
        )

    async def run(
        self,
        queries: list[str],
    ) -> list[dict[str, Any]]:

        if not queries:
            logger.warning("No queries provided")
            return []

        results = []

        try:
            for query_number, query in enumerate(queries, start=1):

                result = await self.worker.ask(
                    question=query,
                    link=self.endpoint,
                )

                results.append(result)

                logger.info(
                    "Endpoint=%s | query=%d/%d | status=%s | hit=%s | latency=%.3fs",
                    self.endpoint,
                    query_number,
                    len(queries),
                    result.get("status_code"),
                    result.get("cache_hit"),
                    result.get("latency_sec", 0),
                )

        finally:
            await self.close()

        return results

    async def close(self):
        await self.worker.close()