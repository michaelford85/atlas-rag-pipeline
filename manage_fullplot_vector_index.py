#!/usr/bin/env python3
"""
Idempotently create or update a MongoDB Atlas Vector Search index
for the `fullplot_embedding` field in the specified cluster.
Uses the 2025-03-12 Atlas API spec.
"""

import os
import json
import requests
from dotenv_vault import load_dotenv

# --- 1️⃣ Load environment variables ---
load_dotenv(".env.vault")

ATLAS_PUBLIC_KEY = os.getenv("ATLAS_PUBLIC_KEY")
ATLAS_PRIVATE_KEY = os.getenv("ATLAS_PRIVATE_KEY")
ATLAS_GROUP_ID = os.getenv("ATLAS_GROUP_ID")
ATLAS_CLUSTER = os.getenv("ATLAS_CLUSTER")  # You’ll still pass this in

DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")

VECTOR_INDEX_NAME = "fullplot_embedding_vector_index"
NUM_DIMENSIONS = 1024     # Adjust to match your embedding model
SIMILARITY = "cosine"     # cosine | euclidean | dotProduct

# --- 2️⃣ Validate required inputs ---
for key, val in {
    "ATLAS_PUBLIC_KEY": ATLAS_PUBLIC_KEY,
    "ATLAS_PRIVATE_KEY": ATLAS_PRIVATE_KEY,
    "ATLAS_GROUP_ID": ATLAS_GROUP_ID,
    "ATLAS_CLUSTER": ATLAS_CLUSTER,
}.items():
    if not val:
        raise ValueError(f"❌ Missing required environment variable: {key}")

# --- 3️⃣ Configure API base and headers ---
AUTH = (ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY)
HEADERS = {
    "Accept": "application/vnd.atlas.2025-03-12+json",
    "Content-Type": "application/json",
}

# Base Atlas API URLs
BASE_URL = f"https://cloud.mongodb.com/api/atlas/v2/groups/{ATLAS_GROUP_ID}"
CLUSTERS_URL = f"{BASE_URL}/clusters"
INDEX_URL = f"{BASE_URL}/clusters/{ATLAS_CLUSTER}/fts/indexes/{DB_NAME}/{COLL_NAME}"

# --- 4️⃣ Define desired index specification ---
DESIRED_INDEX = {
    "collectionName": COLL_NAME,
    "database": DB_NAME,
    "name": VECTOR_INDEX_NAME,
    "type": "vectorSearch",
    "fields": [
        {
            "type": "vector",
            "path": "fullplot_embedding",
            "numDimensions": NUM_DIMENSIONS,
            "similarity": SIMILARITY,
        }
    ],
}

# --- 5️⃣ Connectivity check ---
def verify_connectivity():
    print("🧠 Checking Atlas API connectivity ...")
    try:
        r = requests.get(CLUSTERS_URL + "?pretty=true", auth=AUTH, headers=HEADERS)
        if r.status_code == 200:
            clusters = [c["name"] for c in r.json().get("results", [])]
            print(f"✅ Atlas API reachable. Found clusters: {', '.join(clusters)}")
            if ATLAS_CLUSTER not in clusters:
                print(f"⚠️ Cluster '{ATLAS_CLUSTER}' not found — check ATLAS_CLUSTER value.")
        elif r.status_code == 401:
            print("❌ Unauthorized. Verify API key roles and project access.")
            exit(1)
        else:
            print(f"⚠️ Unexpected {r.status_code}: {r.text[:300]}")
            exit(1)
    except Exception as e:
        print(f"❌ Connection error: {e}")
        exit(1)

# --- 6️⃣ Ensure vector index exists or update if needed ---
def ensure_vector_index():
    print(f"\n🔍 Managing vector index '{VECTOR_INDEX_NAME}' on {DB_NAME}.{COLL_NAME} ...")
    try:
        # Fetch all indexes on this collection
        resp = requests.get(INDEX_URL, auth=AUTH, headers=HEADERS)
        resp.raise_for_status()
        indexes = resp.json()
        existing = next((i for i in indexes if i.get("name") == VECTOR_INDEX_NAME), None)

        if existing:
            # Compare field definitions
            if existing.get("fields") != DESIRED_INDEX["fields"]:
                print("♻️  Updating existing vector index definition ...")
                patch_url = f"{INDEX_URL}/{existing['_id']}"
                patch_resp = requests.patch(patch_url, auth=AUTH, headers=HEADERS, data=json.dumps(DESIRED_INDEX))
                patch_resp.raise_for_status()
                print("✅ Vector index updated successfully.")
            else:
                print("✅ Vector index already up-to-date.")
        else:
            print("🧩 Creating new vector index ...")
            create_resp = requests.post(INDEX_URL, auth=AUTH, headers=HEADERS, data=json.dumps(DESIRED_INDEX))
            create_resp.raise_for_status()
            print("✅ Vector index created successfully.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Atlas API error: {e}")
        if e.response is not None:
            print(f"Response: {e.response.text[:500]}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")

# --- 7️⃣ Run main workflow ---
if __name__ == "__main__":
    verify_connectivity()
    ensure_vector_index()