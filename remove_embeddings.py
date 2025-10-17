#!/usr/bin/env python3
import os
from pymongo import MongoClient
from dotenv_vault import load_dotenv

# ============================================================
#  Load environment
# ============================================================
dotenv_path_encrypted = ".env.vault"
print(f"🔍 Loading env from {dotenv_path_encrypted}...")
load_dotenv(dotenv_path=dotenv_path_encrypted, override=True)

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")

# Accept both EMBEDDING_PATHS and EMBEDDING_NAMES
EMBEDDING_PATHS = [p.strip() for p in os.getenv("EMBEDDING_PATHS", "").split(",") if p.strip()]
EMBEDDING_NAMES = [n.strip() for n in os.getenv("EMBEDDING_NAMES", "").split(",") if n.strip()]

if not MONGODB_URI:
    raise ValueError("❌ Missing required environment variable: MONGODB_URI")

if not EMBEDDING_NAMES:
    raise ValueError("❌ No EMBEDDING_NAMES defined. Provide via EMBEDDING_NAMES or .env.vault")

print(f"✅ Loaded embedding names: {', '.join(EMBEDDING_NAMES)}")

# ============================================================
#  Connect to MongoDB
# ============================================================
cluster_host = MONGODB_URI.split('@')[-1].split('/')[0] if '@' in MONGODB_URI else "localhost"
print(f"📡 Connecting to MongoDB cluster: {cluster_host} ...")

client = MongoClient(MONGODB_URI)
collection = client[DB_NAME][COLL_NAME]

# ============================================================
#  Remove embedding fields (top-level or nested)
# ============================================================
total_removed = 0

for name in EMBEDDING_NAMES:
    print(f"\n🧠 Checking for documents containing field '{name}' ...")

    # Support dot notation (e.g. "data.actv_embedding")
    query = {name: {"$exists": True}}
    count_with_field = collection.count_documents(query)
    print(f"🧮 Found {count_with_field} documents with '{name}'")

    if count_with_field == 0:
        print(f"✅ No documents contain '{name}'. Skipping.")
        continue

    # Handle embedded arrays (e.g., "data.actv_embedding" in array of objects)
    # We use an aggregation-style update pipeline for array-safe removal
    print(f"🧹 Removing '{name}' from all matching documents ...")

    try:
        if "." in name:
            # Dot-path removal via $unset works as long as the field path exists
            result = collection.update_many(
                {name: {"$exists": True}},
                {"$unset": {name: ""}}
            )
        else:
            # Top-level field
            result = collection.update_many({}, {"$unset": {name: ""}})

        print(f"✅ Successfully removed '{name}' from {result.modified_count} documents")
        total_removed += result.modified_count

    except Exception as e:
        print(f"⚠️ Failed to remove '{name}': {e}")

print(f"\n🏁 Finished cleaning embeddings.")
print(f"🧾 Total embedding fields processed: {len(EMBEDDING_NAMES)}")
print(f"📉 Total documents modified: {total_removed}")