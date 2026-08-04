import os
import httpx

class QueryProcessor:
    """Redacts sensitive information using analyzer/anonymizer microservices."""
    def __init__(self, analyzer_url: str = None, anonymizer_url: str = None, timeout: float = 10):
        self.analyzer_url = analyzer_url or os.getenv("ANALYZER_URL", "http://localhost:5002/analyze")
        self.anonymizer_url = anonymizer_url or os.getenv("ANONYMIZER_URL", "http://localhost:5001/anonymize")
        self.timeout = timeout
        print(f"Analyzer URL: {self.analyzer_url}")
        print(f"Anonymizer URL: {self.anonymizer_url}")
    async def process(self, query : str) -> str:
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

            anonymize_payload = {
                "text": query,
                "anonymizers": {
                    "DEFAULT": {"type": "replace", "new_value": "<REDACTED>"}
                },
                "analyzer_results": analyzer_results,
            }

            try:
                anonymize_resp = await client.post(self.anonymizer_url, json=anonymize_payload)
                anonymize_resp.raise_for_status()
                return anonymize_resp.json()["text"]
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as e:
                raise RuntimeError(f"Anonymization failed: {e}") from e