from testing.fake_components.fake_llm import Fake_LLM

def test_hello():
    llm = Fake_LLM()
    assert llm.get_answer("hello!") == "what do you want?"