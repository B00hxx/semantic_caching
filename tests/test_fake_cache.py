import sys
from pathlib import Path
from fake_embedding import FakeEmbedder
from fake_llm import Fake_LLM

sys.path.append(str(Path(__file__).resolve().parent.parent))

from semantic_caching import SemanticCaching


fake_testing = SemanticCaching()