# upsert_docs.py
# One-off script to load sample_docs.json into Pinecone index.

import json
import os
from rag_pipeline import upsert_documents

DATA_FILE = "sample_docs.json"

def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)
    result = upsert_documents(docs)
    print("Upsert result:", result)

if __name__ == "__main__":
    main()
