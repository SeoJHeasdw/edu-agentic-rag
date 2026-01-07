"""
rag-service 전용 BM25 인덱스.

의도:
- Qdrant(벡터 검색) 결과와 BM25(키워드 기반) 결과를 결합한 하이브리드 검색을 구현합니다.
- 외부 라이브러리 없이(네트워크 설치 없이) 동작하도록 최소 구현을 제공합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
import math
import re


_TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]+")


def tokenize(text: str) -> List[str]:
    """
    영문/숫자/한글 토큰을 간단히 추출합니다.
    - 실습용이므로 형태소 분석 등은 하지 않습니다.
    """

    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


@dataclass
class BM25Document:
    doc_id: str
    text: str
    payload: Dict[str, Any]


class BM25Index:
    """
    BM25 인덱스(Okapi BM25).
    - k1, b는 일반적인 기본값을 사용합니다.
    """

    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = float(k1)
        self.b = float(b)
        self._docs: List[BM25Document] = []
        self._doc_tokens: List[List[str]] = []
        self._doc_tf: List[Dict[str, int]] = []
        self._df: Dict[str, int] = {}
        self._avgdl: float = 0.0

    def __len__(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._docs = []
        self._doc_tokens = []
        self._doc_tf = []
        self._df = {}
        self._avgdl = 0.0

    def build(self, docs: Iterable[BM25Document]) -> None:
        """
        전체 문서로부터 인덱스를 새로 생성합니다.
        """

        self.clear()
        for d in docs:
            self._add_doc(d)
        self._recompute_stats()

    def upsert_many(self, docs: Iterable[BM25Document]) -> None:
        """
        문서를 인덱스에 추가합니다.
        - 단순 구현: 동일 id 중복 제거를 하지 않습니다(실습용).
          필요하면 호출 측에서 recreate 시 clear 후 build 하도록 합니다.
        """

        for d in docs:
            self._add_doc(d)
        self._recompute_stats()

    def _add_doc(self, d: BM25Document) -> None:
        toks = tokenize(d.text)
        tf: Dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        self._docs.append(d)
        self._doc_tokens.append(toks)
        self._doc_tf.append(tf)

        # df 업데이트(문서당 1회)
        seen = set(tf.keys())
        for t in seen:
            self._df[t] = self._df.get(t, 0) + 1

    def _recompute_stats(self) -> None:
        n = len(self._docs)
        if n <= 0:
            self._avgdl = 0.0
            return
        total_len = 0
        for toks in self._doc_tokens:
            total_len += len(toks)
        self._avgdl = float(total_len) / float(n)

    def _idf(self, term: str) -> float:
        """
        Okapi BM25 idf:
        idf = ln(1 + (N - df + 0.5)/(df + 0.5))
        """

        n = len(self._docs)
        df = self._df.get(term, 0)
        return math.log(1.0 + (n - df + 0.5) / (df + 0.5))

    def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        payload_filters: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        BM25로 검색하고 상위 결과를 반환합니다.

        반환 포맷:
        - id, bm25_score, payload
        """

        if not self._docs:
            return []

        q_terms = tokenize(query)
        if not q_terms:
            return []

        # 중복 제거(쿼리에서 같은 토큰이 여러 번 나와도 과도한 가중을 피함)
        q_terms = list(dict.fromkeys(q_terms))

        scores: List[Tuple[int, float]] = []
        avgdl = self._avgdl or 1.0

        for i, tf in enumerate(self._doc_tf):
            dl = len(self._doc_tokens[i]) or 1
            score = 0.0
            for t in q_terms:
                f = tf.get(t, 0)
                if f <= 0:
                    continue
                idf = self._idf(t)
                denom = f + self.k1 * (1.0 - self.b + self.b * (float(dl) / avgdl))
                score += idf * (f * (self.k1 + 1.0) / (denom if denom != 0 else 1.0))
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[: int(top_k)]

        def match_filters(payload: Dict[str, Any]) -> bool:
            """
            아주 단순한 payload 필터:
            - key="field": exact match
            - key="field__prefix": prefix match
            - key="field__contains": substring match
            - value가 list이면 any-of
            """

            if not payload_filters:
                return True
            for k, v in payload_filters.items():
                op = "eq"
                field = k
                if k.endswith("__prefix"):
                    op = "prefix"
                    field = k[: -len("__prefix")]
                elif k.endswith("__contains"):
                    op = "contains"
                    field = k[: -len("__contains")]

                pv = payload.get(field)
                # None이면 매치 실패
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

        out: List[Dict[str, Any]] = []
        for i, s in scores:
            d = self._docs[i]
            if not match_filters(d.payload):
                continue
            out.append({"id": d.doc_id, "bm25_score": float(s), "payload": d.payload})
            if len(out) >= int(top_k):
                break
        return out


