# 🧩 Atlas RAG Pipeline — Jupyter Notebook Edition

![diagram](docs/atlas_rag_pipeline.png)

This project demonstrates a **Retrieval-Augmented Generation (RAG)** workflow that combines:

- **MongoDB Atlas Vector Search** — for fast semantic retrieval  
- **VoyageAI Embeddings** — to encode text meaningfully  
- **Ollama + Mistral** — for local, private LLM inference  

All code is runnable directly inside a **Jupyter Notebook** (including Google Colab).

---

## 🚀 Features

- End-to-end RAG pipeline in a single notebook  
- Secure `.env.vault` environment variable management  
- Semantic search over MongoDB Atlas collections  
- Local LLM inference using the Ollama REST API  
- Storytelling-style explanations for each cell  

---

## ⚙️ Prerequisites

1. **Install Ollama**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull mistral
   ```

2. **Set up MongoDB Atlas**
   - Create a collection and enable **Vector Search**
   - Create a vector index (e.g., `fullplot_vector_index`)
   - Upload documents with vector embeddings

3. **Obtain API Keys**
   - [VoyageAI API key](https://voyageai.com)
   - [MongoDB Atlas connection string](https://cloud.mongodb.com)

4. **Create `.env.vault`**
   ```bash
   MONGODB_URI="your_mongodb_connection_uri"
   VOYAGE_API_KEY="your_voyage_api_key"
   DB_NAME="sample_mflix"
   COLL_NAME="movies"
   FULLPLOT_INDEX_NAME="fullplot_vector_index"
   VECTOR_FIELD="fullplot_embedding"
   LLM_MODEL="mistral"
   ```

---

## 🧠 Running the Notebook

1. **Open in Jupyter or Colab**
   - Clone the repo and open `Atlas RAG Pipeline.ipynb`
   - Or upload it directly into Google Colab.

2. **Run Initialization Cell**
   ```python
   from dotenv_vault import load_dotenv
   load_dotenv(dotenv_path=".env.vault", override=True)
   ```

3. **Start Ollama (if running locally)**
   ```bash
   ollama serve &
   ```

4. **Execute the notebook cells sequentially**
   Each section builds on the previous one, from environment setup → retrieval → generation.

---

## 📊 Workflow Diagram

```mermaid
flowchart TD
    A[User Query] --> B[VoyageAI Embeddings]
    B --> C[MongoDB Atlas Vector Search]
    C --> D[Top-k Similar Documents]
    D --> E[Prompt Assembly]
    E --> F[Ollama (Mistral Model)]
    F --> G[Generated Answer]
```

---

## 🧪 Example Query

```python
!python3 rag_mistral_complete.py "Which movies feature artificial intelligence or sentient robots?"
```

Output:

```
🔎 Generating embeddings for query...
🧠 Retrieved documents:
- Bicentennial Man
- I, Robot
💬 Generated Answer:
These films explore human-like AI behavior and the tension between sentience and control.
```

---

## 💡 Notes

- The notebook uses **VoyageAI** embeddings for retrieval, not OpenAI.
- If you use Google Colab, Ollama runs locally within the environment.
- Adjust `OLLAMA_HOST` in `.env.vault` if connecting to a remote instance.

---

## 🧩 License

MIT © 2025 Michael Ford
