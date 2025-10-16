#!/usr/bin/env python3
import os
import sys
import json
import requests
from requests.auth import HTTPDigestAuth
from dotenv_vault import load_dotenv

# ============================================================
#  Load environment variables
# ============================================================
dotenv_path_encrypted = ".env.vault"
print(f"🔍 Loading env from {dotenv_path_encrypted}...")
load_dotenv(dotenv_path=dotenv_path_encrypted, override=True)

# ============================================================
#  Read required environment variables
# ============================================================

PUBLIC_KEY = os.getenv("ATLAS_PUBLIC_KEY")
PRIVATE_KEY = os.getenv("ATLAS_PRIVATE_KEY")
PROJECT_ID = os.getenv("ATLAS_GROUP_ID")
CLUSTER_NAME = os.getenv("ATLAS_CLUSTER")
INDEX_NAME = os.getenv("INDEX_NAME")
DB_NAME = os.getenv("DB_NAME")
COLL_NAME = os.getenv("COLL_NAME")
BASE_URL = "https://cloud.mongodb.com/api/atlas/v2"
NUM_DIMENSIONS = int(os.getenv("NUM_DIMENSIONS"))

if not all([PUBLIC_KEY, PRIVATE_KEY, PROJECT_ID]):
    raise ValueError("❌ Missing one or more required environment variables: "
                     "ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY, or ATLAS_GROUP_ID")

# ============================================================
#  Helper: call Atlas API with Digest Auth
# ============================================================

def atlas_get(endpoint: str):
    """Perform GET request to MongoDB Atlas API with Digest Auth."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.atlas.2025-03-12+json"
    }

    try:
        response = requests.get(url, auth=HTTPDigestAuth(PUBLIC_KEY, PRIVATE_KEY), headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise PermissionError("❌ Unauthorized: Check API key roles, project access, and Digest Auth.")
        else:
            raise RuntimeError(f"⚠️ Unexpected status {response.status_code}: {response.text[:500]}")
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"💥 Request error: {e}")

def atlas_post(endpoint: str, payload: dict):
    """Perform POST request to MongoDB Atlas API with Digest Auth."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.atlas.2025-03-12+json",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url,
            auth=HTTPDigestAuth(PUBLIC_KEY, PRIVATE_KEY),
            headers=headers,
            json=payload
        )

        if response.status_code in (200, 201, 202):
            return response.json()
        elif response.status_code == 401:
            raise PermissionError("❌ Unauthorized: Check API key roles, project access, and Digest Auth.")
        else:
            raise RuntimeError(f"⚠️ POST {endpoint} failed ({response.status_code}): {response.text[:500]}")

    except requests.exceptions.RequestException as e:
        raise SystemExit(f"💥 Request error: {e}")
# ============================================================
#  Connectivity check
# ============================================================

def check_connectivity():
    """Confirm we can reach Atlas API and list clusters."""
    print("🧠 Checking Atlas API connectivity ...")
    endpoint = f"groups/{PROJECT_ID}/clusters"
    data = atlas_get(endpoint)

    if "results" in data:
        print(f"✅ Connected successfully — found {len(data['results'])} cluster(s).")
        for cluster in data["results"]:
            print(f"   • {cluster['name']} (state: {cluster.get('stateName', 'unknown')})")
    else:
        print("⚠️ Atlas API returned no clusters; check project ID or permissions.")


# ============================================================
#  List vector search indexes
# ============================================================
def list_vector_indexes():
    print(f"🔍 Checking vector search indexes for cluster: {CLUSTER_NAME}")
    endpoint = f"groups/{PROJECT_ID}/clusters/{CLUSTER_NAME}/search/indexes"
    data = atlas_get(endpoint)

    if isinstance(data, dict) and "results" in data:
        indexes = data["results"]
    elif isinstance(data, list):
        indexes = data
    else:
        indexes = []

    for idx in indexes:
        name = idx.get("name", "")
        print(f"   • {name} ({idx.get('type')}) on {idx.get('collectionName')} — {idx.get('status', '?')}")
    return indexes

# ============================================================
#  Vector Search Index Management
# ============================================================

def manage_vector_index():
    """List Atlas Vector Search indexes using the /search/indexes endpoint."""
    if not CLUSTER_NAME:
        print("⚠️  No ATLAS_CLUSTER_NAME defined — skipping vector index check.")
        return

    print(f"🔎 Checking vector search indexes for cluster: {CLUSTER_NAME}")
    endpoint = f"groups/{PROJECT_ID}/clusters/{CLUSTER_NAME}/search/indexes"
    data = atlas_get(endpoint)

    # Handle both dict and list API responses
    if isinstance(data, dict) and "results" in data:
        indexes = data["results"]
    elif isinstance(data, list):
        indexes = data
    else:
        indexes = []

    if indexes:
        print(f"✅ Found {len(indexes)} search index(es):")
        for idx in indexes:
            name = idx.get("name", "Unnamed")
            index_type = idx.get("type", "?")
            coll = idx.get("collectionName", "?")
            status = idx.get("status", "?")
            print(f"   • {name} ({index_type}) on {coll} — status: {status}")
    else:
        print("⚠️ No indexes returned — check cluster name or permissions.")

# ============================================================
# 2. Create embedding vector index if missing
# ============================================================
def ensure_fullplot_vector_index():
    indexes = list_vector_indexes()
    existing = next((i for i in indexes if i.get("name") == INDEX_NAME), None)

    if existing:
        print(f"✅ Vector index '{INDEX_NAME}' already exists — no action taken.")
        return

    print(f"🚀 Creating vector search index '{INDEX_NAME}' on {DB_NAME}.{COLL_NAME} ...")

    payload = {
        "collectionName": COLL_NAME,
        "database": DB_NAME,
        "name": INDEX_NAME,
        "type": "vectorSearch",
        "fields": [
            {
                # "path": "fullplot_embedding",
                "path": "fullplot_embedding",
                "type": "vector",
                "numDimensions": NUM_DIMENSIONS,
                "similarity": "cosine"
            }
        ]
    }

    resp = atlas_post(
        f"groups/{PROJECT_ID}/clusters/{CLUSTER_NAME}/fts/indexes",
        payload
    )

    if "id" in resp:
        print(f"✅ Created vector index '{INDEX_NAME}' successfully (id={resp['id']})")
    else:
        print(f"⚠️ Failed to create vector index '{INDEX_NAME}'. See response:")
        print(resp)

# ============================================================
#  Main
# ============================================================

if __name__ == "__main__":
    try:
        check_connectivity()
        manage_vector_index()
        ensure_fullplot_vector_index()
        print("🏁 Done.")
    except Exception as e:
        print(f"💥 {e}")
        sys.exit(1)