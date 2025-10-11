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
  - MongoDB Atlas Trigger keeps vector data in sync with CRUD operations
- **Python Loader Script**
  - Populates the database and computes initial embeddings via the VoyageAI API
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