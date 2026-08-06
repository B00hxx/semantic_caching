import asyncio
import json
import statistics
import time
from typing import Any, Dict, List
from benchmark.worker import Worker
from benchmark.questions import QUESTIONS


async def run_benchmark(num_workers: int = 1, link: str = "http://127.0.0.1:8000/chat/ask", concurrent: bool = True,) -> None:
    workers = [Worker(worker_id=i) for i in range(num_workers)]
    start_total = time.perf_counter()
    tasks = [worker.asks(link=link, questions=QUESTIONS, concurrent=concurrent) for worker in workers]
    worker_results = await asyncio.gather(*tasks)
    total_duration = time.perf_counter() - start_total
    all_results: List[Dict[str, Any]] = [item for sublist in worker_results for item in sublist]
    hits = [r for r in all_results if r.get("cache_hit")]
    misses = [r for r in all_results if not r.get("cache_hit") and r.get("status_code") == 200]
    errors = [r for r in all_results if r.get("status_code") != 200]
    hit_latencies = [r["latency_sec"] for r in hits]
    miss_latencies = [r["latency_sec"] for r in misses]
    total_requests = len(all_results)
    summary = {
        "total_requests": total_requests,
        "total_duration_sec": round(total_duration, 3),
        "requests_per_sec": (
            round(total_requests / total_duration, 2)
            if total_duration > 0
            else 0.0
        ),
        "cache_hit_rate": (
            f"{(len(hits) / total_requests * 100):.1f}%"
            if total_requests
            else "0%"
        ),
        "avg_hit_latency_sec": (
            round(statistics.mean(hit_latencies), 4) if hit_latencies else 0.0
        ),
        "avg_miss_latency_sec": (
            round(statistics.mean(miss_latencies), 4) if miss_latencies else 0.0
        ),
        "errors_count": len(errors),
    }

    print("\n================ BENCHMARK SUMMARY ================")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("====================================================\n")

    output = {"summary": summary, "detailed_results": all_results}

    with open("results.json", "w") as f:
        json.dump(output, f, indent=4)

    print("Benchmark complete. Detailed results saved to results.json.")


if __name__ == "__main__":
    asyncio.run(run_benchmark(num_workers=10, concurrent=False))