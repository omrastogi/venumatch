import chromadb
from embedder import embed_texts, embed_query

COLLECTION_NAME = "venues"


def load_or_build_vectorstore(structs: list[dict], texts: list[str], persist_dir: str = "data/chroma_db"):
    """
    Load ChromaDB collection from disk if complete, else build and persist.
    Uses cosine similarity space. Returns ChromaDB collection.
    """
    client = chromadb.PersistentClient(path=persist_dir)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() == len(structs):
        print(f"Vectorstore loaded from {persist_dir} ({collection.count()} venues)")
        return collection

    # Partial or empty — rebuild cleanly
    print(f"Building vectorstore with {len(structs)} venues...")
    client.delete_collection(COLLECTION_NAME)
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    embeddings = embed_texts(texts)

    collection.add(
        ids=[str(v["id"]) for v in structs],
        documents=texts,
        metadatas=[{
            "id": v["id"],
            "name": v["name"],
            "neighborhood": v["neighborhood"],
            "capacity": v["capacity"],
            "avg_cost_pp": v["avg_cost_pp"],
            "specialty": v["specialty"],
            "original_idx": v["original_idx"],
        } for v in structs],
        embeddings=embeddings,
    )

    print(f"Vectorstore built and saved to {persist_dir}")
    return collection


def semantic_search(
    collection,
    query_text: str,
    passing_ids: list[int],
    k: int = 5,
) -> list[dict]:
    """
    Stage 2 retrieval: query ChromaDB for top-k venues from passing_ids only.
    Cosine space: distance = 1 - cosine_similarity, so similarity = 1 - distance.
    Returns list of venue dicts with similarity_score added, sorted descending.
    """
    q_emb = embed_query(query_text).tolist()
    n = min(k, len(passing_ids))

    results = collection.query(
        query_embeddings=[q_emb],
        n_results=n,
        where={"id": {"$in": passing_ids}},
    )

    output = []
    for i, meta in enumerate(results["metadatas"][0]):
        distance = results["distances"][0][i]
        similarity = round(1 - distance, 4)
        output.append({**meta, "similarity_score": similarity})

    return output
