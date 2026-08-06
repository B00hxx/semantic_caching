from typing import List

from benchmark.workers.worker import Worker
from benchmark.clients.cache_client import CacheClient
from benchmark.metrics.classification_metrics import ClassificationMetrics
from benchmark.quora_questions.question_pair import QuoraQuestionsPair


class SequentialBenchmarkRunner:

    def __init__(
        self,
        worker: Worker,
        cache_client: CacheClient,
        metrics: ClassificationMetrics
    ):
        self.worker = worker
        self.cache_client = cache_client
        self.metrics = metrics


    async def run(
        self,
        endpoint: str,
        pairs: List[QuoraQuestionsPair]
    ):

        for pair in pairs:

            # Reset cache before every experiment
            clear_result = await self.cache_client.clear_cache()

            if not clear_result["success"]:
                print(
                    f"Cache clear failed: {clear_result['error']}"
                )
                continue


            # Insert first question
            await self.worker.ask(
                link=endpoint,
                question=pair.question1
            )


            # Test second question
            result = await self.worker.ask(
                link=endpoint,
                question=pair.question2
            )


            # Update evaluation metrics
            self.metrics.update(
                cache_hit=result.get("cache_hit", False),
                is_duplicate=pair.is_duplicate
            )


        return self.metrics.results()