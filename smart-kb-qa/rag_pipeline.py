# rag_pipeline.py
# Responsible for embedding docs, upserting to Pinecone, querying Pinecone, and calling OpenAI for answer synthesis.

import os
import openai
import pinecone
from typing import List, Dict, Any

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "smart-kb-index")

openai.api_key = OPENAI_KEY

# Initialize Pinecone
def init_pinecone():
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not set")
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
    if PINECONE_INDEX not in pinecone.list_indexes():
        # create index with 1536-dim (OpenAI embedding dim)
        pinecone.create_index(name=PINECONE_INDEX, dimension=1536)
    return pinecone.Index(PINECONE_INDEX)

pine_index = None
def get_index():
    global pine_index
    if pine_index is None:
        pine_index = init_pinecone()
    return pine_index

# Embedding wrapper
def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Use OpenAI embeddings API to convert texts -> vectors.
    """
    if not OPENAI_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    resp = openai.Embedding.create(model="text-embedding-3-small", input=texts)
    embeddings = [r["embedding"] for r in resp["data"]]
    return embeddings

# Upsert docs (used by upsert_docs.py)
def upsert_documents(docs: List[Dict[str, str]]):
    """
    docs: list of {id, title, text}
    """
    idx = get_index()
    texts = [d["text"] for d in docs]
    embeddings = embed_texts(texts)
    # prepare pinecone upsert items (id, vector, metadata)
    items = []
    for d, emb in zip(docs, embeddings):
        items.append((d["id"], emb, {"title": d.get("title", ""), "text": d["text"]}))
    idx.upsert(vectors=items)
    return {"upserted": len(items)}

# Query pipeline: find top-k docs and synthesize answer
def query_kg_and_answer(query: str, k: int = 4) -> Dict[str, Any]:
    """
    - Embed the query
    - Query Pinecone to fetch top-k similar docs
    - Call OpenAI chat completion with context to generate answer + citations
    Returns: { answer: str, sources: [ {id, title, snippet, score} ] }
    """
    idx = get_index()
    q_emb = embed_texts([query])[0]
    # fetch top k matches
    res = idx.query(vector=q_emb, top_k=k, include_metadata=True, include_values=False)
    matches = res.get("matches", [])
    sources = []
    context_texts = []
    for m in matches:
        meta = m.get("metadata", {})
        snippet = (meta.get("text") or "")[:800]  # short snippet (max 800 chars)
        sources.append({"id": m["id"], "title": meta.get("title", ""), "snippet": snippet, "score": m.get("score")})
        context_texts.append(f"TITLE: {meta.get('title','')}\nCONTENT: {snippet}\n---\n")
    # Build prompt for OpenAI
    system_prompt = (
        "You are an internal knowledge assistant. Use only the provided documents to answer the user's question. "
        "If the answer is not present, say you don't know and suggest where to ask internally."
    )
    user_prompt = f"User question:\n{query}\n\nUse the following documents (use citations by document id):\n\n{''.join(context_texts)}\n\nProvide a concise answer (3-6 sentences), then list the document ids used as citations at the end."
    # call chat completion
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=400,
        temperature=0.0
    )
    answer_text = completion["choices"][0]["message"]["content"].strip()
    return {"answer": answer_text, "sources": sources}
