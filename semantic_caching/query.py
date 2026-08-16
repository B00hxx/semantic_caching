import os
import httpx
class QueryProcessor:
    """Figures out if there is any sensitive information using analyzer microservices."""
    def __init__(self, analyzer_url: str = None, timeout: float = 10):
        self.analyzer_url = analyzer_url or os.getenv("ANALYZER_URL", "http://localhost:5002/analyze")
        self.timeout = timeout
    
    async def process(self, query : str) -> list:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            analyze_payload = {"text": query, "language": "en"}
            try:
                analyze_resp = await client.post(self.analyzer_url, json=analyze_payload)
                analyze_resp.raise_for_status()
                analyzer_results = analyze_resp.json()
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Analyzer service error: {e.response.status_code}") from e
            except httpx.RequestError as e:
                raise RuntimeError(f"Analyzer connection failed: {e}") from e

            if not isinstance(analyzer_results, list):
                raise ValueError(f"Unexpected analyzer response format: {type(analyzer_results)}")

            return analyzer_results
    
    def redact(self, query: str, analyzer_results: list, replacement: str = "<REDACTED>") -> str:
        results = sorted(
            analyzer_results,
            key=lambda x: x["start"],
            reverse=True
        )

        redacted_query = query

        for result in results:
            start = result["start"]
            end = result["end"]

            redacted_query = (
                redacted_query[:start]
                + replacement
                + redacted_query[end:]
            )

        return redacted_query