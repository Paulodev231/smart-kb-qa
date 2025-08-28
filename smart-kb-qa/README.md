# Smart KB Q&A — Slack RAG Bot

**One-line:** A small FastAPI service + Pinecone-backed RAG index that answers Slack slash-command questions from company docs and shows source citations.


## Important: Secrets
- This project needs real API keys to run (OpenAI, Pinecone, Slack). Do **not** put real keys into files you upload.
- Fill in ` .env` from ` .env.example` on the machine that will run the service, keep `.env` private and never push it to GitHub.

---

## Files included (root)
- `main.py` — FastAPI app and Slack endpoint  
- `rag_pipeline.py` — embeddings, Pinecone upsert/query, OpenAI calls  
- `upsert_docs.py` — script to load `sample_docs.json` into Pinecone  
- `db.py` — simple SQLite logging & fetch functions  
- `requirements.txt` — Python deps  
- `Dockerfile`, `docker-compose.yml` — container run instructions  
- `sample_docs.json` — example docs to index  
- `.env.example` — keys template (replace with real keys locally)  
- `templates/admin.html` — simple admin/audit viewer  
- `.gitignore` — ignore secrets & temp files

---

## Optional: How to run.
(Only run if you or someone with the API keys will run it.)
1. Build and run with Docker:
