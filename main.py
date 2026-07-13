import ollama
import redis
import numpy as np
import pandas as pd

client = ollama.Client(host='http://localhost:11434')
saved_answers = dict()


def cosine_similarity(vec1, vec2):
    vec1, vec2 = np.squeeze(np.asarray(vec1)), np.squeeze(np.asarray(vec2))
    dot = np.dot(vec1, vec2)
    return dot / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def get_answer(prompt):
    for key in saved_answers.keys():
        if cosine_similarity(saved_answers[key][0], embedded_response["embeddings"]) > 0.9:
            print("we are using a saved response")
            print(saved_answers[key][1])
            return None
    print("we are calling the LLM")
    response = client.chat(
         model='qwen2.5:0.5b',
         messages=[
                    {'role': 'user', 'content': prompt}
         ])
    print(response['message']['content'])
    saved_answers[prompt] = [np.array(embedded_response["embeddings"]), response['message']['content']]
    return None


try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    if r.ping():
        print("Connected to Redis successfully!")
except redis.ConnectionError:
    print("Failed to connect to Redis.")

while 1:
    prompt = input("Enter your prompt: ")
    embedded_response = client.embed(
        model='qwen3-embedding:0.6b',
        input=prompt
    )
    print(type(embedded_response["embeddings"]))
    get_answer(prompt=prompt)