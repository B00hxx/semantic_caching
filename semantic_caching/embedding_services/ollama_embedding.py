import numpy as np
import ollama
from .embedding_service import Embedder


class OllamaEmbeddingModel(Embedder):
    def __init__(
        self,
        client: ollama.AsyncClient | None = None,
        embedding_model: str = "qwen3-embedding:0.6b",
        embedding_dimension: int = 1024,
    ):
        super().__init__(model_name=embedding_model, embedding_dimension=embedding_dimension)
        self.client = client or ollama.AsyncClient()
        self.embedding_model = embedding_model

    async def embed(self, query: str) -> np.ndarray:
        embedded_dictionary = await self.client.embed(
            model=self.embedding_model,
            input=query,
        )
        embeddings = embedded_dictionary.get("embeddings") or embedded_dictionary.get("embedding")
        embedded_query = np.squeeze(np.asarray(embeddings, dtype=np.float32))
        return embedded_query
