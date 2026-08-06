import httpx
import asyncio
import time
from typing import Any, Dict, List


class Worker:
    def __init__(self, worker_id : int,timeout : float = 100):
        self.worker_id = worker_id
        self.timeout = httpx.Timeout(timeout)
        self._client = httpx.AsyncClient(timeout = self.timeout)
   
    async def close(self) -> None:
        """Closes the worker's HTTP client if it exists."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def ask(self, question: str, link : str) -> Dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Worker has been closed.")
        start = time.perf_counter()
        try:
            response = await self._client.post(link, json={"query": question})
            latency = time.perf_counter() - start
            if response.status_code == 200:
                data = response.json()
                return {
                        "worker_id": self.worker_id,
                        "query": question,
                        "status_code": 200,
                        "latency_sec": latency,
                        "cache_hit": data.get("cache_hit", False),
                        "cosine_distance": data.get("cosine_distance"),
                        "answer": data.get("answer"),
                        "error": None,
                }
            else:
                return {
                        "worker_id": self.worker_id,
                        "query": question,
                        "status_code": response.status_code,
                        "latency_sec": latency,
                        "cache_hit": False,
                        "error": response.text,
                }
        except Exception as e:
            latency = time.perf_counter() - start
            return {
                    "worker_id": self.worker_id,
                    "query": question,
                    "status_code": None,
                    "latency_sec": latency,
                    "cache_hit": False,
                    "error": str(e),
            }
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()