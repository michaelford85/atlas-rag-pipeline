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

# Core config
MONGODB_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")
INDEX_NAME = os.getenv("INDEX_NAME", "fullplot_vector_index")
MODEL_NAME = os.getenv("MODEL_NAME", "voyage-3-large")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")

# Multi-embedding arrays
EMBEDDING_PATHS = [p.strip() for p in os.getenv("EMBEDDING_PATHS", "").split(",") if p.strip()]
EMBEDDING_NAMES = [n.strip() for n in os.getenv("EMBEDDING_NAMES", "").split(",") if n.strip()]

# # Fallback for single-field legacy vars
# if not EMBEDDING_NAMES:
#     EMBEDDING_NAMES = [os.getenv("VECTOR_FIELD", "fullplot_embedding")]

# ============================================================
# 2. Sanity checks
# ============================================================
missing_vars = [k for k, v in {
    "MONGODB_URI": MONGODB_URI,
    "VOYAGE_API_KEY": VOYAGE_API_KEY,
}.items() if not v]

if missing_vars:
    raise EnvironmentError(f"❌ Missing required environment variables: {missing_vars}")

print(f"✅ Loaded environment for DB '{DB_NAME}', collection '{COLL_NAME}'")
print(f"   → Using index '{INDEX_NAME}' across {len(EMBEDDING_NAMES)} embedding field(s): {', '.join(EMBEDDING_NAMES)}")

# ============================================================
# 3. MongoDB connection
# ============================================================
client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
coll = client[DB_NAME][COLL_NAME]

# ============================================================
# 4. VoyageAI setup
# ============================================================
v = voyageai.Client(api_key=VOYAGE_API_KEY)

# ============================================================
# 5. Retrieve relevant documents
# ============================================================
def retrieve_relevant_docs(query_text, limit=3):
    print(f"\n🔎 Generating query embedding for: {query_text}")
    query_embedding = v.embed(texts=[query_text], model=MODEL_NAME).embeddings[0]

    all_results = []

    for field in EMBEDDING_NAMES:
        print(f"📚 Searching index '{INDEX_NAME}' on field '{field}' ...")
        pipeline = [
            {
                "$vectorSearch": {
                    "index": INDEX_NAME,
                    "path": field,
                    "queryVector": query_embedding,
                    "numCandidates": 150,
                    "limit": limit
                }
            },
            {"$project": {"title": 1, "fullplot": 1, "score": {"$meta": "vectorSearchScore"}}}
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

    # Sort and deduplicate results by score
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
        print(f"- {r.get('title', 'Unknown')} (score: {r.get('score'):.4f}, from: {r['_search_field']})")

    return unique_results

# ============================================================
# 6. Generate answer using local Ollama model
# ============================================================
def generate_answer(query_text, docs):
    if not docs:
        return "No relevant documents found to generate an answer."

    context = "\n\n".join([
        f"{d.get('title', 'Unknown')}:\n{d.get('fullplot', '')}" for d in docs
    ])
    prompt = f"""
You are a helpful assistant that answers questions based on movie plot information.

Context:
{context}

Question: {query_text}

Provide a concise and accurate answer (3–6 sentences).
"""

    print("\n🧩 Sending context to local Mistral model via Ollama ...")
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("response", "").strip()
        print("\n💬 Generated Answer:\n")
        print(answer)
        return answer
    except Exception as e:
        print(f"❌ Ollama generation failed: {e}")
        return "Error during generation."

# ============================================================
# 7. Main entry point
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "What movies are about an animal trying to accomplish something great?"

    docs = retrieve_relevant_docs(user_query)
    generate_answer(user_query, docs)