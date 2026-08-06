import asyncio
import httpx
import pandas as pd
from tqdm import tqdm
from benchmark.quora_questions.question_pair import QuoraQuestionsPair
from benchmark.worker import Worker

payload = {
    "state": "true"  
}

class ParallelBenchmarking:
    def __init__(self, num_workers: int = 5, cache_clear_duration: int = 100, base_url: str = "http://127.0.0.1:8000"):
        self.num_workers = num_workers
        self.cache_clear_duration = cache_clear_duration
        self.base_url = base_url
        self.workers = [Worker(worker_id=i) for i in range(num_workers)]

        # Metrics
        self.true_positives = 0
        self.false_positives = 0
        self.true_negatives = 0
        self.false_negatives = 0

        self._lock = asyncio.Lock()
    
    async def clear_cache(self, client: httpx.AsyncClient):
        """Clear the server cache"""
        try:
            await client.post(
                f"{self.base_url}/delete/cache", 
                json=payload
            )
        except Exception as e:
            print(f"Warning: Failed to clear cache: {e}")
    
    async def update_metrics(self, cache_hit: bool, is_duplicate: int):
        """Thread-safe metrics update"""
        async with self._lock:
            if cache_hit and is_duplicate == 1:
                self.true_positives += 1
            elif not cache_hit and is_duplicate == 1:
                self.false_negatives += 1
            elif cache_hit and is_duplicate == 0:
                self.false_positives += 1
            elif not cache_hit and is_duplicate == 0:
                self.true_negatives += 1
    
    async def process_pair(self, worker: Worker, client: httpx.AsyncClient, pair: QuoraQuestionsPair):
        """Process a single question pair"""
        # Send first question to populate cache
        _ = await worker._send_request(
            client=client,
            link=f"{self.base_url}/chat/fake_ask",
            question=pair.question1
        )
        
        # Send second question to check cache hit
        result = await worker._send_request(
            client=client,
            link=f"{self.base_url}/chat/fake_ask",
            question=pair.question2
        )
        
        await self.update_metrics(result.get("cache_hit", False), pair.is_duplicate)
        await self.clear_cache(client=client)
        return result
    
    async def run_sequential_benchmark(self, questions_df: pd.DataFrame, limit: int = None):
        """Run benchmark sequentially (single worker)"""
        async with httpx.AsyncClient() as client:
            worker = self.workers[0]
            
            # Limit rows if specified
            if limit:
                questions_df = questions_df.head(limit)
            
            length_df = len(questions_df)
            
            for i in tqdm(range(length_df), desc="Processing pairs"):
                pair = QuoraQuestionsPair(
                    question1=questions_df["question1"].iloc[i],
                    question2=questions_df["question2"].iloc[i],
                    is_duplicate=questions_df["is_duplicate"].iloc[i]
                )
                
                # Process the pair
                await self.process_pair(worker, client, pair)
                
                # Clear cache periodically
                if i % self.cache_clear_duration == 0 and i > 0:
                    await self.clear_cache(client)
            
            return self._calculate_metrics()
    
    async def run_parallel_benchmark(self, questions_df: pd.DataFrame, limit: int = None):
        """Run benchmark with multiple workers in parallel"""
        if limit:
            questions_df = questions_df.head(limit)
        
        # Create question pairs
        pairs = []
        for i in range(len(questions_df)):
            pair = QuoraQuestionsPair(
                question1=questions_df["question1"].iloc[i],
                question2=questions_df["question2"].iloc[i],
                is_duplicate=questions_df["is_duplicate"].iloc[i]
            )
            pairs.append(pair)
        
        # Split pairs among workers
        pairs_per_worker = len(pairs) // self.num_workers
        worker_pairs = []
        
        for i in range(self.num_workers):
            start_idx = i * pairs_per_worker
            if i == self.num_workers - 1:
                # Last worker gets remaining pairs
                end_idx = len(pairs)
            else:
                end_idx = (i + 1) * pairs_per_worker
            worker_pairs.append(pairs[start_idx:end_idx])
        
        # Create tasks for each worker
        async with httpx.AsyncClient() as cache_client:
            worker_tasks = []
            
            for worker_id, worker_pairs_list in enumerate(worker_pairs):
                worker = self.workers[worker_id]
                task = self._worker_loop(worker, worker_pairs_list, cache_client, worker_id)
                worker_tasks.append(task)
            
            # Run all workers concurrently
            print(f"Running benchmark with {self.num_workers} workers...")
            print(f"Total question pairs: {len(pairs)}")
            
            await asyncio.gather(*worker_tasks)
        
        return self._calculate_metrics()
    
    async def _worker_loop(self, worker: Worker, pairs: list, cache_client: httpx.AsyncClient, worker_id: int):
        """Worker loop that processes its assigned pairs"""
        async with httpx.AsyncClient() as client:
            for idx, pair in enumerate(pairs):
                await self.process_pair(worker, client, pair)
                
                # Clear cache periodically (only worker 0 handles this to avoid conflicts)
                if worker_id == 0 and idx % self.cache_clear_duration == 0 and idx > 0:
                    await self.clear_cache(cache_client)
                
                # Progress update
                if idx % 10 == 0 and idx > 0:
                    async with self._lock:
                        total_processed = (self.true_positives + self.false_positives + 
                                         self.true_negatives + self.false_negatives)
                        print(f"Worker {worker_id}: ~{total_processed} total processed")
    
    def _calculate_metrics(self):
        """Calculate benchmark metrics"""
        total = self.true_positives + self.false_positives + self.true_negatives + self.false_negatives
        
        accuracy = (self.true_positives + self.true_negatives) / total if total > 0 else 0
        precision = self.true_positives / (self.true_positives + self.false_positives) if (self.true_positives + self.false_positives) > 0 else 0
        recall = self.true_positives / (self.true_positives + self.false_negatives) if (self.true_positives + self.false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "total_pairs": total
        }


async def execute_sequential_worker():
    """Run sequential benchmark (single worker)"""
    quora_questions_df = pd.read_csv('benchmark/datasets/train.csv')
    
    benchmark = ParallelBenchmarking(num_workers=1)
    results = await benchmark.run_sequential_benchmark(quora_questions_df, limit=1000)
    
    return results


async def execute_parallel_workers():
    """Run parallel benchmark (multiple workers)"""
    quora_questions_df = pd.read_csv('benchmark/datasets/train.csv')
    
    # Use multiple workers for parallel processing
    benchmark = ParallelBenchmarking(num_workers=8, cache_clear_duration=50)
    results = await benchmark.run_parallel_benchmark(quora_questions_df, limit=10000)
    
    return results


if __name__ == "__main__":
    print("Testing with the Quora dataset...")
    
    # Choose which benchmark to run:
    # For sequential (original behavior):
    result = asyncio.run(execute_sequential_worker())
    
    # For parallel processing (faster):
    #result = asyncio.run(execute_parallel_workers())
    
    print("\n=== Results ===")
    for key, value in result.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")