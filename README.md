# Atlas RAG Pipeline — Jupyter & Colab Edition

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/michaelford85/atlas-rag-pipeline/blob/main/atlas_rag_pipeline.ipynb)

This project demonstrates an end-to-end **Retrieval-Augmented Generation (RAG)** workflow combining:

- **VoyageAI Embeddings** — to semantically encode text into vector representations
- **MongoDB Atlas Vector Search** — to retrieve contextually similar content from a database
- **Ollama + Mistral** — to generate grounded, private LLM responses locally

All code is runnable directly inside a **Jupyter Notebook or Google Colab**, with narrative explanations at each step to help you understand the full RAG process.

---

## What is RAG?

**Retrieval-Augmented Generation (RAG)** is a technique that improves AI-generated answers by first searching a knowledge base for relevant information, then passing that context to a language model to formulate a response. Rather than relying solely on what a model learned during training, RAG grounds answers in real data you control.

This notebook uses MongoDB Atlas as that knowledge base, VoyageAI to convert text into searchable vectors, and Ollama to run the language model locally on your machine.

---

## How the Pipeline Works

```
Your Question
     │
     ▼
VoyageAI API ──► Converts your question into a vector embedding
     │
     ▼
MongoDB Atlas Vector Search ──► Finds documents whose embeddings are semantically similar
     │
     ▼
Ollama (Mistral) ──► Generates a natural-language answer using the retrieved documents as context
     │
     ▼
Your Answer
```

---

## What the Notebook Does

| Step | Description |
|------|-------------|
| 1 | Clone the repository and install dependencies |
| 2 | Load credentials (MongoDB, VoyageAI) securely |
| 3 | Generate VoyageAI vector embeddings for your collection and create an Atlas Vector Search index |
| 4 | Install and configure Ollama + Mistral locally via Ansible |
| 5 | Verify the local model is running via a test prompt |
| 6 | Run a full end-to-end RAG query (retrieval + generation) |
| 7 | Launch an interactive Gradio web UI to query your data in real time |

---

## Prerequisites

### 1. MongoDB Atlas cluster with sample data

- Create a free cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
- Load the **Sample Mflix** dataset (Movies) from the Atlas UI — or use any collection you prefer
- The notebook will create the vector embeddings and search index for you automatically

### 2. VoyageAI API key

- Sign up at [voyageai.com](https://www.voyageai.com) to get an API key
- VoyageAI converts your text into high-quality vector embeddings

### 3. Ollama (for local LLM inference)

The notebook installs Ollama automatically via Ansible. If you want to install it manually:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral
```

### 4. API credentials

You will need:
- Your **MongoDB Atlas connection string** (URI)
- Your **VoyageAI API key**
- Your **MongoDB Atlas API public and private keys** (for programmatic index management)
- Your **Atlas Project (Group) ID** and **cluster name**

The notebook provides two ways to load these — via an encrypted `.env.vault` file stored in Google Drive (recommended for Colab), or by pasting values directly into a cell (suitable for local runs or demos).

---

## Notebook Walkthrough

### 1. Clone and Set Up the Repository

Installs `git` and clones the latest version of this repository so the notebook always runs against current code.

### 2. Load Credentials

**Option A — Secure (Colab recommended):** Mount Google Drive, read your Dotenv Vault key file, and decrypt a `.env.vault` file containing your secrets. Credentials never appear in the notebook.

**Option B — Simple:** Set environment variable values directly in a cell. Suitable for local development or demos. Never commit real keys to GitHub.

### 3. Generate Embeddings and Build the Vector Index

The notebook runs two helper scripts:

- **`update_voyage_ai_embeddings.py`** — calls the VoyageAI API to generate vector embeddings for each document in your collection (e.g., the `fullplot` and `plot` fields of a movies collection) and stores them as new fields on each document.
- **`manage_vector_index.py`** — creates (or verifies) an Atlas Vector Search index over those embedding fields and waits until it is fully built before continuing.

You configure which fields to embed, the model to use, and the index name through environment variables in the notebook.

An optional script, `remove_embeddings.py`, can wipe existing embeddings if you need to regenerate them from scratch.

### 4. Set Up Ollama with Ansible

An Ansible playbook installs Ollama, configures it as a systemd service, and pulls the Mistral model. This makes the setup consistent whether you are running locally or on a fresh Colab VM.

### 5. Test the Local Model

Sends a simple test prompt to the Ollama REST API (`http://localhost:11434/api/generate`) and prints the response. This confirms the model is running before you execute the full pipeline.

### 6. Run a Full RAG Query

Executes `rag_with_input.py` with a natural-language question. The script:
1. Embeds your question using VoyageAI
2. Runs a `$vectorSearch` query against MongoDB Atlas to retrieve the most semantically similar documents
3. Passes those documents as context to Mistral via Ollama
4. Prints the generated answer

Example query used in the notebook:
> *"Which movies feature artificial intelligence or sentient robots?"*

You can swap in any question to explore how the system responds.

### 7. Interactive Gradio UI

Installs [Gradio](https://gradio.app) and launches a simple web interface. You type a question, hit submit, and the app retrieves relevant documents from Atlas and generates an answer — all without touching the notebook cells. A shareable public link is generated so you can demo the pipeline to others.

When you are done, a cleanup cell shuts down the Gradio server gracefully.

---

## Optional: Restart Ollama

If Ollama becomes unresponsive during a long session, the notebook includes a cell to restart it cleanly:

```bash
pkill ollama || true
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 10
```

---

## Tips

- When using Colab, rerun the Ollama startup cell after reconnecting to your runtime — Colab VMs reset between sessions.
- You can point the pipeline at any MongoDB collection by changing the `DB_NAME`, `COLL_NAME`, and `EMBEDDING_PATHS` environment variables in the notebook.
- The `voyage-4-large` model (1024 dimensions) is used by default. You can change the model and dimension count to match whatever VoyageAI model you prefer.
- Keep your credential files in a private Google Drive folder and never commit them to version control.

---

## License

MIT © 2025 Michael Ford
