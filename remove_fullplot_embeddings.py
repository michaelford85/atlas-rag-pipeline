import os
from pymongo import MongoClient
from dotenv_vault import load_dotenv

# --- Load environment ---
dotenv_path_encrypted = ".env.vault"
print(f"🔍 Loading env from {dotenv_path_encrypted}...")
load_dotenv(dotenv_path=dotenv_path_encrypted, override=True)

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")

if not MONGODB_URI:
    raise ValueError("❌ Missing required environment variable: MONGODB_URI")

# --- Connect to MongoDB ---
print(f"📡 Connecting to MongoDB cluster: {MONGODB_URI.split('@')[-1].split('/')[0]} ...")
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLL_NAME]

# --- Count docs with the field ---
count_with_field = collection.count_documents({"fullplot_embedding": {"$exists": True}})
print(f"🧮 Found {count_with_field} documents containing 'fullplot_embedding'")

if count_with_field == 0:
    print("✅ No documents contain the field. Nothing to remove.")
else:
    # --- Perform the update ---
    result = collection.update_many({}, {"$unset": {"fullplot_embedding": ""}})
    print(f"✅ Successfully removed 'fullplot_embedding' from {result.modified_count} documents")

print("🏁 Done.")