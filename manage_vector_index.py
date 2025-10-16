#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
import argparse
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
DB_NAME = os.getenv("DB_NAME")
COLL_NAME = os.getenv("COLL_NAME")
INDEX_NAME = os.getenv("INDEX_NAME")
NUM_DIMENSIONS = int(os.getenv("NUM_DIMENSIONS", "1536"))
BASE_URL = "https://cloud.mongodb.com/api/atlas/v2"

if not all([PUBLIC_KEY, PRIVATE_KEY, PROJECT_ID]):
    raise ValueError("❌ Missing one or more required environment variables: "
                     "ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY, or ATLAS_GROUP_ID")

# ============================================================
#  Helper: Atlas API (Digest Auth)
# ============================================================

def atlas_get(endpoint: str):
    """Perform GET request to MongoDB Atlas API with Digest Auth."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {"Accept": "application/vnd.atlas.2025-03-12+json"}

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
    """Return all vector/search indexes for the given cluster."""
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
#  Wait for vector index to reach READY
# ============================================================

def wait_for_index_ready(index_name, poll_interval=15, timeout=900):
    """Poll Atlas until the specified index reaches READY status."""
    print(f"⏳ Waiting for index '{index_name}' to become READY ...")
    start = time.time()

    while time.time() - start < timeout:
        indexes = list_vector_indexes()
        idx = next((i for i in indexes if i.get("name") == index_name), None)

        if not idx:
            print(f"⚠️ Index '{index_name}' not found yet, retrying...")
        else:
            status = idx.get("status", "UNKNOWN")
            print(f"   • Current status: {status}")
            if status.upper() == "READY":
                print(f"✅ Index '{index_name}' is READY!")
                return True
        time.sleep(poll_interval)

    print(f"⌛ Timeout reached — index '{index_name}' not READY after {timeout/60:.1f} min.")
    return False

# ============================================================
#  Vector Search Index Management
# ============================================================

def ensure_vector_index(index_name: str, fields: list[str], similarity: str = "cosine"):
    """Ensure a vector index exists with the specified fields."""
    indexes = list_vector_indexes()
    existing = next((i for i in indexes if i.get("name") == index_name), None)

    if existing:
        status = existing.get("status", "UNKNOWN")
        print(f"✅ Vector index '{index_name}' already exists (status={status}).")
        if status.upper() != "READY":
            wait_for_index_ready(index_name)
        return

    print(f"🚀 Creating vector search index '{index_name}' on {DB_NAME}.{COLL_NAME} ...")

    field_definitions = [
        {
            "path": field,
            "type": "vector",
            "numDimensions": NUM_DIMENSIONS,
            "similarity": similarity
        }
        for field in fields
    ]

    payload = {
        "collectionName": COLL_NAME,
        "database": DB_NAME,
        "name": index_name,
        "type": "vectorSearch",
        "fields": field_definitions
    }

    resp = atlas_post(f"groups/{PROJECT_ID}/clusters/{CLUSTER_NAME}/fts/indexes", payload)

    if "id" in resp or "indexID" in resp or resp.get("status") == "IN_PROGRESS":
        print(f"✅ Index creation started (status={resp.get('status', 'IN_PROGRESS')})")
        wait_for_index_ready(index_name)
    else:
        print(f"⚠️ Failed to create vector index '{index_name}'. See response:")
        print(resp)

# ============================================================
#  Main CLI entrypoint
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage MongoDB Atlas Vector Indexes")
    parser.add_argument("--index-name", type=str, help="Name of the vector index")
    parser.add_argument("--fields", nargs="+", help="List of vector embedding fields (space-separated)")
    parser.add_argument("--similarity", type=str, choices=["cosine", "euclidean", "dotProduct"], default="cosine",
                        help="Similarity metric (default: cosine)")
    parser.add_argument("--wait", action="store_true", help="Wait for the index to finish building before exiting")
    parser.add_argument("--timeout", type=int, default=900, help="Maximum wait time in seconds (default 900s)")

    args = parser.parse_args()

    try:
        check_connectivity()
        list_vector_indexes()

        # Determine which fields and index name to use
        index_name = args.index_name or INDEX_NAME
        env_fields = os.getenv("EMBEDDING_NAMES", "")
        fields = args.fields or [f.strip() for f in env_fields.split(",") if f.strip()]

        if not fields:
            raise ValueError("❌ No embedding fields provided (via --fields or EMBEDDING_NAMES).")

        ensure_vector_index(index_name, fields, similarity=args.similarity)

        if args.wait:
            wait_for_index_ready(index_name, timeout=args.timeout)

        print("🏁 Done.")

    except Exception as e:
        print(f"💥 {e}")
        sys.exit(1)