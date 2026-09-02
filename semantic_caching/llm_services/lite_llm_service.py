from openai import AsyncOpenAI
from .llm_service import LLM


class LiteLLMService(LLM):
    def __init__(
        self,
        api_key: str,
        model_name: str,
        link: str = "http://localhost:4000",
        max_retries: int = 1,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.link = link

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=f"{link}/v1",
            timeout=None,
            max_retries=max_retries,
        )

    async def generate(self, query: str) -> str:

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": query,
                }
            ],
        )

        return response.choices[0].message.content