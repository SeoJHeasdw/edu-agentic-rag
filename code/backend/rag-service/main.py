from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from shared_utils import QdrantUtils, TextUtils, iter_docs_files

app = FastAPI(title="RAG Service (Qdrant)", version="1.0.0")

qdrant = QdrantUtils()


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class IndexRequest(BaseModel):
    docs_root: Optional[str] = None  # default: repo docs/
    max_files: int = 200


@app.get("/health")
async def health():
    """
    Healthcheck that verifies Qdrant connectivity.
    """
    try:
        # This will fail fast if Qdrant is not reachable
        qdrant.client().get_collections()
        return {
            "status": "ok",
            "qdrant_ok": True,
            "collection": qdrant.collection,
            "qdrant_host": qdrant.host,
            "qdrant_port": qdrant.port,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "qdrant_ok": False,
                "collection": qdrant.collection,
                "qdrant_host": qdrant.host,
                "qdrant_port": qdrant.port,
                "error": str(e),
                "hint": "Qdrant is not reachable. Start Qdrant (default http://localhost:6333) and retry.",
            },
        )


@app.post("/rag/query")
async def rag_query(req: QueryRequest):
    try:
        hits = qdrant.search(req.query, top_k=req.top_k)
        # Format for display
        out = []
        for h in hits:
            payload = h.get("payload") or {}
            text = payload.get("text", "")
            if isinstance(text, str) and len(text) > 400:
                text = text[:400] + "..."
            out.append(
                {
                    "score": h.get("score", 0.0),
                    "source": payload.get("source", ""),
                    "text": text,
                }
            )
        return {"query": req.query, "hits": out}
    except Exception as e:
        msg = str(e)
        # Common local-dev failure modes
        if "Connection refused" in msg or "Failed to establish a new connection" in msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": f"Qdrant is not running or not reachable at {qdrant.host}:{qdrant.port}. Start Qdrant and retry.",
                },
            )
        if "No embedding provider configured" in msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": "Embeddings are not configured. Set OPENAI_API_KEY (or AZURE_OPENAI_* + AZURE_EMBEDDING_DEPLOYMENT_NAME) and retry.",
                },
            )
        raise HTTPException(status_code=500, detail=msg)


@app.post("/rag/index/docs")
async def index_docs(req: IndexRequest):
    # repo root: .../code/backend/rag-service -> .../edu-agentic-rag
    repo_root = Path(__file__).resolve().parents[3]
    default_docs = repo_root / "docs"
    docs_root = Path(req.docs_root) if req.docs_root else default_docs
    if not docs_root.exists():
        raise HTTPException(status_code=400, detail=f"docs_root not found: {docs_root}")

    chunks: List[Dict[str, Any]] = []
    files = list(iter_docs_files(docs_root))
    files = files[: req.max_files]
    for fp in files:
        text = fp.read_text(encoding="utf-8", errors="ignore")
        for part in TextUtils.chunk_text(text):
            chunks.append(
                {
                    "id": uuid.uuid4().hex,
                    "text": part,
                    "source": str(fp),
                    "meta": {},
                }
            )

    if not chunks:
        return {"indexed_files": 0, "indexed_chunks": 0}

    try:
        qdrant.upsert_chunks(chunks)
        return {"indexed_files": len(files), "indexed_chunks": len(chunks), "collection": qdrant.collection}
    except Exception as e:
        msg = str(e)
        if "Connection refused" in msg or "Failed to establish a new connection" in msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": f"Qdrant is not running or not reachable at {qdrant.host}:{qdrant.port}. Start Qdrant and retry.",
                },
            )
        if "No embedding provider configured" in msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": "Embeddings are not configured. Set OPENAI_API_KEY (or AZURE_OPENAI_* + AZURE_EMBEDDING_DEPLOYMENT_NAME) and retry.",
                },
            )
        raise HTTPException(status_code=500, detail=msg)


