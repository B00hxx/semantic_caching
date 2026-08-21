import asyncio
import httpx
import os
from dotenv import load_dotenv

from benchmark.clients.auth_client import AuthClient
from benchmark.workers.worker import Worker
from benchmark.clients.cache_client import CacheClient
from benchmark.metrics.classification_metrics import ClassificationMetrics
from benchmark.runners.sequential_runner import SequentialBenchmarkRunner
from benchmark.quora_questions.quora_dataloader import QuoraDataLoader


BASE_URL = "http://127.0.0.1:8000"

ENDPOINT = "/chat/fake_ask"

load_dotenv()

USERNAME = os.getenv("ADMIN_USERNAME")
PASSWORD = os.getenv("ADMIN_PASSWORD")


async def main():

    loader = QuoraDataLoader(
        "benchmark/datasets/train.csv"
    )

    pairs = loader.load(
        limit=10000
    )


    async with httpx.AsyncClient(
        timeout=100
    ) as client:

        # Authenticate
        auth_client = AuthClient(
            client=client,
            base_url=BASE_URL
        )

        token = await auth_client.login(
            username=USERNAME,
            password=PASSWORD
        )

        # Add JWT token to all future requests
        client.headers.update(
            {
                "Authorization": f"Bearer {token}"
            }
        )


        worker = Worker(
            worker_id=14, 
        )


        cache_client = CacheClient(
            client=client,
            base_url=BASE_URL
        )


        metrics = ClassificationMetrics()


        runner = SequentialBenchmarkRunner(
            worker=worker,
            cache_client=cache_client,
            metrics=metrics
        )


        results = await runner.run(
            endpoint=f"{BASE_URL}{ENDPOINT}",
            pairs=pairs
        )


        print("\n===== Benchmark Results =====")

        for key, value in results.items():
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())