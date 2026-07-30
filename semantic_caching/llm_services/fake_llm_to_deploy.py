from .llm_service import LLM

class FakeLLMToDeploy(LLM):
    async def generate(self, query : str)-> str:
        x =  "x"
        return x
