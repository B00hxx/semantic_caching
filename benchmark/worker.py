import asyncio
import time
from typing import Any, Dict, List
import httpx


class Worker:
    def __init__(self, worker_id: int, timeout: float = 100000.0):
        self.worker_id = worker_id
        self.timeout = httpx.Timeout(timeout)
        self._client = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client == None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    async def _send_request(self, client: httpx.AsyncClient, link: str, question: str) -> Dict[str, Any]:
        client = await self.get_client()
        start = time.perf_counter()
        try:
            response = await client.post(link, json={"query": question})
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

    async def asks(self, link: str, questions: List[str], concurrent: bool = False) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if concurrent:
                tasks = [
                    self._send_request(client, link, q) for q in questions
                ]
                return list(await asyncio.gather(*tasks))
            else:
                results = []
                for q in questions:
                    res = await self._send_request(client, link, q)
                    results.append(res)
                return results