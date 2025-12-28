from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import os

from shared_utils import QdrantUtils, TextUtils, iter_docs_files

app = FastAPI(title="RAG Service (Qdrant)", version="1.0.0")

qdrant = QdrantUtils()

def _cors_origins() -> list[str]:
    raw = os.getenv("RAG_CORS_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    # dev-friendly defaults
    return ["http://localhost:5173", "http://localhost:3000"]


# CORS (for frontend /manage triggering indexing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _repo_root() -> Path:
    # repo root: .../code/backend/rag-service -> .../edu-agentic-rag
    return Path(__file__).resolve().parents[3]


def _normalize_source(p: Path) -> str:
    """
    Prefer stable, repo-relative paths for citations.
    """
    try:
        return str(p.resolve().relative_to(_repo_root().resolve()))
    except Exception:
        return str(p)


def _build_chunks(*, docs_root: Path, max_files: int) -> tuple[list[dict[str, Any]], list[Path]]:
    chunks: List[Dict[str, Any]] = []
    files = list(iter_docs_files(docs_root))
    files = files[:max_files]
    for fp in files:
        text = fp.read_text(encoding="utf-8", errors="ignore")
        for part in TextUtils.chunk_text(text):
            chunks.append(
                {
                    "id": uuid.uuid4().hex,
                    "text": part,
                    "source": _normalize_source(fp),
                    "meta": {},
                }
            )
    return chunks, files


def _maybe_auto_index(*, min_points: int = 20, max_files: int = 200) -> dict[str, Any]:
    """
    Ensure the collection has some data.
    If it's empty, auto-index repo docs/ once (best-effort).
    """
    count = qdrant.count_points()
    if count >= min_points:
        return {"auto_indexed": False, "points": count}

    repo_root = _repo_root()
    docs_root = repo_root / "docs"
    if not docs_root.exists():
        return {"auto_indexed": False, "points": count, "warning": f"docs_root not found: {docs_root}"}

    chunks, files = _build_chunks(docs_root=docs_root, max_files=max_files)
    if chunks:
        qdrant.upsert_chunks(chunks)
    return {"auto_indexed": True, "points": qdrant.count_points(), "indexed_files": len(files), "indexed_chunks": len(chunks)}


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    auto_index: bool = True
    snippet_chars: int = 1200


class IndexRequest(BaseModel):
    docs_root: Optional[str] = None  # default: repo docs/
    max_files: int = 200
    recreate: bool = False
    preview: bool = True
    preview_files: int = 20
    preview_chunks_per_file: int = 3
    preview_chars: int = 320


def _build_preview(*, chunks: list[dict[str, Any]], preview_files: int, preview_chunks_per_file: int, preview_chars: int) -> list[dict[str, Any]]:
    """
    Build a lightweight preview grouped by source:
    - source
    - chunk_count
    - sample_chunks: [{chars, preview}]
    """
    seen: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for ch in chunks:
        src = str(ch.get("source") or "")
        if src not in seen:
            seen[src] = []
            order.append(src)
        if len(seen[src]) < int(preview_chunks_per_file):
            text = str(ch.get("text") or "")
            prev = text[: int(preview_chars)]
            if len(text) > int(preview_chars):
                prev = prev + "..."
            seen[src].append({"chars": len(text), "preview": prev})

    out: list[dict[str, Any]] = []
    for src in order[: int(preview_files)]:
        # count is computed from original chunks list for this source
        count = 0
        for ch in chunks:
            if str(ch.get("source") or "") == src:
                count += 1
        out.append({"source": src, "chunk_count": count, "sample_chunks": seen.get(src) or []})
    return out


@app.get("/health")
async def health():
    """
    Healthcheck that verifies Qdrant connectivity.
    """
    try:
        # This will fail fast if Qdrant is not reachable
        qdrant.client().get_collections()
        has_openai_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
        has_azure_api_key = bool(os.getenv("AZURE_OPENAI_API_KEY", "").strip())
        has_azure_endpoint = bool(os.getenv("AZURE_OPENAI_ENDPOINT", "").strip())
        has_azure_embedding_deployment = bool(
            (os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME", "").strip() or os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "").strip())
        )
        has_azure = bool(has_azure_api_key and has_azure_endpoint and has_azure_embedding_deployment)
        embeddings_provider = (os.getenv("EMBEDDINGS_PROVIDER", "auto") or "auto").strip().lower()
        # Surface config (no secrets) to make debugging easy
        try:
            from shared_config import EMBEDDING_DIMENSION, EMBEDDING_MODEL, AZURE_EMBEDDING_DEPLOYMENT_NAME, QDRANT_COLLECTION
        except Exception:
            EMBEDDING_DIMENSION = qdrant.vector_size
            EMBEDDING_MODEL = ""
            AZURE_EMBEDDING_DEPLOYMENT_NAME = ""
            QDRANT_COLLECTION = qdrant.collection
        return {
            "status": "ok",
            "qdrant_ok": True,
            "collection": qdrant.collection,
            "qdrant_host": qdrant.host,
            "qdrant_port": qdrant.port,
            "embeddings_configured": bool(has_openai_key or has_azure),
            "embeddings_provider": embeddings_provider,
            "embeddings_config": {
                "has_openai_key": has_openai_key,
                "has_azure_api_key": has_azure_api_key,
                "has_azure_endpoint": has_azure_endpoint,
                "has_azure_embedding_deployment_name": has_azure_embedding_deployment,
            },
            "runtime_config": {
                "qdrant_collection": QDRANT_COLLECTION,
                "expected_vector_dim": EMBEDDING_DIMENSION,
                "embedding_model": EMBEDDING_MODEL,
                "azure_embedding_deployment": AZURE_EMBEDDING_DEPLOYMENT_NAME,
            },
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
        auto = {"auto_indexed": False}
        if req.auto_index:
            try:
                auto = _maybe_auto_index()
            except Exception:
                auto = {"auto_indexed": False, "warning": "auto_index failed"}

        hits = qdrant.search(req.query, top_k=req.top_k)
        # Format for display
        out = []
        for h in hits:
            payload = h.get("payload") or {}
            text = payload.get("text", "")
            if isinstance(text, str) and len(text) > int(req.snippet_chars):
                text = text[: int(req.snippet_chars)] + "..."
            out.append(
                {
                    "id": h.get("id"),
                    "score": h.get("score", 0.0),
                    "source": payload.get("source", ""),
                    "text": text,
                }
            )
        return {"query": req.query, "hits": out, "meta": {"collection": qdrant.collection, **auto}}
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
    repo_root = _repo_root()
    default_docs = repo_root / "docs"
    docs_root = Path(req.docs_root) if req.docs_root else default_docs
    if not docs_root.exists():
        raise HTTPException(status_code=400, detail=f"docs_root not found: {docs_root}")

    if req.recreate:
        try:
            qdrant.recreate_collection()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to recreate collection: {e}")

    chunks, files = _build_chunks(docs_root=docs_root, max_files=req.max_files)

    if not chunks:
        return {"indexed_files": 0, "indexed_chunks": 0}

    try:
        qdrant.upsert_chunks(chunks)
        resp: dict[str, Any] = {"indexed_files": len(files), "indexed_chunks": len(chunks), "collection": qdrant.collection}
        if req.preview:
            resp["preview"] = _build_preview(
                chunks=chunks,
                preview_files=req.preview_files,
                preview_chunks_per_file=req.preview_chunks_per_file,
                preview_chars=req.preview_chars,
            )
        return resp
    except Exception as e:
        msg = str(e)
        if "Can't create directory for collection" in msg or ("./storage/collections" in msg and ("Operation not permitted" in msg or "os error 1" in msg)):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": (
                        "Qdrant storage is not writable/readable. If you're using Docker Desktop on macOS, "
                        "avoid mounting Qdrant storage under Desktop/Documents unless Docker Desktop has permission. "
                        "Recommended:\n"
                        "  mkdir -p ~/.local/share/edu-agentic-rag/qdrant_storage\n"
                        "  docker run --name qdrant --rm -p 6333:6333 -p 6334:6334 "
                        "-v ~/.local/share/edu-agentic-rag/qdrant_storage:/qdrant/storage qdrant/qdrant"
                    ),
                },
            )
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


@app.post("/rag/index/qdrant-embedding-docs")
async def index_qdrant_embedding_docs(req: IndexRequest):
    """
    Convenience endpoint for this repo:
    Indexes `qdrant_embedding_docs/` at repo root into Qdrant.

    Frontend should call this instead of sending filesystem paths.
    """
    repo_root = _repo_root()
    docs_root = repo_root / "qdrant_embedding_docs"
    if not docs_root.exists():
        raise HTTPException(status_code=400, detail=f"docs_root not found: {docs_root}")

    if req.recreate:
        try:
            qdrant.recreate_collection()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to recreate collection: {e}")

    chunks, files = _build_chunks(docs_root=docs_root, max_files=req.max_files)
    if not chunks:
        resp: dict[str, Any] = {"indexed_files": 0, "indexed_chunks": 0, "collection": qdrant.collection}
        if req.preview:
            resp["preview"] = []
        return resp

    try:
        qdrant.upsert_chunks(chunks)
        resp: dict[str, Any] = {"indexed_files": len(files), "indexed_chunks": len(chunks), "collection": qdrant.collection}
        if req.preview:
            resp["preview"] = _build_preview(
                chunks=chunks,
                preview_files=req.preview_files,
                preview_chunks_per_file=req.preview_chunks_per_file,
                preview_chars=req.preview_chars,
            )
        return resp
    except Exception as e:
        msg = str(e)
        if "Can't create directory for collection" in msg or ("./storage/collections" in msg and ("Operation not permitted" in msg or "os error 1" in msg)):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": (
                        "Qdrant storage is not writable/readable. If you're using Docker Desktop on macOS, "
                        "avoid mounting Qdrant storage under Desktop/Documents unless Docker Desktop has permission. "
                        "Recommended:\n"
                        "  mkdir -p ~/.local/share/edu-agentic-rag/qdrant_storage\n"
                        "  docker run --name qdrant --rm -p 6333:6333 -p 6334:6334 "
                        "-v ~/.local/share/edu-agentic-rag/qdrant_storage:/qdrant/storage qdrant/qdrant"
                    ),
                },
            )
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

