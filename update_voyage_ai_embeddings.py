#!/usr/bin/env python3
import os
import time
import requests
from pymongo import MongoClient, UpdateOne, errors
from dotenv_vault import load_dotenv

# ============================================================
# 1. Load environment
# ============================================================
dotenv_path_encrypted = ".env.vault"
print(f"🔍 Loading env from {dotenv_path_encrypted}...")
load_dotenv(dotenv_path=dotenv_path_encrypted, override=True)

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
MODEL_NAME = os.getenv("MODEL_NAME", "voyage-3-large")

# Allow multiple embedding paths/names (comma-separated)
EMBEDDING_PATHS = [p.strip() for p in os.getenv("EMBEDDING_PATHS", "").split(",") if p.strip()]
EMBEDDING_NAMES = [n.strip() for n in os.getenv("EMBEDDING_NAMES", "").split(",") if n.strip()]

# Fallback for single-field legacy env vars
if not EMBEDDING_PATHS:
    path = os.getenv("EMBEDDING_PATH")
    if path:
        EMBEDDING_PATHS = [path]
if not EMBEDDING_NAMES:
    name = os.getenv("EMBEDDING_NAME")
    if name:
        EMBEDDING_NAMES = [name]

if len(EMBEDDING_PATHS) != len(EMBEDDING_NAMES):
    raise ValueError("❌ EMBEDDING_PATHS and EMBEDDING_NAMES must have the same number of entries.")

if not VOYAGE_API_KEY or not MONGODB_URI:
    raise ValueError("Missing required environment variables: VOYAGE_API_KEY or MONGODB_URI")

# ============================================================
# 2. MongoDB connection
# ============================================================
client = MongoClient(MONGODB_URI)
collection = client[DB_NAME][COLL_NAME]
print(f"✅ Connected to MongoDB collection: {DB_NAME}.{COLL_NAME}")

# ============================================================
# 3. VoyageAI helper
# ============================================================
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

# ============================================================
# 4. Main multi-field embedding loop
# ============================================================
for path, name in zip(EMBEDDING_PATHS, EMBEDDING_NAMES):
    print(f"\n🧠 Processing embeddings for: {path} → {name}")

    query = {path: {"$exists": True}, name: {"$exists": False}}
    cursor = collection.find(query, {"_id": 1, path: 1})
    total = collection.count_documents(query)
    print(f"📄 Found {total} documents missing embeddings for '{path}'")

    batch = []
    count = 0

    def process_batch(batch, count):
        if not batch:
            return count
        texts = [d[path] for d in batch]
        embeddings = get_embeddings(texts)

        ops = []
        for doc, emb in zip(batch, embeddings):
            ops.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            name: emb,
                            "embedding_model": MODEL_NAME,
                            "embedding_updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        }
                    }
                )
            )

        try:
            result = collection.bulk_write(ops, ordered=False)
            count += len(batch)
            print(f"💾 Updated {result.modified_count} docs for '{name}' ({count}/{total} total)")
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

    if batch:
        count = process_batch(batch, count)

    print(f"✅ Embedding update complete for '{name}'.")

print("🏁 All embeddings updated successfully.")