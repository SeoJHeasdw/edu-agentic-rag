from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import threading
import hashlib
import uuid

from shared_utils import iter_docs_files
from bm25 import BM25Document, BM25Index
from qdrant_store import RagQdrantStore
from chunking import chunk_markdown, chunk_text_fallback
from qdrant_client.http import models as qmodels

app = FastAPI(title="RAG Service (Qdrant)", version="1.0.0")

qdrant = RagQdrantStore()

# BM25 인덱스는 메모리 캐시로 유지합니다(인덱싱 시점에 갱신).
_bm25 = BM25Index()
_bm25_lock = threading.Lock()

def _cors_origins() -> list[str]:
    raw = os.getenv("RAG_CORS_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    # 개발 기본값
    return ["http://localhost:5173", "http://localhost:3000"]


# CORS (프론트엔드 /manage 에서 인덱싱 호출용)
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
    인용(citation) 표기를 위해 가능한 repo 상대 경로를 사용합니다.
    """
    try:
        return str(p.resolve().relative_to(_repo_root().resolve()))
    except Exception:
        return str(p)


def _stable_chunk_ids(*, docset: str, source: str, heading_path: str, chunk_index: int) -> tuple[str, str]:
    """
    재인덱싱 시 중복이 쌓이지 않도록 결정적(deterministic) 청크 ID들을 생성합니다.
    - point_id: Qdrant point id로 사용(반드시 UUID 또는 unsigned int여야 함)
    - chunk_id: 사람이 읽기 좋은 레거시 청크 키(디버깅/표시용)
    """

    base = f"{docset}|{source}|{heading_path}|{int(chunk_index)}"
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, base))
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:24]  # 너무 길지 않게 축약
    chunk_id = f"ch_{digest}"
    return point_id, chunk_id


def _build_chunks(*, docs_root: Path, max_files: int, docset: str) -> tuple[list[dict[str, Any]], list[Path]]:
    chunks: List[Dict[str, Any]] = []
    files = list(iter_docs_files(docs_root))
    files = files[:max_files]
    for fp in files:
        text = fp.read_text(encoding="utf-8", errors="ignore")
        source = _normalize_source(fp)
        # md 파일은 헤더/코드블록 인식 청킹을 적용합니다.
        if fp.suffix.lower() == ".md":
            md_chunks = chunk_markdown(
                text,
                chunk_size=int(os.getenv("DEFAULT_CHUNK_SIZE", "900")),
                overlap=int(os.getenv("DEFAULT_CHUNK_OVERLAP", "120")),
            )
            for idx, ch in enumerate(md_chunks):
                heading_path = str((ch.meta or {}).get("heading_path") or "")
                pid, chunk_id = _stable_chunk_ids(docset=docset, source=source, heading_path=heading_path, chunk_index=idx)
                chunks.append(
                    {
                        "id": pid,
                        "text": ch.text,
                        "source": source,
                        "meta": {"docset": docset, "chunk_index": idx, "chunk_id": chunk_id, **(ch.meta or {})},
                    }
                )
            continue

        # 그 외 텍스트는 fallback 청킹(문단 기반 + overlap)
        fb = chunk_text_fallback(
            text,
            chunk_size=int(os.getenv("DEFAULT_CHUNK_SIZE", "900")),
            overlap=int(os.getenv("DEFAULT_CHUNK_OVERLAP", "120")),
        )
        for idx, ch in enumerate(fb):
            pid, chunk_id = _stable_chunk_ids(docset=docset, source=source, heading_path="", chunk_index=idx)
            chunks.append(
                {
                    "id": pid,
                    "text": ch.text,
                    "source": source,
                    "meta": {"docset": docset, "chunk_index": idx, "chunk_id": chunk_id, **(ch.meta or {})},
                }
            )
    return chunks, files


def _maybe_auto_index(*, min_points: int = 20, max_files: int = 200) -> dict[str, Any]:
    """
    컬렉션이 비어있으면(또는 너무 적으면) repo의 docs/를 자동 인덱싱합니다(베스트 에포트).
    """
    count = qdrant.count_points()
    if count >= min_points:
        return {"auto_indexed": False, "points": count}

    repo_root = _repo_root()
    docs_root = repo_root / "docs"
    if not docs_root.exists():
        return {"auto_indexed": False, "points": count, "warning": f"docs_root not found: {docs_root}"}

    chunks, files = _build_chunks(docs_root=docs_root, max_files=max_files, docset="docs")
    if chunks:
        qdrant.upsert_chunks(chunks)
        _refresh_bm25_from_chunks(chunks)
    return {"auto_indexed": True, "points": qdrant.count_points(), "indexed_files": len(files), "indexed_chunks": len(chunks)}


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    auto_index: bool = True
    snippet_chars: int = 1200
    # 메타데이터 기반 필터(선택)
    # 예:
    # - {"docset": "qdrant_embedding_docs"}
    # - {"source__prefix": "qdrant_embedding_docs/"}
    # - {"heading_path__contains": "embedding"}
    filters: Optional[Dict[str, Any]] = None


class IndexRequest(BaseModel):
    docs_root: Optional[str] = None  # default: repo docs/
    max_files: int = 200
    recreate: bool = False
    # 같은 docset을 재인덱싱할 때 기존 docset 데이터를 먼저 삭제할지(중복 방지)
    # - recreate=True면 어차피 전체 drop이므로 의미 없음
    replace_docset: bool = True
    preview: bool = True
    preview_files: int = 20
    preview_chunks_per_file: int = 3
    preview_chars: int = 320


def _build_preview(*, chunks: list[dict[str, Any]], preview_files: int, preview_chunks_per_file: int, preview_chars: int) -> list[dict[str, Any]]:
    """
    소스 파일 단위의 간단한 프리뷰를 만듭니다:
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
    Qdrant 연결/설정 상태를 확인하는 헬스체크입니다.
    """
    try:
        # Qdrant가 죽어있으면 여기서 바로 실패합니다.
        qdrant.client().get_collections()
        has_openai_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
        has_azure_api_key = bool(os.getenv("AZURE_OPENAI_API_KEY", "").strip())
        has_azure_endpoint = bool(os.getenv("AZURE_OPENAI_ENDPOINT", "").strip())
        has_azure_embedding_deployment = bool(
            (os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME", "").strip() or os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "").strip())
        )
        has_azure = bool(has_azure_api_key and has_azure_endpoint and has_azure_embedding_deployment)
        embeddings_provider = (os.getenv("EMBEDDINGS_PROVIDER", "auto") or "auto").strip().lower()
        # 디버깅 편의를 위해(시크릿 제외) 설정을 노출합니다.
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
            "bm25_cache": {"docs": len(_bm25)},
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
                "hint": "Qdrant에 연결할 수 없습니다. Qdrant(기본 http://localhost:6333)를 실행한 뒤 다시 시도하세요.",
            },
        )


def _refresh_bm25_from_chunks(chunks: list[dict[str, Any]]) -> None:
    """
    방금 인덱싱한 청크들을 기준으로 BM25 인덱스를 새로 구성합니다.
    - 현재 구현은 '전체 재빌드' 방식입니다(교육/디버깅 친화).
    """

    docs: List[BM25Document] = []
    for ch in chunks:
        payload = {"text": ch.get("text", ""), "source": ch.get("source", ""), **(ch.get("meta") or {})}
        docs.append(BM25Document(doc_id=str(ch.get("id")), text=str(ch.get("text") or ""), payload=payload))

    with _bm25_lock:
        _bm25.build(docs)


def _ensure_bm25_from_qdrant_if_empty(*, limit: int) -> None:
    """
    BM25 캐시가 비어있을 때, Qdrant payload를 스크롤로 읽어와 BM25 인덱스를 구성합니다.
    - Qdrant에 이미 인덱싱되어 있는데, rag-service 프로세스가 재시작되면 메모리 캐시가 비므로 필요합니다.
    """

    with _bm25_lock:
        if len(_bm25) > 0:
            return

    docs: List[BM25Document] = []
    for pid, payload in qdrant.scroll_payloads(limit=int(limit)):
        text = payload.get("text", "")
        if not isinstance(text, str) or not text.strip():
            continue
        docs.append(BM25Document(doc_id=str(pid), text=text, payload=dict(payload)))

    with _bm25_lock:
        # 다시 한 번 체크(레이스 방지)
        if len(_bm25) == 0:
            _bm25.build(docs)


def _minmax_norm(scores: List[float]) -> List[float]:
    if not scores:
        return []
    mn = min(scores)
    mx = max(scores)
    if mx <= mn:
        return [0.0 for _ in scores]
    return [(s - mn) / (mx - mn) for s in scores]


def _rrf_fuse(*, vec_rank: Dict[str, int], bm_rank: Dict[str, int], alpha: float, rrf_k: int) -> Dict[str, float]:
    """
    가중 RRF(Reciprocal Rank Fusion) 점수 생성.
    score(id) = alpha/(k + rank_vec) + (1-alpha)/(k + rank_bm25)
    """

    out: Dict[str, float] = {}
    vw = float(alpha)
    bw = 1.0 - float(alpha)
    k = int(rrf_k)

    ids = set(vec_rank.keys()) | set(bm_rank.keys())
    for pid in ids:
        s = 0.0
        vr = vec_rank.get(pid)
        br = bm_rank.get(pid)
        if vr is not None:
            s += vw / (k + int(vr))
        if br is not None:
            s += bw / (k + int(br))
        out[pid] = s
    return out


def _to_qdrant_filter(filters: Optional[Dict[str, Any]]) -> Optional[qmodels.Filter]:
    """
    rag-service에서 받는 간단 필터를 Qdrant Filter로 변환합니다.
    - 현재는 exact match 중심으로만 Qdrant에 pushdown 합니다.
    - prefix/contains는 Qdrant에서 완전한 지원이 어려워 후처리(클라 측 필터)로 처리합니다.
    """

    if not filters:
        return None

    must: List[qmodels.FieldCondition] = []
    for k, v in filters.items():
        # suffix 연산자는 Qdrant pushdown에서 제외(후처리)
        if k.endswith("__prefix") or k.endswith("__contains"):
            continue

        field = k
        if isinstance(v, list):
            must.append(qmodels.FieldCondition(key=field, match=qmodels.MatchAny(any=v)))
        else:
            must.append(qmodels.FieldCondition(key=field, match=qmodels.MatchValue(value=v)))

    if not must:
        return None
    return qmodels.Filter(must=must)


def _match_filters(payload: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
    """
    BM25/벡터 결과 공통 후처리용 필터 매칭.
    `bm25.py`와 동일한 규칙을 사용합니다.
    """

    if not filters:
        return True
    for k, v in filters.items():
        op = "eq"
        field = k
        if k.endswith("__prefix"):
            op = "prefix"
            field = k[: -len("__prefix")]
        elif k.endswith("__contains"):
            op = "contains"
            field = k[: -len("__contains")]

        pv = payload.get(field)
        if pv is None:
            return False

        candidates = v if isinstance(v, list) else [v]
        ok = False
        for cand in candidates:
            if op == "eq":
                ok = pv == cand
            else:
                pv_s = str(pv)
                cand_s = str(cand)
                if op == "prefix":
                    ok = pv_s.startswith(cand_s)
                elif op == "contains":
                    ok = cand_s in pv_s
            if ok:
                break
        if not ok:
            return False
    return True


def _hybrid_search(query: str, *, top_k: int, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    하이브리드 검색(BM25 + 벡터검색) 결과를 반환합니다.

    전략:
    - 벡터 결과: top_k * VECTOR_MULT 후보
    - BM25 결과: top_k * BM25_MULT 후보
    - 후보를 합친 뒤 점수 정규화(min-max) 후 가중합으로 최종 랭킹
    - filters가 있으면:
      - 가능한 건 Qdrant query_filter로 pushdown(exact match)
      - prefix/contains는 결과 후처리로 필터링
    """

    vector_mult = int(os.getenv("HYBRID_VECTOR_MULT", "4"))
    bm25_mult = int(os.getenv("HYBRID_BM25_MULT", "4"))
    alpha = float(os.getenv("HYBRID_ALPHA", "0.6"))  # alpha=벡터 비중
    bm25_limit = int(os.getenv("BM25_SCROLL_LIMIT", "5000"))
    fusion = (os.getenv("HYBRID_FUSION", "rrf") or "rrf").strip().lower()  # rrf|minmax
    rrf_k = int(os.getenv("RRF_K", "60"))

    vector_k = max(int(top_k) * vector_mult, 20)
    bm25_k = max(int(top_k) * bm25_mult, 20)

    # BM25 캐시가 없다면 Qdrant에서 payload를 읽어와 구성합니다.
    _ensure_bm25_from_qdrant_if_empty(limit=bm25_limit)

    qf = _to_qdrant_filter(filters)
    vec_hits = qdrant.vector_search(query, top_k=vector_k, qdrant_filter=qf)
    with _bm25_lock:
        bm_hits = _bm25.search(query, top_k=bm25_k, payload_filters=filters)

    # 후보 합치기 + 랭크 수집(=RRF용)
    by_id: Dict[str, Dict[str, Any]] = {}
    vec_rank: Dict[str, int] = {}
    bm_rank: Dict[str, int] = {}

    for h in vec_hits:
        pid = str(h.get("id"))
        if pid not in vec_rank:
            vec_rank[pid] = len(vec_rank) + 1  # 1-based rank
        by_id.setdefault(pid, {"id": pid, "payload": h.get("payload") or {}, "vector_score": 0.0, "bm25_score": 0.0})
        by_id[pid]["vector_score"] = float(h.get("vector_score") or 0.0)
        # payload는 벡터 검색에서 받은 걸 우선 사용
        if h.get("payload"):
            by_id[pid]["payload"] = h.get("payload") or {}

    for h in bm_hits:
        pid = str(h.get("id"))
        if pid not in bm_rank:
            bm_rank[pid] = len(bm_rank) + 1  # 1-based rank
        by_id.setdefault(pid, {"id": pid, "payload": h.get("payload") or {}, "vector_score": 0.0, "bm25_score": 0.0})
        by_id[pid]["bm25_score"] = float(h.get("bm25_score") or 0.0)
        # payload가 비어있으면 BM25 쪽 payload로 채움
        if not (by_id[pid].get("payload") or {}).get("text") and h.get("payload"):
            by_id[pid]["payload"] = h.get("payload") or {}

    # prefix/contains 같은 후처리 필터 적용
    cands = [c for c in by_id.values() if _match_filters(c.get("payload") or {}, filters)]

    if fusion == "minmax":
        vec_scores = [float(c.get("vector_score") or 0.0) for c in cands]
        bm_scores = [float(c.get("bm25_score") or 0.0) for c in cands]
        vec_norm = _minmax_norm(vec_scores)
        bm_norm = _minmax_norm(bm_scores)

        for i, c in enumerate(cands):
            c["vector_norm"] = vec_norm[i]
            c["bm25_norm"] = bm_norm[i]
            c["score"] = alpha * vec_norm[i] + (1.0 - alpha) * bm_norm[i]
    else:
        fused = _rrf_fuse(vec_rank=vec_rank, bm_rank=bm_rank, alpha=alpha, rrf_k=rrf_k)
        for c in cands:
            pid = str(c.get("id"))
            c["vector_rank"] = vec_rank.get(pid)
            c["bm25_rank"] = bm_rank.get(pid)
            c["score"] = float(fused.get(pid, 0.0))

    cands.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    return cands[: int(top_k)]


@app.post("/rag/query")
async def rag_query(req: QueryRequest):
    try:
        auto = {"auto_indexed": False}
        if req.auto_index:
            try:
                auto = _maybe_auto_index()
            except Exception:
                auto = {"auto_indexed": False, "warning": "auto_index failed"}

        hits = _hybrid_search(req.query, top_k=req.top_k, filters=req.filters)
        # 프론트 표시용 포맷
        out = []
        for h in hits:
            payload = h.get("payload") or {}
            text = payload.get("text", "")
            if isinstance(text, str) and len(text) > int(req.snippet_chars):
                text = text[: int(req.snippet_chars)] + "..."
            out.append(
                {
                    "id": h.get("id"),
                    "score": h.get("score", 0.0),  # 하이브리드 최종 점수
                    "vector_score": h.get("vector_score", 0.0),
                    "bm25_score": h.get("bm25_score", 0.0),
                    "source": payload.get("source", ""),
                    "text": text,
                }
            )
        return {
            "query": req.query,
            "hits": out,
            "meta": {
                "collection": qdrant.collection,
                "hybrid": {
                    "alpha": float(os.getenv("HYBRID_ALPHA", "0.6")),
                    "vector_mult": int(os.getenv("HYBRID_VECTOR_MULT", "4")),
                    "bm25_mult": int(os.getenv("HYBRID_BM25_MULT", "4")),
                    "fusion": (os.getenv("HYBRID_FUSION", "rrf") or "rrf").strip().lower(),
                    "rrf_k": int(os.getenv("RRF_K", "60")),
                    "bm25_cache_docs": len(_bm25),
                    "bm25_scroll_limit": int(os.getenv("BM25_SCROLL_LIMIT", "5000")),
                    "filters": req.filters or {},
                },
                **auto,
            },
        }
    except Exception as e:
        msg = str(e)
        # 로컬 개발 환경에서 자주 보는 에러를 친절하게 가공합니다.
        if "Connection refused" in msg or "Failed to establish a new connection" in msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": f"Qdrant가 실행 중이 아니거나 {qdrant.host}:{qdrant.port} 로 접근할 수 없습니다. Qdrant를 실행한 뒤 재시도하세요.",
                },
            )
        if "No embedding provider configured" in msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": "임베딩 설정이 없습니다. OPENAI_API_KEY 또는 AZURE_OPENAI_* + AZURE_EMBEDDING_DEPLOYMENT_NAME 를 설정한 뒤 재시도하세요.",
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
            with _bm25_lock:
                _bm25.clear()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to recreate collection: {e}")

    chunks, files = _build_chunks(docs_root=docs_root, max_files=req.max_files, docset="docs")

    if not chunks:
        return {"indexed_files": 0, "indexed_chunks": 0}

    try:
        # recreate가 아니더라도 docset 단위로 교체하면 중복 인덱싱을 방지할 수 있습니다.
        if req.replace_docset and not req.recreate:
            qdrant.delete_by_filter(qmodels.Filter(must=[qmodels.FieldCondition(key="docset", match=qmodels.MatchValue(value="docs"))]))
        qdrant.upsert_chunks(chunks)
        _refresh_bm25_from_chunks(chunks)
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
                    "hint": f"Qdrant가 실행 중이 아니거나 {qdrant.host}:{qdrant.port} 로 접근할 수 없습니다. Qdrant를 실행한 뒤 재시도하세요.",
                },
            )
        if "No embedding provider configured" in msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": "임베딩 설정이 없습니다. OPENAI_API_KEY 또는 AZURE_OPENAI_* + AZURE_EMBEDDING_DEPLOYMENT_NAME 를 설정한 뒤 재시도하세요.",
                },
            )
        raise HTTPException(status_code=500, detail=msg)


@app.post("/rag/index/qdrant-embedding-docs")
async def index_qdrant_embedding_docs(req: IndexRequest):
    """
    레포 전용 편의 엔드포인트:
    - repo 루트의 `qdrant_embedding_docs/` 를 Qdrant에 인덱싱합니다.
    - 프론트엔드는 로컬 파일 경로를 직접 보내는 대신 이 엔드포인트를 호출
    """
    repo_root = _repo_root()
    docs_root = repo_root / "qdrant_embedding_docs"
    if not docs_root.exists():
        raise HTTPException(status_code=400, detail=f"docs_root not found: {docs_root}")

    if req.recreate:
        try:
            qdrant.recreate_collection()
            with _bm25_lock:
                _bm25.clear()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to recreate collection: {e}")

    chunks, files = _build_chunks(docs_root=docs_root, max_files=req.max_files, docset="qdrant_embedding_docs")
    if not chunks:
        resp: dict[str, Any] = {"indexed_files": 0, "indexed_chunks": 0, "collection": qdrant.collection}
        if req.preview:
            resp["preview"] = []
        return resp

    try:
        if req.replace_docset and not req.recreate:
            qdrant.delete_by_filter(
                qmodels.Filter(must=[qmodels.FieldCondition(key="docset", match=qmodels.MatchValue(value="qdrant_embedding_docs"))])
            )
        qdrant.upsert_chunks(chunks)
        _refresh_bm25_from_chunks(chunks)
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
                    "hint": f"Qdrant가 실행 중이 아니거나 {qdrant.host}:{qdrant.port} 로 접근할 수 없습니다. Qdrant를 실행한 뒤 재시도하세요.",
                },
            )
        if "No embedding provider configured" in msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": msg,
                    "hint": "임베딩 설정이 없습니다. OPENAI_API_KEY 또는 AZURE_OPENAI_* + AZURE_EMBEDDING_DEPLOYMENT_NAME 를 설정한 뒤 재시도하세요.",
                },
            )
        raise HTTPException(status_code=500, detail=msg)

