from ollama import Client
from redis import Redis


ollama_client = Client(host='http://localhost:11434')
redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)

MODELS = {
    "chat" : "qwen2.5:0.5b",
    "emb" : "qwen3-embedding:0.6b"
}

