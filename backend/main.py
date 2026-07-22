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

# Enable CORS for local development (frontend running on port 5173 or 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })

    return {
        "message": f"Processed {len(files)} files",
        "details": results
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
