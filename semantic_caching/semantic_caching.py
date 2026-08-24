import logging
from .llm_services.llm_service import LLM
from .embedding_services.embedding_service import Embedder
from .cache_entry.cache_entry_retrieval import CacheEntryForRetrieval
from .vector_store_services.vector_store_services import VectorStore
from .query import QueryProcessor
from .postgres_service.postgres_service import PostgresService, CacheEntryForPersistence
from .cache_invalidation.cache_invalidation_strategy import CacheInvalidationStrategy
from .cache_eviction.cache_eviction_strategy import CacheEvictionStrategy

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
class SemanticCaching:
    def __init__(self, 
                 llm_model: LLM, 
                 embedding_model: Embedder, 
                 vector_store: VectorStore, 
                 invalidation_strategy : CacheInvalidationStrategy | None = None,
                 eviction_strategy : CacheEvictionStrategy | None = None, 
                 query_processor : QueryProcessor = None, 
                 threshold: float = 0.5, 
                 namespace : str = "default", 
                 postgres : PostgresService | None = None):
       
        self.llm = llm_model
        self.embedding = embedding_model
        self.threshold = threshold
        self.vector_store = vector_store
        self.query_processor = query_processor
        self.postgres = postgres
        self.invalidation_strategy = invalidation_strategy
        self.eviction_strategy = eviction_strategy
        
        if not namespace:
            raise ValueError("namespace cannot be empty")
        self.namespace = namespace
    
    async def initialize(self, limit : int = 10):
        if not self.postgres:
            return 0
        top_entries = await self.postgres.get_top_entries(embedding_model = self.embedding.model_name, 
                                          embedding_dimension=int(self.embedding.embedding_dimension), 
                                          namespace=self.namespace, 
                                          limit=limit)
        top_entries_transformed = [CacheEntryForRetrieval(
                                                        question=entry.question,
                                                        embedding=entry.embedding,
                                                        answer=entry.answer,
                                                        namespace=entry.namespace,
                                                        id=entry.id,
                                                        created_at=entry.created_at,
                                                        hit_count=entry.hit_count,
                                                        last_hit_at=entry.last_hit_at,
                                                        last_accessed_at=entry.last_accessed_at) for entry in top_entries]
        for entry in top_entries_transformed:
            await self.vector_store.add_entry(entry)
        logger.info("Loaded %d cache entries from PostgreSQL", len(top_entries))
        return len(top_entries)
    
    async def invalidate_entries(self) -> int:
        if self.invalidation_strategy is None:
            return 0
        entries = await self.vector_store.get_all_entries()
        invalidated_count = 0
        for entry in entries:
            should_invalidate = (await self.invalidation_strategy.should_invalidate_entry(entry))
            if should_invalidate:
                await self.vector_store.delete_entry(entry.id)
                invalidated_count += 1
                logger.info(
                    "Invalidated cache entry %s",
                    entry.id
                )
        return invalidated_count
    
    async def evict_entries(self, max_size: int) -> int:
        if max_size < 0:
            raise ValueError("max_size cannot be negative")
        if self.eviction_strategy is None:
            return 0
        current_size = await self.vector_store.get_size()
        if current_size <= max_size:
            return 0
        number_to_evict = current_size - max_size
        entries = await self.vector_store.get_all_entries()
        entries_to_evict = (
            await self.eviction_strategy.select_entries_for_eviction(
                entries,
                number_to_evict
            )
        )
        evicted_count = 0
        for entry in entries_to_evict:
            deleted = await self.vector_store.delete_entry(entry.id)
            if deleted:
                evicted_count += 1
                logger.info(
                    "Evicted cache entry %s", entry.id
                )
        logger.info(
            "Cache eviction completed: %d entries evicted",evicted_count
        )
        return evicted_count
    
    
    async def get_answers(self, query:str)->dict:
        spans = []
        if self.query_processor is not None:
            logger.info("Query sent to Presidio Analyzer...")
            spans = await self.query_processor.process(query)
            logger.info("Presidio spans: %s", spans)
        has_sensitive_data = (self.query_processor is not None and self.query_processor.contains_sensitive_data(spans))
        if not has_sensitive_data:
            for span in spans:
                logger.info(
                        "Detected entity=%s score=%.3f text=%r",
                        span["entity_type"],
                        span["score"],
                        query[span["start"]:span["end"]],
                        )
            logger.info("No sensitive information discovered!")
            embedded = await self.embedding.embed(query)
            logger.info("Query embedded")
            response_from_vector_store = await self.vector_store.search(query_embedding=embedded, threshold=self.threshold, namespace=self.namespace)
            logger.info("Lookup finished")
            if response_from_vector_store == None:
                logger.info("No approprite match, generating answer")
                answer_by_llm = await self.llm.generate(query=query)
                logger.info("Answer generated by LLM")
                entry_retrieval = CacheEntryForRetrieval(question=query,
                                               embedding=embedded, 
                                               answer=answer_by_llm, 
                                               namespace=self.namespace,
                                               hit_count=1)
                logger.info("Entry being added to cache")
                await self.vector_store.add_entry(entry_retrieval)
                if self.postgres:
                    try: 
                        entry_persistent = CacheEntryForPersistence(
                            question=query,
                            embedding=embedded,
                            answer=answer_by_llm,
                            embedding_model=self.embedding.model_name,
                            embedding_dimension=int(self.embedding.embedding_dimension),
                            namespace=self.namespace,
                            id=entry_retrieval.id,
                            hit_count=entry_retrieval.hit_count,
                        )
                        await self.postgres.save_entry(entry_persistent)
                    except Exception:
                        logger.exception("Failed to persist cache entry to PostgreSQL")
                return {
                    "cache_hit" : False,
                    "cosine_distance" : None,
                    "answer" : answer_by_llm,
                    "time" : entry_retrieval.created_at            
                }
            else:
                logger.info("Good match was found, retrieving from Store")
                await self.vector_store.update_access_metadata(identifier=response_from_vector_store.identifier)
                if self.postgres:
                    try:
                        id = response_from_vector_store.identifier.split(":", 1)[-1]
                        await self.postgres.update_hit_count(id=id)
                    except Exception:
                        logger.exception("Failed to update cache hit metrics")
                
                return {
                    "cache_hit" : True,
                    "cosine_distance" : response_from_vector_store.score,
                    "answer" : response_from_vector_store.answer,
                    "time" : response_from_vector_store.created_at,
                    "id" : response_from_vector_store.identifier,
                }
        else:
            logger.info("PII discovered, send to LLM directly")
            answer_by_llm = await self.llm.generate(query=query)
            redacted_query = self.query_processor.redact(query = query, analyzer_results=spans)
            if self.postgres:
                try:
                    entry_persistent = CacheEntryForPersistence(
                                            question=redacted_query,
                                            embedding=[0],
                                            answer=answer_by_llm,
                                            embedding_model= "None",
                                            embedding_dimension = 0,
                                            namespace="None",
                                        )
                    await self.postgres.save_entry(entry_persistent)
                except Exception:
                        logger.info("error in saving redacted stuff to postgres")

            return {
                "cache_hit" : False,
                "cache_bypassed" : True,
                "answer" : answer_by_llm
            }