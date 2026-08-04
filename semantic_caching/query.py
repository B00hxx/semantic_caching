import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RedactionResult:
    """Outcome of running a query through the analyzer/anonymizer services."""

    text: str
    entities: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_pii(self) -> bool:
        return bool(self.entities)


class QueryProcessor:
    """Redacts sensitive information using analyzer/anonymizer microservices."""
    def __init__(self, analyzer_url: str = None, anonymizer_url: str = None, timeout: float = 10):
        self.analyzer_url = analyzer_url or os.getenv("ANALYZER_URL", "http://localhost:5002/analyze")
        self.anonymizer_url = anonymizer_url or os.getenv("ANONYMIZER_URL", "http://localhost:5001/anonymize")
        self.timeout = timeout
        logger.info("Analyzer URL: %s", self.analyzer_url)
        logger.info("Anonymizer URL: %s", self.anonymizer_url)

    async def process(self, query : str) -> RedactionResult:
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

            # Nothing sensitive found: skip the anonymizer round-trip entirely.
            if not analyzer_results:
                return RedactionResult(text=query, entities=[])

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
                return RedactionResult(
                    text=anonymize_resp.json()["text"],
                    entities=analyzer_results,
                )
            except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as e:
                raise RuntimeError(f"Anonymization failed: {e}") from e