"""
rag-service 전용 임베딩 유틸.

- 다른 서비스에 영향 없이(rag-service만) 임베딩 구현을 분리하기 위해 만든 모듈입니다.
- OpenAI / Azure OpenAI 임베딩을 동일한 인터페이스로 제공합니다.
"""

from __future__ import annotations

from typing import List, Tuple
import os

import httpx
from openai import OpenAI, AzureOpenAI

from shared_config import (
    OPENAI_API_KEY,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    EMBEDDING_MODEL,
    AZURE_EMBEDDING_DEPLOYMENT_NAME,
)


def _get_embedding_client() -> Tuple[str, object]:
    """
    임베딩 클라이언트를 선택합니다.

    - EMBEDDINGS_PROVIDER=openai|azure|auto (기본: auto)
      - openai: OPENAI_API_KEY 필수
      - azure: AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_EMBEDDING_DEPLOYMENT_NAME 필수
      - auto: OpenAI 우선, 없으면 Azure
    """

    pref = (os.getenv("EMBEDDINGS_PROVIDER", "auto") or "auto").strip().lower()

    def openai_client() -> Tuple[str, object]:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 가 설정되어 있지 않습니다. (EMBEDDINGS_PROVIDER=openai)")
        # 로컬 실습 환경에서 SSL 검증 이슈가 있을 수 있어 옵션 제공
        no_ssl = httpx.Client(verify=bool(os.getenv("SSL_VERIFY", "true").lower() == "true"))
        return ("openai", OpenAI(api_key=OPENAI_API_KEY, http_client=no_ssl))

    def azure_client() -> Tuple[str, object]:
        if not (AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_EMBEDDING_DEPLOYMENT_NAME):
            raise RuntimeError(
                "Azure 임베딩 설정이 부족합니다. (EMBEDDINGS_PROVIDER=azure)\n"
                "필요: AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_EMBEDDING_DEPLOYMENT_NAME"
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
        "임베딩 제공자가 설정되어 있지 않습니다. OPENAI_API_KEY 또는 "
        "AZURE_OPENAI_* + AZURE_EMBEDDING_DEPLOYMENT_NAME 를 설정하세요."
    )


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    텍스트 리스트를 임베딩 벡터 리스트로 변환합니다.
    """

    provider, client = _get_embedding_client()
    cleaned = [t.replace("\n", " ") for t in texts]

    if provider == "openai":
        res = client.embeddings.create(model=EMBEDDING_MODEL, input=cleaned)  # type: ignore[attr-defined]
        return [d.embedding for d in res.data]

    # azure
    res = client.embeddings.create(model=AZURE_EMBEDDING_DEPLOYMENT_NAME, input=cleaned)  # type: ignore[attr-defined]
    return [d.embedding for d in res.data]


if __name__ == "__main__":
    # 간단 테스트용: `python embeddings.py "문장1" "문장2"`
    import sys

    texts = [t for t in sys.argv[1:] if t.strip()]
    if not texts:
        print("사용법: python embeddings.py \"텍스트1\" \"텍스트2\" ...")
        raise SystemExit(2)

    vecs = embed_texts(texts)
    print(f"입력 {len(texts)}개 -> 벡터 {len(vecs)}개 (dim={len(vecs[0]) if vecs else 0})")


