from testing.fake_components.fake_llm import Fake_LLM
from testing.fake_components.fake_semantic_caching import SemanticCaching

def test_hello():
    llm = Fake_LLM()
    assert llm.get_answer("hello!") == "what do you want?"

def test_empty_cache_calls_llm():

    cache = SemanticCaching()

    result = cache.get_answers("hello!")

    assert result["cache_hit"] is False
    assert result["answer"] == "what do you want?"

