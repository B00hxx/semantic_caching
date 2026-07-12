import ollama
import redis


r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

if r.ping():
    print("Connected to Redis successfully!")


client = ollama.Client(host='http://localhost:11434')

response = client.chat(
    model='qwen2.5:0.5b',
    messages=[
        {'role': 'user', 'content': 'Why is the sky blue?'}
    ]
)

print(response['message']['content'])


