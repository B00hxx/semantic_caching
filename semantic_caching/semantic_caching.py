import httpx
import asyncio
import logging
from .llm_services.llm_service import LLM
from .embedding_services.embedding_service import Embedder
from .cache_entry import CacheEntry
from .vector_store_services.vector_store_services import VectorStore
from .vector_store_services.vector_search_result import VectorSearchResult
from .query import QueryProcessor
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class SemanticCaching:
    def __init__(self, llm_model: LLM, embedding_model: Embedder, vector_store: VectorStore, query_processor : QueryProcessor = None, threshold: float = 0.5,):
        self.llm = llm_model
        self.embedding = embedding_model
        self.threshold = threshold
        self.vector_store = vector_store
        self.query_processor = query_processor

    async def get_answers(self, query:str)->dict:
        # Queries carrying sensitive entities are still redacted before they reach the
        # provider, but they are never matched against nor written to the cache: every
        # entity collapses to the same placeholder, so two different secrets produce
        # identical text and one caller would be served the other caller's answer.
        cacheable = True
        if self.query_processor is not None:
            redaction = await self.query_processor.process(query)
            query = redaction.text
            cacheable = not redaction.has_pii
            if not cacheable:
                logger.info("Sensitive entities detected; bypassing cache for this query")

        if cacheable:
            embedded = await self.embedding.embed(query)
            response_from_vector_store = await self.vector_store.search(query_embedding=embedded, threshold=self.threshold)
            if response_from_vector_store is not None:
                return {
                    "cache_hit" : True,
                    "cache_bypassed" : False,
                    "cosine_distance" : response_from_vector_store.score,
                    "answer" : response_from_vector_store.answer,
                    "time" : response_from_vector_store.time,
                    "id" : response_from_vector_store.identifier,
                    "ttl" : response_from_vector_store.ttl
                }

        answer_by_llm = await self.llm.generate(query=query)
        entry = CacheEntry(query, embedded if cacheable else None, answer_by_llm)
        if cacheable:
            await self.vector_store.add_entry(entry)
        return {
            "cache_hit" : False,
            "cache_bypassed" : not cacheable,
            "cosine_distance" : None,
            "answer" : answer_by_llm,
            "time" : entry.created_at,
            "id" : None,
            "ttl" : None
        }