#!/usr/bin/env python3
"""
Update MongoDB documents with VoyageAI embeddings for multiple fields.
Supports both top-level and nested array-based fields (e.g., data.actv).
No document structure changes — only new embedding fields are added.
"""

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
DB_NAME = os.getenv("DB_NAME", "threatmanager")
COLL_NAME = os.getenv("COLL_NAME", "user_activity")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
MODEL_NAME = os.getenv("MODEL_NAME", "voyage-3-large")

# Comma-separated lists for multiple embeddings
EMBEDDING_PATHS = [p.strip() for p in os.getenv("EMBEDDING_PATHS", "").split(",") if p.strip()]
EMBEDDING_NAMES = [n.strip() for n in os.getenv("EMBEDDING_NAMES", "").split(",") if n.strip()]

# Validate configuration
if not VOYAGE_API_KEY or not MONGODB_URI:
    raise ValueError("❌ Missing required environment variables: VOYAGE_API_KEY or MONGODB_URI")
if len(EMBEDDING_PATHS) != len(EMBEDDING_NAMES):
    raise ValueError("❌ EMBEDDING_PATHS and EMBEDDING_NAMES must have the same number of entries.")

# ============================================================
# 2. Connect to MongoDB
# ============================================================
client = MongoClient(MONGODB_URI)
collection = client[DB_NAME][COLL_NAME]
print(f"✅ Connected to MongoDB collection: {DB_NAME}.{COLL_NAME}")

# ============================================================
# 3. Helper: extract nested or array-based value
# ============================================================
def extract_value(doc, path):
    """Safely extract a nested or array-based value."""
    parts = path.split(".")
    value = doc
    for p in parts:
        if isinstance(value, list):
            if not value:
                return ""
            value = value[0]  # Take first element of array
        if not isinstance(value, dict) or p not in value:
            return ""
        value = value[p]
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    return str(value) if value else ""

# ============================================================
# 4. VoyageAI helper
# ============================================================
def get_embeddings(texts, retries=3, delay=2):
    """Call VoyageAI API with retry logic."""
    url = "https://api.voyageai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {VOYAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"model": MODEL_NAME, "input": texts}

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
# 5. Main multi-field embedding loop
# ============================================================
for path, name in zip(EMBEDDING_PATHS, EMBEDDING_NAMES):
    print(f"\n🧠 Processing embeddings for: {path} → {name}")

    # Build query: use $elemMatch for nested arrays like data.actv
    if "." in path:
        subfield = path.split(".", 1)[1]
        query = {"data": {"$elemMatch": {subfield: {"$exists": True}}}, name: {"$exists": False}}
    else:
        query = {path: {"$exists": True}, name: {"$exists": False}}

    total = collection.count_documents(query)
    print(f"📄 Found {total} documents missing embeddings for '{path}'")

    cursor = collection.find(query, {"_id": 1, path: 1, "data": 1})
    batch, count = [], 0

    def process_batch(batch, count):
        if not batch:
            return count

        texts = [extract_value(d, path) for d in batch]
        embeddings = get_embeddings(texts)

        ops = []
        for doc, emb in zip(batch, embeddings):
            ops.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {"$set": {
                        name: emb,
                        "embedding_model": MODEL_NAME,
                        "embedding_updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }}
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

print("\n🏁 All embeddings updated successfully.")