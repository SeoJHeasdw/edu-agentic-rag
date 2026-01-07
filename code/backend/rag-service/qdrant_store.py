"""
rag-service 전용 Qdrant 스토어 래퍼.

여기서는:
- Qdrant 컬렉션 생성/검증
- 청크 upsert(임베딩은 `embeddings.py` 사용)
- 벡터 검색, 스크롤(=BM25 인덱스 구축용) 기능을 제공합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from shared_config import (
    EMBEDDING_DIMENSION,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
)

from embeddings import embed_texts


@dataclass
class RagQdrantStore:
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
            # 벡터 차원 불일치(설정 변경 등)를 빠르게 알려줍니다.
            info = c.get_collection(collection_name=self.collection)
            cfg = getattr(info, "config", None)
            params = getattr(cfg, "params", None) if cfg else None
            vectors = getattr(params, "vectors", None) if params else None
            size = getattr(vectors, "size", None) if vectors else None
            if size is not None and int(size) != int(self.vector_size):
                raise RuntimeError(
                    f"Qdrant 컬렉션 '{self.collection}' 벡터 차원 불일치: expected={self.vector_size}, got={size}. "
                    "컬렉션을 recreate 하거나 EMBEDDING_DIMENSION/배포 모델을 맞추세요."
                )
            return

        c.create_collection(
            collection_name=self.collection,
            vectors_config=qmodels.VectorParams(size=self.vector_size, distance=qmodels.Distance.COSINE),
        )

    def count_points(self) -> int:
        self.ensure_collection()
        try:
            res = self.client().count(collection_name=self.collection, exact=True)
            return int(getattr(res, "count", 0) or 0)
        except Exception:
            return 0

    def recreate_collection(self) -> None:
        c = self.client()
        try:
            c.delete_collection(collection_name=self.collection)
        except Exception:
            pass
        c.create_collection(
            collection_name=self.collection,
            vectors_config=qmodels.VectorParams(size=self.vector_size, distance=qmodels.Distance.COSINE),
        )

    def delete_by_filter(self, qdrant_filter: qmodels.Filter) -> None:
        """
        필터 조건에 해당하는 point들을 삭제합니다.
        - 재인덱싱 시 같은 docset/source를 '교체'하고 싶을 때 사용합니다.
        """

        self.ensure_collection()
        self.client().delete(
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(filter=qdrant_filter),
        )

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        chunks 스키마:
        - id: str|int
        - text: str
        - source: str
        - meta: dict (optional)
        """

        self.ensure_collection()
        texts = [str(c.get("text") or "") for c in chunks]
        vectors = embed_texts(texts)

        points: List[qmodels.PointStruct] = []
        for i, ch in enumerate(chunks):
            payload = {"text": ch.get("text", ""), "source": ch.get("source", ""), **(ch.get("meta") or {})}
            points.append(qmodels.PointStruct(id=ch["id"], vector=vectors[i], payload=payload))

        self.client().upsert(collection_name=self.collection, points=points)

    def vector_search(
        self,
        query: str,
        *,
        top_k: int = 10,
        qdrant_filter: Optional[qmodels.Filter] = None,
    ) -> List[Dict[str, Any]]:
        """
        Qdrant 벡터 검색 결과를 반환합니다.
        반환: [{id, vector_score, payload}]
        """

        self.ensure_collection()
        q_vec = embed_texts([query])[0]
        hits = self.client().search(
            collection_name=self.collection,
            query_vector=q_vec,
            limit=int(top_k),
            with_payload=True,
            query_filter=qdrant_filter,
        )

        out: List[Dict[str, Any]] = []
        for h in hits:
            out.append({"id": str(h.id), "vector_score": float(h.score), "payload": h.payload or {}})
        return out

    def scroll_payloads(self, *, limit: int = 5000) -> Iterable[Tuple[str, Dict[str, Any]]]:
        """
        컬렉션의 point payload를 스크롤로 가져옵니다.
        - BM25 인덱스 구축용(텍스트 전체 스캔)으로 사용합니다.
        - limit 만큼만 가져옵니다(안전장치).
        """

        self.ensure_collection()
        c = self.client()

        fetched = 0
        offset: Optional[qmodels.PointId] = None
        while fetched < int(limit):
            batch_limit = min(256, int(limit) - fetched)
            points, next_offset = c.scroll(
                collection_name=self.collection,
                limit=batch_limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not points:
                break

            for p in points:
                payload = p.payload or {}
                yield (str(p.id), payload)
                fetched += 1
                if fetched >= int(limit):
                    break

            if next_offset is None:
                break
            offset = next_offset


