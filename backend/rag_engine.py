import os
import uuid
import numpy as np
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Use Google Embedding API on Render (no heavy ML libs needed)
# Fall back to sentence-transformers locally
_USE_GOOGLE_EMBEDDINGS = os.environ.get("RENDER", "").lower() in ("true", "1", "yes")


class EmbeddingManager:
    """Manages embedding generation.

    On Render: uses google.generativeai.embed_content (v1 API, not v1beta) directly.
    Locally: uses sentence-transformers.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._local_model = None
        self._configured = False

    def _configure_google(self):
        if not self._configured:
            api_key = os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            self._configured = True

    def _get_local_model(self):
        if self._local_model is None:
            try:
                import torch
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)
            except Exception:
                pass
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(self.model_name)
        return self._local_model

    def generate_embeddings(self, texts: List[str]):
        if _USE_GOOGLE_EMBEDDINGS:
            self._configure_google()
            # Embed in batches of 100 (API limit)
            all_embeddings = []
            for i in range(0, len(texts), 100):
                batch = texts[i:i+100]
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=batch,
                    task_type="retrieval_document"
                )
                # result['embedding'] is list of vectors when content is a list
                vecs = result['embedding']
                if isinstance(vecs[0], float):   # single text returned flat list
                    all_embeddings.append(vecs)
                else:
                    all_embeddings.extend(vecs)
            return np.array(all_embeddings)
        else:
            model = self._get_local_model()
            return model.encode(texts, show_progress_bar=False, batch_size=8)

    def generate_query_embedding(self, text: str):
        if _USE_GOOGLE_EMBEDDINGS:
            self._configure_google()
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                task_type="retrieval_query"
            )
            return np.array(result['embedding'])
        else:
            model = self._get_local_model()
            return model.encode([text], show_progress_bar=False)[0]


class VectorStoreManager:
    """Manages ChromaDB persistent vector collection for documents."""
    def __init__(self, persist_directory: str = "data/vector_store", collection_name: str = "documind_collection"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        # embedding_function=None: we manage our own embeddings (Google API or sentence-transformers)
        # Without this, chromadb loads its default ONNX model (memory-intensive)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Vector store for DocuMind AI PDF embeddings"},
            embedding_function=None
        )

    def add_documents(self, documents: List[Document], embeddings) -> int:
        if len(documents) != len(embeddings):
            raise ValueError("Number of documents does not match number of embeddings")

        ids = []
        all_metadata = []
        documents_content = []
        embeddings_list = []

        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            doc_id = f"doc_{uuid.uuid4()}"
            ids.append(doc_id)

            metadata = dict(doc.metadata) if doc.metadata else {}
            metadata["doc_index"] = i
            metadata["content_length"] = len(doc.page_content)
            if "source" in metadata:
                metadata["filename"] = os.path.basename(metadata["source"])
            else:
                metadata["filename"] = "unknown.pdf"

            all_metadata.append(metadata)
            documents_content.append(doc.page_content)
            embeddings_list.append(embedding.tolist())

        if ids:
            self.collection.add(
                ids=ids,
                metadatas=all_metadata,
                documents=documents_content,
                embeddings=embeddings_list
            )

        return len(documents_content)

    def get_collection_stats(self) -> Dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "total_chunks": self.collection.count()
        }

    def list_indexed_documents(self) -> List[Dict[str, Any]]:
        count = self.collection.count()
        if count == 0:
            return []

        all_items = self.collection.get(include=["metadatas"])
        metadatas = all_items.get("metadatas", [])
        
        doc_summary: Dict[str, Dict[str, Any]] = {}
        for meta in metadatas:
            filename = meta.get("filename", "unknown.pdf")
            page = meta.get("page", 1)
            if filename not in doc_summary:
                doc_summary[filename] = {
                    "filename": filename,
                    "total_chunks": 0,
                    "pages": set(),
                    "source_path": meta.get("source", filename)
                }
            doc_summary[filename]["total_chunks"] += 1
            doc_summary[filename]["pages"].add(page)

        result = []
        for fn, data in doc_summary.items():
            result.append({
                "filename": fn,
                "total_chunks": data["total_chunks"],
                "total_pages": len(data["pages"]),
                "source_path": data["source_path"]
            })
        return result

    def delete_document_by_filename(self, filename: str) -> int:
        all_items = self.collection.get(include=["metadatas"])
        ids_to_delete = []
        for doc_id, meta in zip(all_items["ids"], all_items["metadatas"]):
            if meta.get("filename") == filename or os.path.basename(meta.get("source", "")) == filename:
                ids_to_delete.append(doc_id)

        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)


class RAGEngine:
    """Main orchestration engine for PDF processing and vector retrieval."""
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.uploads_dir = os.path.join(data_dir, "uploads")
        os.makedirs(self.uploads_dir, exist_ok=True)

        self.embedding_manager = EmbeddingManager()
        self.vector_store = VectorStoreManager(persist_directory=os.path.join(data_dir, "vector_store"))
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)

    def process_pdf_file(self, file_path: str) -> Dict[str, Any]:
        """Parses a PDF file, chunks text, generates embeddings and stores in ChromaDB."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc_fitz = fitz.open(file_path)
        filename = os.path.basename(file_path)

        documents = []
        for page_idx, page in enumerate(doc_fitz):
            text = page.get_text()
            if text and text.strip():
                documents.append(Document(
                    page_content=text,
                    metadata={
                        "page": page_idx + 1,
                        "source": file_path,
                        "filename": filename,
                        "total_pages": len(doc_fitz)
                    }
                ))

        if not documents:
            return {"filename": filename, "status": "empty", "chunks": 0, "pages": len(doc_fitz)}

        chunks = self.text_splitter.split_documents(documents)
        texts = [c.page_content for c in chunks]

        embeddings = self.embedding_manager.generate_embeddings(texts)
        added_count = self.vector_store.add_documents(chunks, embeddings)

        return {
            "filename": filename,
            "status": "indexed",
            "chunks": added_count,
            "pages": len(doc_fitz)
        }

    def index_workspace_pdfs(self) -> List[Dict[str, Any]]:
        """Scans workspace root and data/ for existing PDFs and indexes any missing ones."""
        root_dir = os.path.abspath(os.path.join(self.data_dir, ".."))
        pdf_paths = []

        for target_dir in [root_dir, self.uploads_dir]:
            if os.path.exists(target_dir):
                for f in os.listdir(target_dir):
                    if f.lower().endswith(".pdf"):
                        full_p = os.path.join(target_dir, f)
                        pdf_paths.append(full_p)

        indexed_docs = self.vector_store.list_indexed_documents()
        indexed_filenames = {d["filename"] for d in indexed_docs}

        results = []
        for pdf_path in pdf_paths:
            fn = os.path.basename(pdf_path)
            if fn not in indexed_filenames:
                try:
                    res = self.process_pdf_file(pdf_path)
                    results.append(res)
                except Exception as e:
                    pass
        return results

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Retrieves top_k relevant text chunks without exposing score metrics."""
        if self.vector_store.collection.count() == 0:
            return []

        query_emb = self.embedding_manager.generate_query_embedding(query)
        results = self.vector_store.collection.query(
            query_embeddings=[query_emb.tolist()],
            n_results=min(top_k, self.vector_store.collection.count())
        )

        retrieved = []
        if results.get("documents") and results["documents"][0]:
            ids = results["ids"][0]
            metadatas = results["metadatas"][0]
            documents = results["documents"][0]

            for rank, (doc_id, meta, doc_text) in enumerate(zip(ids, metadatas, documents)):
                retrieved.append({
                    "id": doc_id,
                    "document": doc_text,
                    "metadata": meta,
                    "rank": rank + 1,
                    "filename": meta.get("filename", "document.pdf"),
                    "page": meta.get("page", 1)
                })

        return retrieved

    def query(self, query_text: str, top_k: int = 4) -> Dict[str, Any]:
        """Executes RAG query and returns context-based answer."""
        retrieved_docs = self.retrieve(query_text, top_k=top_k)

        if not retrieved_docs:
            return {
                "query": query_text,
                "answer": "No answer found in the provided document context.",
                "sources": [],
                "context_used": False
            }

        context_parts = []
        for doc in retrieved_docs:
            src_info = f"[Source: {doc['filename']}, Page: {doc['page']}]"
            context_parts.append(f"{src_info}\n{doc['document']}")
        context_str = "\n\n---\n\n".join(context_parts)

        prompt = f"""You are DocuMind AI. Answer the query strictly using the provided context. If the context does not contain enough information to answer the question, state: "No answer found in the provided document context."

Context:
{context_str}

Query: {query_text}
"""

        candidate_models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
        answer = None
        api_key = os.getenv("GEMINI_API_KEY")

        if api_key:
            for model_name in candidate_models:
                try:
                    llm_instance = ChatGoogleGenerativeAI(
                        google_api_key=api_key,
                        model=model_name,
                        temperature=0.1,
                        max_output_tokens=1200,
                        max_retries=1,
                        request_timeout=10.0
                    )
                    response = llm_instance.invoke(prompt)
                    content = response.content
                    if isinstance(content, list):
                        text_parts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in content]
                        answer = "\n".join(text_parts)
                    else:
                        answer = str(content)
                    if answer and answer.strip():
                        break
                except Exception:
                    continue

        if not answer or not answer.strip():
            answer = "No answer found in the provided document context."

        return {
            "query": query_text,
            "answer": answer,
            "sources": retrieved_docs,
            "context_used": bool(retrieved_docs)
        }
