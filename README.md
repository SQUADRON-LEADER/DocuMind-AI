# 🧠 DocuMind AI (Kinetic Typography Document RAG Platform)

> **DocuMind AI** is an intelligent document processing and Retrieval-Augmented Generation (RAG) platform powered by ChromaDB vector search and a Kinetic Typography design system.

---

## ⚡ Features

- **Kinetic Typography UI**: High-energy brutalist aesthetic with Acid Yellow (`#DFE104`) accents, uppercase display lockups, and infinite ticker marquees.
- **Vector Search Engine**: Semantic document chunking & ChromaDB vector storage using `sentence-transformers` (`all-MiniLM-L6-v2`).
- **Context-Aware RAG Synthesis**: Answers questions strictly based on uploaded PDF document context with precise page citations.
- **Drag & Drop PDF Ingestion**: Instant client-side PDF upload, vector indexing, and chunk management.
- **Privacy First**: Sensitive credential protection with strict `.gitignore` filters.

---

## 🚀 Getting Started

### 1. Installation

Clone the repository:
```bash
git clone https://github.com/SQUADRON-LEADER/DocuMind-AI.git
cd DocuMind-AI
```

Install backend dependencies:
```bash
pip install -r requirements.txt
```

Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

### 2. Environment Setup

Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_api_key_here
```

### 3. Run Application

Launch both backend (FastAPI) and frontend (Vite React) using the one-click runner:
```bash
python run.py
```

- **Frontend UI**: `http://localhost:5173`
- **Backend API**: `http://127.0.0.1:8000`

---

## 📂 Project Structure

```
DocuMind-AI/
├── backend/
│   ├── main.py              # FastAPI REST endpoints
│   ├── rag_engine.py        # Core RAG pipeline & vector store engine
│   └── requirements.txt     # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # React SPA with Kinetic Typography design
│   │   ├── index.css        # Kinetic Typography Design System
│   │   └── main.jsx         # Vite entry point
│   ├── index.html           # HTML template
│   └── package.json         # Frontend dependencies
├── requirements.txt         # Root Python requirements
├── run.py                   # One-click fullstack launcher
└── README.md                # Project documentation
```

---

## 📄 License
MIT License
