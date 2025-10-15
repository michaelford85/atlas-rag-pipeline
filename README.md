# 🧩 Atlas RAG Pipeline — Jupyter & Colab Edition

![diagram](docs/atlas_rag_pipeline.png)

This project demonstrates an end-to-end **Retrieval-Augmented Generation (RAG)** workflow combining:

- 🧬 **VoyageAI Embeddings** — to semantically encode text  
- 🌍 **MongoDB Atlas Vector Search** — to retrieve contextually similar content  
- 🤖 **Ollama + Mistral** — to generate grounded, private LLM responses locally  

All code is runnable directly inside a **Jupyter Notebook or Google Colab**, with narrative explanations at each step to help users understand the full RAG process.

---

## 🚀 Overview

The notebook walks through each major stage of the RAG workflow:

| Step | Description |
|------|--------------|
| 1️⃣ | Clone and set up the repository environment |
| 2️⃣ | Mount Google Drive and securely load `.env.vault` keys |
| 3️⃣ | Configure and test MongoDB Atlas + VoyageAI connections |
| 4️⃣ | Build or update vector embeddings and indexes |
| 5️⃣ | Install and configure Ollama with Mistral |
| 6️⃣ | Verify model connectivity via the Ollama API |
| 7️⃣ | Run full RAG queries combining retrieval and generation |
| 8️⃣ | Optionally restart Ollama to refresh connections |

---

## 🧭 System Flow Diagram

```mermaid
flowchart TD
    A[🔑 Mount Google Drive / Load .env.vault] --> B[⚙️ Clone and Setup Repository]
    B --> C[🧮 Generate VoyageAI Embeddings]
    C --> D[🌍 MongoDB Atlas Vector Search]
    D --> E[📄 Retrieve Similar Documents]
    E --> F[🧱 Assemble Prompt with Context]
    F --> G[🤖 Ollama (Mistral Model)]
    G --> H[💬 Generated Response to User]
    H --> I[🔄 (Optional) Restart Ollama Server]
```

---

## ⚙️ Prerequisites

1. **Install Ollama (locally or in Colab)**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull mistral
   ```

2. **Set up MongoDB Atlas**
   - Create a collection and enable **Vector Search**  
   - Create a vector index (e.g., `fullplot_vector_index`)  
   - Populate it with text embeddings using VoyageAI  

3. **Obtain API Keys**
   - [VoyageAI API key](https://voyageai.com)  
   - [MongoDB Atlas connection string](https://cloud.mongodb.com)

4. **Create your `.env.vault`**
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

## 🧩 Notebook Storyline

Below are the **key narrative steps** used throughout the notebook — each represented by a Markdown cell above the matching code cell.

### 1️⃣ Clone and Setup Repository
> Installs `git`, removes any old version, and clones the **atlas-rag-pipeline** repository.  
> Ensures the environment is current before running the pipeline.

### 2️⃣ Enable Output Wrapping
> Adds CSS to wrap long text outputs in Colab for easier readability of model responses.

### 3️⃣ Load Environment Variables
> Securely loads your `.env.vault` or `.env` file to configure credentials for MongoDB, VoyageAI, and Ollama.

### 4️⃣ Mount Google Drive (Colab Only)
> Mounts Google Drive, retrieves your `atlas_rag_pipeline_dotenv_key.txt`, and sets it as the `DOTENV_KEY` variable.

### 5️⃣ Build Vector Embeddings and Indexes
> Executes helper scripts to generate embeddings using VoyageAI and manage the MongoDB Atlas vector index.

### 6️⃣ Set Up Ollama with Ansible
> Automatically installs and configures Ollama on Ubuntu, enabling consistent and repeatable setup.

### 7️⃣ Test Mistral Model
> Uses a sample `curl` command to test the Ollama REST API and confirm that the local model responds correctly.

### 8️⃣ Run Full RAG Query
> Executes `rag_mistral_complete_input.py` to run the retrieval-augmented generation process end-to-end.  
> Retrieves top-k documents, constructs a contextual prompt, and generates an answer using Mistral.

### 9️⃣ Restart Ollama (Optional)
> Safely restarts the Ollama server to clear connections or memory before running new sessions.

---

## 🧠 Example Usage

### **Run a Full Query**
```bash
!python3 atlas-rag-pipeline/rag_mistral_complete_input.py "Which movies feature artificial intelligence or sentient robots?"
```

### **Expected Output**
```
🔎 Generating embeddings for query...
🧠 Retrieved documents:
- Bicentennial Man
- I, Robot
💬 Generated Answer:
These films explore human-like AI behavior and the tension between sentience and control.
```

---

## 🧩 Optional Maintenance Commands

### **Restart Ollama**
```bash
!pkill ollama || true
!nohup ollama serve > /tmp/ollama.log 2>&1 &
!sleep 10
```

> Use this if you encounter connection errors or need to reset the Ollama service during testing.

---

## 💡 Tips

- When using Colab, rerun the **Ollama startup cell** after reconnecting to your runtime.  
- Keep your `atlas_rag_pipeline_dotenv_key.txt` in a private Google Drive folder for secure access.  
- You can modify the RAG query string to explore different movie-related or conceptual questions.

---

## 📜 License

MIT © 2025 Michael Ford
