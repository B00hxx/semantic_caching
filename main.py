from llm_service import LLM
from embedding import embedder
from cosine_sim import cosine_similarity
from config import MODELS


testing_llm = LLM(MODELS["chat"])
testing_emb = embedder(MODELS["emb"])

saved_answers = dict()


while True:
    state = False
    prompt = input("give me a question: ")
    embedded = testing_emb.get_embedding(prompt)
    for key in saved_answers.keys():
        if cosine_similarity(embedded, saved_answers[key][0]) > 0.9:
            state = True
            print("using a saved answer : {}".format(saved_answers[key][1]))
            break
    if state == False:
        answer_by_llm = testing_llm.get_answer(prompt)
        saved_answers[prompt] = [embedded, answer_by_llm]
        print("using the LLM : {}".format(answer_by_llm))
        