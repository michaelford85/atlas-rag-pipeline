import os
import time
import requests
from pymongo import MongoClient, UpdateOne, errors
from dotenv_vault import load_dotenv

# ================================
# 1. Load environment
# ================================
dotenv_path = ".env.vault"
print(f"🔍 Loading env from {dotenv_path} ...")
load_dotenv(dotenv_path=dotenv_path, override=True)

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
MODEL_NAME = os.getenv("MODEL_NAME", "voyage-3-large")

if not VOYAGE_API_KEY or not MONGODB_URI:
    raise ValueError("Missing required environment variables: VOYAGE_API_KEY or MONGODB_URI")

print("✅ Environment variables successfully loaded from .env.vault!")
print(f"VOYAGE_API_KEY starts with: {VOYAGE_API_KEY[:6]}")
print(f"MONGODB_URI starts with: {MONGODB_URI[:20]}")
print(f"The embedding model is  with: {MODEL_NAME}")

# ================================
# 2. MongoDB connection
# ================================
client = MongoClient(MONGODB_URI)
collection = client[DB_NAME][COLL_NAME]
print(f"✅ Connected to MongoDB collection: {DB_NAME}.{COLL_NAME}")

# ================================
# 3. Find docs missing embeddings
# ================================
cursor = collection.find(
    {"fullplot": {"$exists": True}, "fullplot_embedding": {"$exists": False}},
    {"_id": 1, "fullplot": 1}
)
total = collection.count_documents({"fullplot": {"$exists": True}, "fullplot_embedding": {"$exists": False}})
print(f"📄 Found {total} documents missing embeddings")

# ================================
# 4. VoyageAI helper
# ================================
def get_embeddings(texts, retries=3, delay=2):
    """Call VoyageAI API with retry logic."""
    url = "https://api.voyageai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {VOYAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "input": texts
    }

    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
        except Exception as e:
            print(f"⚠️ VoyageAI request failed (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(delay)
    raise RuntimeError("❌ Failed to fetch embeddings after multiple retries")

# ================================
# 5. Batch processing
# ================================
batch = []
count = 0

def process_batch(batch, count):
    """Send batch to VoyageAI and update MongoDB."""
    if not batch:
        return count
    texts = [d["fullplot"] for d in batch]
    embeddings = get_embeddings(texts)

    ops = []
    for doc, emb in zip(batch, embeddings):
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "fullplot_embedding": emb,
                        "embedding_model": MODEL_NAME,
                        "embedding_updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                }
            )
        )

    try:
        result = collection.bulk_write(ops, ordered=False)
        count += len(batch)
        print(f"💾 Updated {result.modified_count} docs ({count}/{total} total)")
    except errors.BulkWriteError as bwe:
        print("⚠️ Bulk write error:", bwe.details)
    except Exception as e:
        print("⚠️ Unexpected error during bulk write:", e)

    return count

for doc in cursor:
    batch.append(doc)
    if len(batch) >= BATCH_SIZE:
        count = process_batch(batch, count)
        batch = []

# Handle remainder
if batch:
    count = process_batch(batch, count)

print("✅ Embedding update complete.")