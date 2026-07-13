from llm_service import LLM
from embedding import embedder
from cache_entry import CacheEntry
from cosine_sim import cosine_similarity
from config import MODELS


testing_llm = LLM(MODELS["chat"])
testing_emb = embedder(MODELS["emb"])

saved_answers = []


while True:
    state = False
    prompt = input("give me a question: ")
    embedded = testing_emb.get_embedding(prompt)
    for saved_entry in saved_answers:
        if cosine_similarity(embedded, saved_entry.embedding) > 0.9:
            state = True
            print("using a saved answer : {}".format(saved_answers[key][1]))
            break
    if state == False:
        answer_by_llm = testing_llm.get_answer(prompt)
        saved_answers.append(CacheEntry(prompt, embedded, answer_by_llm))
        print("using the LLM : {}".format(answer_by_llm))
        