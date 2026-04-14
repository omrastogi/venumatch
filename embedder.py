import os
import numpy as np
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY"),
)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns list of float vectors via LangChain."""
    return embeddings.embed_documents(texts)


def embed_query(vibe_signals: str) -> np.ndarray:
    """Embed a single vibe query string. Returns numpy array shape (1536,)."""
    return np.array(embeddings.embed_query(vibe_signals), dtype=np.float32)


def load_or_create_embeddings(texts: list[str], cache_path: str) -> np.ndarray:
    """Load embeddings from .npy cache if exists, else embed and save.
    Returns numpy array shape (N, 1536) for backward compatibility.
    Will be replaced by ChromaDB in Phase 1 Step 3.
    """
    if os.path.exists(cache_path):
        print(f"Loading embeddings from cache: {cache_path}")
        return np.load(cache_path)

    print(f"Cache not found. Embedding {len(texts)} texts via LangChain...")
    vectors = embed_texts(texts)
    embs = np.array(vectors, dtype=np.float32)
    np.save(cache_path, embs)
    print(f"Saved embeddings to {cache_path}")
    return embs
