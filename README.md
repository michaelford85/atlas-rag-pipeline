# 🧠 Ollama + MongoDB Atlas RAG

End-to-end **Retrieval-Augmented Generation (RAG)** stack powered by **Ollama** for local LLM inference and **MongoDB Atlas** for vector storage.  
This project demonstrates how to build a self-contained, continuously updated knowledge base that feeds relevant context to an LLM in real time.

---

## 🚀 Features

- **Local LLM Inference with Ollama**
  - Runs any model available in Ollama (e.g., `llama3`, `mistral`, `phi3`)
- **Vector Storage in MongoDB Atlas**
  - Stores embeddings for documents in an Atlas collection using a Vector Search index
- **Automatic Embedding Refresh**
  - MongoDB Atlas Trigger or local scripts keep vector data in sync with CRUD operations
- **Python Embedding Management**
  - `update_embeddings.py` creates embeddings for new or missing documents  
  - `remove_fullplot_embeddings.py` removes old or deprecated embedding fields
- **Composable RAG Pipeline**
  - Retrieve → Rank → Augment → Generate responses through a simple Python interface

---

## 🏗️ Architecture

```mermaid
graph TD
    A[Python ETL Script] -->|Inserts Documents| B[(MongoDB Atlas)]
    B -->|Stores Vectors| C[Atlas Vector Search Index]
    C -->|Retrieval Context| D[Ollama LLM]
    D -->|Response| E[User]
    B -->|Change Event| F[Atlas Trigger]
    F -->|Update Embeddings| B
```

---

## ⚙️ Environment Setup

All scripts use environment variables loaded from a secure `.env.vault` file via [dotenv-vault](https://github.com/dotenv-org/dotenv-vault).

### Required Variables

| Variable | Description | Default / Example |
|-----------|--------------|-------------------|
| `MONGODB_URI` | Connection string to MongoDB Atlas or local instance | `mongodb+srv://user:pass@cluster.mongodb.net` |
| `DB_NAME` | Database name | `sample_mflix` |
| `COLL_NAME` | Collection name | `movies` |
| `VOYAGE_API_KEY` | VoyageAI API key | _(required)_ |
| `MODEL_NAME` | Voyage model for embedding generation | `voyage-3-large` |
| `BATCH_SIZE` | Number of documents processed per API call | `10` |

> ⚠️ Never commit `.env.vault` contents or raw keys to Git.  
> These values are automatically loaded when you run the scripts.

---

## 🧠 Scripts

### 1️⃣ `update_embeddings.py`

Generates embeddings for documents that have a `fullplot` field but are missing `fullplot_embedding`.

#### What It Does
- Connects to your MongoDB collection  
- Calls the VoyageAI API in batches  
- Updates each document with:
  - `fullplot_embedding`
  - `embedding_model`
  - `embedding_updated_at`

#### Run Locally
```bash
python3 update_embeddings.py
```

#### Run in Docker
```bash
docker run   -e DOTENV_KEY="dotenv://:key_abc123@dotenv.org/vault/.env.vault?environment=production"   your_image_name python3 update_embeddings.py
```

#### Example Output
```
📄 Found 245 documents missing embeddings
💾 Updated 10 docs (10/245 total)
✅ Embedding update complete.
```

---

### 2️⃣ `remove_fullplot_embeddings.py`

Removes old or deprecated embedding fields such as `plot_embedding_voyage_3_large`.

#### What It Does
- Executes an `$unset` operation across all documents  
- Can be modified to target any field you want removed

#### Run Locally
```bash
python3 remove_fullplot_embeddings.py
```

#### Example Output
```
🧹 Removing field: plot_embedding_voyage_3_large
✅ Removed from 1,232 documents.
```

---

## 🧩 Docker Usage

```bash
docker build -t ollama-atlas-rag .
docker run --rm -it   --env-file .env   --env-file .env.secrets   ollama-atlas-rag
```

> For production use, replace `--env-file` with your `.env.vault` configuration and pass the `DOTENV_KEY` variable securely.

---

## 🧱 Notes & Best Practices

- **Batch Size:**  
  Adjust `BATCH_SIZE` if you encounter VoyageAI rate limits or MongoDB document size issues.

- **Retries:**  
  The embedding script includes retry logic (3 attempts with delay) to handle temporary API or network issues.

- **Idempotent Updates:**  
  Re-running `update_embeddings.py` is safe — only documents missing the `fullplot_embedding` field are processed.

- **Cleaning Old Data:**  
  Use `remove_fullplot_embeddings.py` before switching models to ensure your collection contains only current embeddings.

---

## 🧩 Next Steps

- Create a **Vector Search Index** in MongoDB Atlas on the `fullplot_embedding` field.  
- Use the stored vectors to perform retrieval + ranking in your Ollama RAG pipeline.  
- Optionally set up an **Atlas Trigger** to automatically invoke embedding refresh on document insert/update events.
