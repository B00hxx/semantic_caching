import pytest
from testing.fake_components.fake_llm import Fake_LLM

@pytest.fixture
def create_llm():
    return Fake_LLM()

@pytest.mark.parametrize("query, expected", [
    ("hello!", "what do you want?"),
    ("hi!", "here we go"),
    ("baha", "he's the man"),
    ("something random as hell", "fake anwswer")
])

def test_responses(create_llm, query, expected):
    assert create_llm.get_answer(query) == expected


def testing_calls():
    fake_llm_instance = Fake_LLM()
    for i in range(10):
        test = fake_llm_instance.get_answer("hello!")
    assert fake_llm_instance.calls == 10
