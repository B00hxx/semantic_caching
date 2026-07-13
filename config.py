from ollama import Client

ollama_client = Client(host='http://localhost:11434')

MODELS = {
    "chat" : "qwen2.5:0.5b",
    "emb" : "qwen3-embedding:0.6b"
}
