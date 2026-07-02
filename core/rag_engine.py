import os
import google.generativeai as genai
import chromadb

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma")

_client = None
_collection = None


def _get_client():
    global _client
    if _client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


def _get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name="compliance_docs",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _embed_texts(texts: list) -> list:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set.")
    genai.configure(api_key=api_key)
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=texts,
        task_type="RETRIEVAL_DOCUMENT",
    )
    return result["embedding"]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def index_document(doc_id: str, user_id: str, redacted_text: str):
    collection = _get_collection()
    try:
        existing = collection.get(
            where={"$and": [{"doc_id": doc_id}, {"user_id": user_id}]}
        )
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    chunks = chunk_text(redacted_text)
    if not chunks:
        return 0

    embeddings = _embed_texts(chunks)

    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "user_id": user_id, "chunk_index": i}
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)


def query_document(doc_id: str, user_id: str, question: str, top_k: int = 5) -> list:
    collection = _get_collection()
    q_embedding = _embed_texts([question])[0]

    results = collection.query(
        query_embeddings=[q_embedding],
        n_results=top_k,
        where={"$and": [{"doc_id": doc_id}, {"user_id": user_id}]},
    )

    if results and results["documents"]:
        return results["documents"][0]
    return []
