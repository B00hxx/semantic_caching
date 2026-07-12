import ollama


client = ollama.Client(host='http://localhost:11434')

response = client.chat(
    model='qwen2.5:0.5b',
    messages=[
        {'role': 'user', 'content': 'Why is the sky blue?'}
    ]
)

print(response['message']['content'])
