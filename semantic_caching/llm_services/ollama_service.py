import ollama
from .llm_service import LLM


class OllamaLLM(LLM):
    def __init__(self, client: ollama.AsyncClient | None = None, model_name: str = "qwen2.5:0.5b"):
        self.client = client or ollama.AsyncClient()
        self.model_name = model_name
        self.calls = 0

    async def generate(self, query: str) -> str:
        self.calls += 1
        response = await self.client.chat(
            model=self.model_name,
            messages=[
                {"role": "user", "content": query}
            ],
        )
        return response["message"]["content"]
