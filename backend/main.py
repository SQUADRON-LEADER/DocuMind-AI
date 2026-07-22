import os
import shutil
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.rag_engine import RAGEngine

app = FastAPI(
    title="DocuMind AI API",
    description="Backend service for PDF indexing, vector retrieval, and RAG search",
    version="1.0.0"
)

# CORS: allow_credentials must be False when allow_origins=["*"]
# (browsers reject credentials=True + wildcard origin — blocks Vercel → Render calls)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine instance
rag_engine = RAGEngine(data_dir="data")


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 4


@app.on_event("startup")
async def startup_event():
    print("[DocuMind AI] Starting backend server...")
    # Skip auto-indexing on Render (RENDER env var is always set there).
    # Auto-indexing loads the ~400MB embedding model which OOMs the 512MB free tier.
    # Users upload PDFs via the UI instead.
    is_render = os.environ.get("RENDER", "").lower() in ("true", "1", "yes")
    if not is_render:
        import asyncio
        async def _delayed_indexing():
            await asyncio.sleep(15)
            try:
                results = await asyncio.to_thread(rag_engine.index_workspace_pdfs)
                if results:
                    print(f"[DocuMind AI] Indexed {len(results)} workspace PDF documents.")
            except Exception as e:
                print(f"[DocuMind AI] Startup indexing notice: {e}")
        asyncio.create_task(_delayed_indexing())
    else:
        print("[DocuMind AI] Running on Render — skipping auto-indexing to conserve memory.")




@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "DocuMind AI Backend",
        "vector_count": rag_engine.vector_store.collection.count()
    }


@app.get("/api/stats")
def get_stats():
    stats = rag_engine.vector_store.get_collection_stats()
    docs = rag_engine.vector_store.list_indexed_documents()
    return {
        "collection_name": stats["collection_name"],
        "total_chunks": stats["total_chunks"],
        "total_documents": len(docs),
        "embedding_model": rag_engine.embedding_manager.model_name,
        "llm_model": "gemini-3.5-flash"
    }


@app.get("/api/documents")
def list_documents():
    return {
        "documents": rag_engine.vector_store.list_indexed_documents()
    }


@app.delete("/api/documents/{filename}")
def delete_document(filename: str):
    deleted_chunks = rag_engine.vector_store.delete_document_by_filename(filename)
    # Also attempt to remove from uploads directory if exists
    uploaded_path = os.path.join(rag_engine.uploads_dir, filename)
    if os.path.exists(uploaded_path):
        try:
            os.remove(uploaded_path)
        except Exception:
            pass

    return {
        "status": "success",
        "filename": filename,
        "deleted_chunks": deleted_chunks
    }


@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File '{file.filename}' is not a PDF.")

        file_path = os.path.join(rag_engine.uploads_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            res = rag_engine.process_pdf_file(file_path)
            results.append(res)
        except Exception as e:
            import traceback
            err_detail = traceback.format_exc()
            print(f"[DocuMind AI] Upload error for {file.filename}: {err_detail}")
            raise HTTPException(status_code=500, detail=f"Indexing failed for '{file.filename}': {str(e)}")

    return {
        "message": f"Processed {len(files)} files",
        "details": results
    }


@app.get("/api/debug")
def debug_info():
    """Debug endpoint — shows embedding mode and config without secrets."""
    import os as _os
    return {
        "render_env": _os.environ.get("RENDER", "not set"),
        "gemini_api_key_set": bool(_os.environ.get("GEMINI_API_KEY")),
        "embedding_mode": "google" if _os.environ.get("RENDER", "").lower() in ("true","1","yes") else "local",
        "vector_count": rag_engine.vector_store.collection.count(),
        "uploads_dir": rag_engine.uploads_dir,
    }


@app.get("/api/test-embed")
def test_embed():
    import os as _os
    import google.generativeai as genai
    api_key = _os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    supported_models = []
    try:
        for m in genai.list_models():
            if "embedContent" in m.supported_generation_methods:
                supported_models.append(m.name)
    except Exception as e:
        supported_models = [f"list_models error: {str(e)}"]

    results = {}
    candidates = [
        "models/text-embedding-004",
        "text-embedding-004",
        "models/embedding-001",
        "embedding-001"
    ]
    for model_name in candidates:
        try:
            res = genai.embed_content(
                model=model_name,
                content="test content",
                task_type="retrieval_document"
            )
            emb = res.get("embedding", [])
            results[model_name] = f"SUCCESS: vector dim = {len(emb)}"
        except Exception as e:
            results[model_name] = f"ERROR: {str(e)}"

    return {
        "supported_models_from_api": supported_models,
        "test_results": results
    }



@app.post("/api/query")
def execute_query(req: QueryRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    result = rag_engine.query(query_text=req.query.strip(), top_k=req.top_k or 4)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
