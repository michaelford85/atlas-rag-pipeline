import os
from dotenv import load_dotenv
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings

print("🔐 Loading environment variables ...")

# Try to load from .env.vault first
dotenv_path_encrypted = ".env.vault"
print(f"🔍 Loading env from {dotenv_path_encrypted}...")
load_dotenv(dotenv_path=dotenv_path_encrypted, override=True)

# Retrieve environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLL_NAME = os.getenv("COLL_NAME", "movies")
INDEX_NAME = os.getenv("INDEX_NAME", "vector_index")
MODEL_NAME = os.getenv("MODEL_NAME", "voyage-3-large")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))

# --- Sanity checks ---
missing_vars = [k for k, v in {
    "MONGODB_URI": MONGODB_URI,
    "VOYAGE_API_KEY": VOYAGE_API_KEY,
}.items() if not v]

if missing_vars:
    raise EnvironmentError(f"❌ Missing required environment variables: {missing_vars}")

print(f"✅ Loaded environment for DB '{DB_NAME}', collection '{COLL_NAME}', model '{MODEL_NAME}'")

# --- Create vector store ---
vectorStore = MongoDBAtlasVectorSearch.from_connection_string(
    MONGODB_URI,
    f"{DB_NAME}.{COLL_NAME}",
    OpenAIEmbeddings(
        model="text-embedding-3-large",
        disallowed_special=(),
        api_key=VOYAGE_API_KEY
    ),
    index_name=INDEX_NAME,
)

# --- Query helper ---
def query_data(query: str):
    retriever = vectorStore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 3,
            "pre_filter": {"hasCode": {"$eq": False}},
            "score_threshold": 0.01,
        },
    )
    results = retriever.invoke(query)
    print("🧠 Query results:")
    for r in results:
        print(f"- {r.page_content[:180]}...\n")

# --- Example run ---
if __name__ == "__main__":
    query_data("When did MongoDB begin supporting multi-document transactions?")