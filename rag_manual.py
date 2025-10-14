import os
import certifi
import voyageai
from pymongo import MongoClient
from dotenv_vault import load_dotenv

print("🔐 Loading environment variables ...")

# --- Load environment variables ---
vault_loaded = load_dotenv(dotenv_path=".env.vault", override=True)
if not vault_loaded:
    print("⚠️  No .env.vault loaded — falling back to .env")
    load_dotenv(dotenv_path=".env", override=True)

# --- Retrieve environment variables ---
MONGODB_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")
INDEX_NAME = os.getenv("FULLPLOT_INDEX_NAME", "fullplot_vector_index")
VECTOR_FIELD = os.getenv("VECTOR_FIELD", "fullplot_embedding")
MODEL_NAME = os.getenv("MODEL_NAME", "voyage-3-large")

# --- Sanity checks ---
missing_vars = [k for k, v in {
    "MONGODB_URI": MONGODB_URI,
    "VOYAGE_API_KEY": VOYAGE_API_KEY,
}.items() if not v]

if missing_vars:
    raise EnvironmentError(f"❌ Missing required environment variables: {missing_vars}")

print(f"✅ Loaded environment for DB '{DB_NAME}', collection '{COLL_NAME}', "
      f"index '{INDEX_NAME}', field '{VECTOR_FIELD}'")

# --- Connect to MongoDB Atlas ---
client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
coll = client[DB_NAME][COLL_NAME]

# --- Create VoyageAI embedding for the query ---
v = voyageai.Client(api_key=VOYAGE_API_KEY)
query_text = "What movies are about an animal trying to accomplish something great?"
embedding = v.embed(
    texts=[query_text],
    model=MODEL_NAME
).embeddings[0]

# --- Build MongoDB Vector Search pipeline ---
pipeline = [
    {
        "$vectorSearch": {
            "index": INDEX_NAME,           # must match Atlas index name
            "path": VECTOR_FIELD,          # must match field in documents
            "queryVector": embedding,      # VoyageAI embedding vector
            "numCandidates": 150,
            "limit": 3
        }
    },
    {"$project": {"title": 1, "score": {"$meta": "vectorSearchScore"}}}
]

# --- Execute and display results ---
print(f"\n🔎 Querying Atlas Vector Index '{INDEX_NAME}' on field '{VECTOR_FIELD}' ...\n")

results = list(coll.aggregate(pipeline))
if not results:
    print("⚠️  No results found — check your vector index or field mapping.")
else:
    print("🧠 Query results:")
    for doc in results:
        print(f"- {doc.get('title', 'Unknown')}  (score: {doc.get('score'):.4f})")