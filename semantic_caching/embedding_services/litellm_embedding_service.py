from semantic_caching.embedding_services.embedding_service import Embedder
from openai import AsyncOpenAI

class LiteLLMEmbedder(Embedder):
    def __init__(self, api_key : str, model_name : str, link : str = "http://localhost:4000"):
        self.api_key = api_key
        self.model_name = model_name
        self.link = link
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=f"{link}/v1"
        )
    
    async def embed(self, query : str):
        response = await self.client.embeddings.create(
            model=self.model_name,
            input=query,
        )

        return response.data[0].embedding