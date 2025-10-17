#!/usr/bin/env python3
import os
import sys
import certifi
import voyageai
import requests
from pymongo import MongoClient
from dotenv_vault import load_dotenv

print("🔐 Loading environment variables ...")

# ============================================================
# 1. Load environment variables
# ============================================================
dotenv_path_encrypted = ".env.vault"
print(f"🔍 Loading env from {dotenv_path_encrypted}...")
load_dotenv(dotenv_path=dotenv_path_encrypted, override=True)

# --- Core configuration ---
MONGODB_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
DB_NAME = os.getenv("DB_NAME")
COLL_NAME = os.getenv("COLL_NAME")
INDEX_NAME = os.getenv("INDEX_NAME", "usr_activity_vector_index")
MODEL_NAME = os.getenv("MODEL_NAME", "voyage-3-large")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")

# --- Multi-embedding arrays ---
EMBEDDING_NAMES = [n.strip() for n in os.getenv("EMBEDDING_NAMES", "").split(",") if n.strip()]
EMBEDDING_FIELDS = [f.strip() for f in os.getenv("EMBEDDING_FIELDS", "").split(",") if f.strip()]

# Default projection fields if EMBEDDING_FIELDS not provided
if not EMBEDDING_FIELDS:
    EMBEDDING_FIELDS = ["usr", "lib", "data", "timestamp"]

# --- Validation ---
missing_vars = [k for k, v in {
    "MONGODB_URI": MONGODB_URI,
    "VOYAGE_API_KEY": VOYAGE_API_KEY,
}.items() if not v]
if missing_vars:
    raise EnvironmentError(f"❌ Missing required environment variables: {missing_vars}")

print(f"✅ Loaded environment for DB '{DB_NAME}', collection '{COLL_NAME}'")
print(f"   → Using index '{INDEX_NAME}' with {len(EMBEDDING_NAMES)} embedding fields: {', '.join(EMBEDDING_NAMES)}")
print(f"   → Returning projection fields: {', '.join(EMBEDDING_FIELDS)}")

# ============================================================
# 2. MongoDB connection
# ============================================================
client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
coll = client[DB_NAME][COLL_NAME]

# ============================================================
# 3. VoyageAI client setup
# ============================================================
v = voyageai.Client(api_key=VOYAGE_API_KEY)

# ============================================================
# 4. Retrieve relevant documents
# ============================================================
def retrieve_relevant_docs(query_text, limit=3, num_candidates=150):
    print(f"\n🔎 Generating query embedding for: {query_text}")
    query_embedding = v.embed(texts=[query_text], model=MODEL_NAME).embeddings[0]

    all_results = []

    for field in EMBEDDING_NAMES:
        print(f"📚 Searching index '{INDEX_NAME}' on embedding field '{field}' ...")
        pipeline = [
            {
                "$vectorSearch": {
                    "index": INDEX_NAME,
                    "path": field,
                    "queryVector": query_embedding,
                    "numCandidates": num_candidates,
                    "limit": limit
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "score": {"$meta": "vectorSearchScore"},
                    **{f: 1 for f in EMBEDDING_FIELDS}
                }
            }
        ]

        try:
            results = list(coll.aggregate(pipeline))
            for r in results:
                r["_search_field"] = field
            all_results.extend(results)
        except Exception as e:
            print(f"⚠️  Vector search failed for field '{field}': {e}")

    if not all_results:
        print("⚠️  No results found across any embedding fields.")
        return []

    # Sort and deduplicate by score
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    seen_ids = set()
    unique_results = []
    for r in all_results:
        if r["_id"] not in seen_ids:
            unique_results.append(r)
            seen_ids.add(r["_id"])
        if len(unique_results) >= limit:
            break

    print("\n🧠 Top Retrieved Documents:")
    for r in unique_results:
        label = r.get("usr") or r.get("lib") or r.get("data") or "Unknown"
        print(f"- {label} (score: {r.get('score'):.4f}, from: {r['_search_field']})")

    return unique_results

# ============================================================
# 5. Generate contextual answer with Ollama
# ============================================================
def generate_answer(query_text, docs):
    if not docs:
        return "No relevant documents found to generate an answer."

    # Flatten context from multiple fields
    context_chunks = []
    for d in docs:
        for f in EMBEDDING_FIELDS:
            if f in d:
                val = d[f]
                if isinstance(val, dict):
                    val = " ".join(f"{k}: {v}" for k, v in val.items())
                elif isinstance(val, list):
                    val = " ".join(map(str, val))
                context_chunks.append(f"{f}: {val}")

    context = "\n".join(context_chunks[:1500])  # limit context size
    prompt = f"""
You are a helpful assistant that answers questions based on the provided document context.

Context:
{context}

Question: {query_text}

Provide a concise, factual answer (3–6 sentences).
"""

    print("\n🧩 Sending context to local LLM via Ollama ...")
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=600
        )
        response.raise_for_status()
        answer = response.json().get("response", "").strip()
        print("\n💬 Generated Answer:\n")
        print(answer)
        return answer
    except Exception as e:
        print(f"❌ Ollama generation failed: {e}")
        return "Error during generation."

# ============================================================
# 6. Main entry point
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "What kind of activity was recorded most recently?"

    docs = retrieve_relevant_docs(user_query)
    generate_answer(user_query, docs)