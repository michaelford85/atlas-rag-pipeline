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

# Comma-separated lists (same format as in Colab)
EMBEDDING_PATHS = [p.strip() for p in os.getenv("EMBEDDING_PATHS", "").split(",") if p.strip()]
EMBEDDING_NAMES = [n.strip() for n in os.getenv("EMBEDDING_NAMES", "").split(",") if n.strip()]

if not MONGODB_URI:
    raise ValueError("❌ Missing required environment variable: MONGODB_URI")

if len(EMBEDDING_PATHS) != len(EMBEDDING_NAMES):
    raise ValueError("❌ EMBEDDING_PATHS and EMBEDDING_NAMES must have the same number of entries.")

if not EMBEDDING_NAMES:
    raise ValueError("❌ No EMBEDDING_NAMES defined. Provide via EMBEDDING_NAMES or .env.vault")

# ============================================================
#  Connect to MongoDB
# ============================================================
cluster_host = MONGODB_URI.split('@')[-1].split('/')[0] if '@' in MONGODB_URI else "localhost"
print(f"📡 Connecting to MongoDB cluster: {cluster_host} ...")

client = MongoClient(MONGODB_URI)
collection = client[DB_NAME][COLL_NAME]

# ============================================================
#  Remove all embedding fields
# ============================================================

total_removed = 0

for name in EMBEDDING_NAMES:
    print(f"\n🧠 Checking for documents with field '{name}' ...")
    count_with_field = collection.count_documents({name: {"$exists": True}})
    print(f"🧮 Found {count_with_field} documents containing '{name}'")

    if count_with_field == 0:
        print(f"✅ No documents contain '{name}'. Skipping.")
        continue

    # Unset the embedding field
    print(f"🧹 Removing '{name}' from all documents ...")
    result = collection.update_many({}, {"$unset": {name: ""}})
    total_removed += result.modified_count
    print(f"✅ Successfully removed '{name}' from {result.modified_count} documents")

print(f"\n🏁 Finished cleaning embeddings. Total fields removed: {len(EMBEDDING_NAMES)}")
print(f"🧾 Total documents modified: {total_removed}")