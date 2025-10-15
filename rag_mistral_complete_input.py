import os
import sys
import certifi
import voyageai
import requests
from pymongo import MongoClient
from dotenv_vault import load_dotenv

print("🔐 Loading environment variables ...")

# --- Load environment variables ---
dotenv_path_encrypted = ".env.vault"
dotenv_path_local = ".env.local"
print(f"🔍 Loading env from {dotenv_path_encrypted} and {dotenv_path_local}...")
load_dotenv(dotenv_path=dotenv_path_encrypted, override=True)
load_dotenv(dotenv_path=dotenv_path_local, override=True)

# --- Retrieve environment variables ---
MONGODB_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")
INDEX_NAME = os.getenv("FULLPLOT_INDEX_NAME", "fullplot_vector_index")
VECTOR_FIELD = os.getenv("VECTOR_FIELD", "fullplot_embedding")
MODEL_NAME = os.getenv("MODEL_NAME", "voyage-3-large")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")  # local Ollama model

# --- Sanity checks ---
missing_vars = [k for k, v in {
    "MONGODB_URI": MONGODB_URI,
    "VOYAGE_API_KEY": VOYAGE_API_KEY,
}.items() if not v]

if missing_vars:
    raise EnvironmentError(f"❌ Missing required environment variables: {missing_vars}")

print(f"✅ Loaded environment for DB '{DB_NAME}', collection '{COLL_NAME}', "
      f"index '{INDEX_NAME}', field '{VECTOR_FIELD}', generator '{LLM_MODEL}'")

# --- Connect to MongoDB Atlas ---
client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
coll = client[DB_NAME][COLL_NAME]

# --- VoyageAI setup ---
v = voyageai.Client(api_key=VOYAGE_API_KEY)

# --- RAG Query ---
def retrieve_relevant_docs(query_text, limit=3):
    print(f"\n🔎 Generating embeddings for query: {query_text}")
    embedding = v.embed(texts=[query_text], model=MODEL_NAME).embeddings[0]

    pipeline = [
        {
            "$vectorSearch": {
                "index": INDEX_NAME,
                "path": VECTOR_FIELD,
                "queryVector": embedding,
                "numCandidates": 150,
                "limit": limit
            }
        },
        {"$project": {"title": 1, "fullplot": 1, "score": {"$meta": "vectorSearchScore"}}}
    ]

    results = list(coll.aggregate(pipeline))
    if not results:
        print("⚠️  No results found — check vector index or field mapping.")
        return []

    print("\n🧠 Retrieved documents:")
    for r in results:
        print(f"- {r.get('title', 'Unknown')} (score: {r.get('score'):.4f})")

    return results


def generate_answer(query_text, docs):
    if not docs:
        return "No relevant documents found to generate an answer."

    context = "\n\n".join([f"{d.get('title', 'Unknown')}: {d.get('fullplot', '')}" for d in docs])
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
            timeout=300  # longer for slow model warmup
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


# --- Main workflow ---
if __name__ == "__main__":
    # 🧠 Take sentence from command line if provided
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "What movies are about an animal trying to accomplish something great?"

    docs = retrieve_relevant_docs(user_query)
    generate_answer(user_query, docs)