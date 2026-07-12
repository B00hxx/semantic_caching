# pip install langchain-huggingface
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


doc_vectors = embeddings.embed_documents(["First chunk of text", "Second chunk"])

print(doc_vectors)