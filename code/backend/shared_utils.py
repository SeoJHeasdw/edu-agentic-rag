"""
Backend shared utils (module at backend root).

Replaces `backend/shared/utils.py` but removes Chroma + heavy deps.
Provides:
- Text chunking
- Embeddings (OpenAI or Azure OpenAI embeddings)
- Qdrant indexing + search helpers
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import os
import re

import httpx
from openai import OpenAI, AzureOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from shared_config import (
    OPENAI_API_KEY,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    AZURE_EMBEDDING_DEPLOYMENT_NAME,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
)


_TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]+")


class TextUtils:
    @staticmethod
    def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
        # paragraph-first chunking with soft limit
        parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: List[str] = []
        buf = ""
        for p in parts:
            if not buf:
                buf = p
                continue
            if len(buf) + 2 + len(p) <= chunk_size:
                buf = f"{buf}\n\n{p}"
            else:
                chunks.append(buf)
                buf = p
        if buf:
            chunks.append(buf)

        # add overlap by simple tail prefix (character overlap)
        if overlap <= 0 or len(chunks) <= 1:
            return chunks
        out: List[str] = []
        prev_tail = ""
        for c in chunks:
            if prev_tail:
                out.append(prev_tail + c)
            else:
                out.append(c)
            prev_tail = c[-overlap:] if len(c) > overlap else c
        return out

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return [t.lower() for t in _TOKEN_RE.findall(text)]


class EmbeddingUtils:
    @staticmethod
    def _client():
        """
        Returns (provider, client) for embeddings.

        Teaching-friendly behavior:
        - If you pick OpenAI, we ONLY use OpenAI (no fallback).
        - If you pick Azure, we ONLY use Azure (no fallback).

        Control via env:
        - EMBEDDINGS_PROVIDER=openai|azure|auto (default: auto)
          - auto keeps prior behavior: OpenAI if OPENAI_API_KEY exists, else Azure if configured
        """
        pref = (os.getenv("EMBEDDINGS_PROVIDER", "auto") or "auto").strip().lower()

        def openai_client():
            if not OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not set (required for EMBEDDINGS_PROVIDER=openai).")
            no_ssl = httpx.Client(verify=bool(os.getenv("SSL_VERIFY", "true").lower() == "true"))
            return ("openai", OpenAI(api_key=OPENAI_API_KEY, http_client=no_ssl))

        def azure_client():
            if not (AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_EMBEDDING_DEPLOYMENT_NAME):
                raise RuntimeError(
                    "Azure embeddings are not configured (required for EMBEDDINGS_PROVIDER=azure). "
                    "Need AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_EMBEDDING_DEPLOYMENT_NAME."
                )
            return (
                "azure",
                AzureOpenAI(
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version=AZURE_OPENAI_API_VERSION,
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                ),
            )

        if pref == "openai":
            return openai_client()
        if pref == "azure":
            return azure_client()

        # auto
        if OPENAI_API_KEY:
            return openai_client()
        if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_EMBEDDING_DEPLOYMENT_NAME:
            return azure_client()
        raise RuntimeError(
            "No embedding provider configured. Set OPENAI_API_KEY or Azure embedding env vars "
            "(AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_EMBEDDING_DEPLOYMENT_NAME)."
        )

    @staticmethod
    def embed(texts: List[str]) -> List[List[float]]:
        provider, client = EmbeddingUtils._client()
        cleaned = [t.replace("\n", " ") for t in texts]
        if provider == "openai":
            res = client.embeddings.create(model=EMBEDDING_MODEL, input=cleaned)
            return [d.embedding for d in res.data]
        # azure
        res = client.embeddings.create(model=AZURE_EMBEDDING_DEPLOYMENT_NAME, input=cleaned)
        return [d.embedding for d in res.data]


@dataclass
class QdrantUtils:
    host: str = QDRANT_HOST
    port: int = QDRANT_PORT
    collection: str = QDRANT_COLLECTION
    vector_size: int = EMBEDDING_DIMENSION

    def client(self) -> QdrantClient:
        return QdrantClient(host=self.host, port=self.port)

    def ensure_collection(self) -> None:
        c = self.client()
        existing = {col.name for col in c.get_collections().collections}
        if self.collection in existing:
            # Validate vector size to avoid confusing 400 errors later.
            try:
                info = c.get_collection(collection_name=self.collection)
                cfg = getattr(info, "config", None)
                params = getattr(cfg, "params", None) if cfg else None
                vectors = getattr(params, "vectors", None) if params else None
                size = getattr(vectors, "size", None) if vectors else None
                if size is not None and int(size) != int(self.vector_size):
                    raise RuntimeError(
                        f"Qdrant collection '{self.collection}' vector size mismatch: expected {self.vector_size}, got {size}. "
                        "Recreate the collection or align EMBEDDING_DIMENSION/embedding deployment."
                    )
            except Exception as e:
                # Surface a clear error to callers (index/query) instead of a raw Qdrant 400.
                raise RuntimeError(str(e))
            return
        try:
            c.create_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(size=self.vector_size, distance=qmodels.Distance.COSINE),
            )
        except Exception as e:
            msg = str(e)
            # Common Docker Desktop / bind-mount failure modes end up as filesystem errors inside Qdrant.
            # When storage is not writable/readable, Qdrant may leave behind partial folders which then cause:
            # - "Can't create directory for collection ... File exists"
            # - "Operation not permitted" touching ./storage/collections/...
            if (
                "Can't create directory for collection" in msg
                or ("./storage/collections" in msg and ("Operation not permitted" in msg or "os error 1" in msg))
            ):
                raise RuntimeError(
                    f"{msg}\n"
                    "Hint: Qdrant storage is not writable/readable. If you're using Docker on macOS, avoid mounting "
                    "Qdrant storage under Desktop/Documents unless Docker Desktop has permission. Recommended:\n"
                    "  mkdir -p ~/.local/share/edu-agentic-rag/qdrant_storage\n"
                    "  docker run --name qdrant --rm -p 6333:6333 -p 6334:6334 "
                    "-v ~/.local/share/edu-agentic-rag/qdrant_storage:/qdrant/storage qdrant/qdrant"
                ) from e
            raise

    def count_points(self) -> int:
        """
        Returns number of points in the collection.
        Ensures the collection exists first.
        """
        self.ensure_collection()
        try:
            res = self.client().count(collection_name=self.collection, exact=True)
            return int(getattr(res, "count", 0) or 0)
        except Exception:
            return 0

    def recreate_collection(self) -> None:
        """
        Drops and recreates the collection.
        """
        c = self.client()
        try:
            c.delete_collection(collection_name=self.collection)
        except Exception:
            pass
        c.create_collection(
            collection_name=self.collection,
            vectors_config=qmodels.VectorParams(size=self.vector_size, distance=qmodels.Distance.COSINE),
        )

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        chunks item schema:
          - id: str|int
          - text: str
          - source: str
          - meta: dict (optional)
        """
        self.ensure_collection()
        texts = [c["text"] for c in chunks]
        vectors = EmbeddingUtils.embed(texts)

        points: List[qmodels.PointStruct] = []
        for i, ch in enumerate(chunks):
            payload = {"text": ch["text"], "source": ch.get("source", ""), **(ch.get("meta") or {})}
            points.append(qmodels.PointStruct(id=ch["id"], vector=vectors[i], payload=payload))

        self.client().upsert(collection_name=self.collection, points=points)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        self.ensure_collection()
        q_vec = EmbeddingUtils.embed([query])[0]
        hits = self.client().search(collection_name=self.collection, query_vector=q_vec, limit=top_k, with_payload=True)
        out: List[Dict[str, Any]] = []
        for h in hits:
            out.append(
                {
                    "id": h.id,
                    "score": float(h.score),
                    "payload": h.payload or {},
                }
            )
        return out


def iter_docs_files(docs_root: Path, exts: Tuple[str, ...] = (".md", ".txt")) -> Iterable[Path]:
    for p in docs_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


