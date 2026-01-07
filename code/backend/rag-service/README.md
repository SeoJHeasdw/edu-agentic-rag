# RAG Service (rag-service)

이 서비스는 **Qdrant**를 벡터 스토어로 사용하여 문서를 인덱싱하고, 검색 시 **BM25(키워드) + 벡터검색(임베딩)** 을 결합한 **하이브리드 검색**을 제공합니다.

핵심 포인트:
- **하이브리드 검색**: BM25 + 벡터 결과를 **RRF(Reciprocal Rank Fusion)** 로 결합(기본)
- **메타데이터 필터링**: `docset`, `source`, `heading_path` 등 payload 기반 필터 지원
- **마크다운 청킹 고도화**: 헤더/코드블록을 최대한 보존
- **재인덱싱 중복 방지**: 청크 ID를 결정적으로 생성 + (옵션) docset 단위 “교체 인덱싱”

---

### 요구사항

- **Qdrant**: 기본 `localhost:6333`
- **임베딩 설정**(둘 중 하나)
  - **OpenAI**: `OPENAI_API_KEY`
  - **Azure OpenAI**: `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_EMBEDDING_DEPLOYMENT_NAME`

---

### 로컬 실행

백엔드 런처로 함께 실행(권장):

```bash
cd code/backend
python start_services.py
```

단독 실행:

```bash
cd code/backend/rag-service
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

---

### 엔드포인트

#### `GET /health`

- Qdrant 연결, 임베딩 설정 여부, BM25 캐시 상태 등을 확인합니다.

#### `POST /rag/index/docs`

- repo의 `docs/` 디렉토리를 인덱싱합니다.

요청 바디 예시:

```json
{
  "max_files": 200,
  "recreate": false,
  "replace_docset": true,
  "preview": true
}
```

주요 필드:
- **recreate**: true면 Qdrant 컬렉션을 드랍 후 재생성(전체 초기화)
- **replace_docset**: true면 `docset="docs"` 포인트를 먼저 삭제한 뒤 upsert (재인덱싱 시 찌꺼기/중복 방지)

#### `POST /rag/index/qdrant-embedding-docs`

- repo 루트의 `qdrant_embedding_docs/` 디렉토리를 인덱싱합니다.
- `replace_docset=true`면 `docset="qdrant_embedding_docs"` 포인트를 먼저 삭제 후 upsert 합니다.

#### `POST /rag/query`

- 하이브리드 검색을 수행합니다.

요청 바디 예시:

```json
{
  "query": "qdrant embedding",
  "top_k": 5,
  "auto_index": true,
  "filters": {
    "docset": "qdrant_embedding_docs",
    "heading_path__contains": "embedding"
  }
}
```

응답의 `hits`는 대략 아래 형태입니다:
- **score**: 하이브리드 최종 점수(RRF 또는 min-max 결합)
- **vector_score / bm25_score**: 개별 점수(참고용)
- **source / text**: payload 기반 표시용

---

### 메타데이터(=payload) 구성

인덱싱 시 각 청크는 Qdrant payload에 아래를 포함합니다.
- **text**: 청크 본문
- **source**: repo 상대경로(가능한 경우)
- **docset**: `"docs"` 또는 `"qdrant_embedding_docs"`
- **heading_path**: 마크다운 헤더 경로(예: `H1 > H2 > H3`) — md 파일에 한해 생성
- **chunk_index**: 해당 파일 내 청크 순번

> 임베딩 벡터는 **text만**으로 생성하며, 메타데이터는 **payload로 별도 저장**합니다.

---

### 필터 규칙 (`/rag/query.filters`)

`filters`는 payload를 기준으로 결과를 제한합니다.

- **exact match(서버단 pushdown 가능)**:
  - `{"docset": "qdrant_embedding_docs"}`
  - `{"source": "qdrant_embedding_docs/rag.md"}`
  - 값이 배열이면 OR: `{"docset": ["docs", "qdrant_embedding_docs"]}`

- **후처리 필터(결과 합친 뒤 payload로 체크)**:
  - `{"source__prefix": "qdrant_embedding_docs/"}`
  - `{"heading_path__contains": "embedding"}`

---

### 하이브리드 검색 튜닝(환경변수)

- **HYBRID_FUSION**: `rrf`(기본) 또는 `minmax`
- **HYBRID_ALPHA**: 벡터 비중(기본 `0.6`)
- **RRF_K**: RRF의 k(기본 `60`)
- **HYBRID_VECTOR_MULT**: 벡터 후보 풀 배수(기본 `4`)
- **HYBRID_BM25_MULT**: BM25 후보 풀 배수(기본 `4`)
- **BM25_SCROLL_LIMIT**: BM25 캐시가 비었을 때 Qdrant에서 스크롤로 읽어올 최대 포인트 수(기본 `5000`)

---

### 청킹 튜닝(환경변수)

- **DEFAULT_CHUNK_SIZE**: 기본 `900`
- **DEFAULT_CHUNK_OVERLAP**: 기본 `120`

md 파일은 `chunking.py`에서 헤더/코드블록을 보존하도록 처리합니다.

---

### 재인덱싱과 중복/찌꺼기 처리

이 서비스는 재인덱싱 시 “중복이 쌓이는 문제”를 2단으로 방지합니다.

- **결정적 청크 ID**: `docset|source|heading_path|chunk_index` 기반으로 ID를 생성 → 같은 청크는 upsert로 덮어쓰기
- **docset 교체 인덱싱(replace_docset)**: 청킹 규칙 변경/문서 삭제 등으로 “더 이상 생성되지 않는 예전 청크”가 남는 것을 막기 위해, 인덱싱 전에 docset을 먼저 삭제할 수 있음

---

### 파일 구조(요약)

- `main.py`: API 엔드포인트, 인덱싱/검색 오케스트레이션
- `qdrant_store.py`: Qdrant 래퍼(업서트/검색/삭제/스크롤)
- `embeddings.py`: 임베딩 생성(OpenAI/Azure)
- `bm25.py`: BM25 인덱스/검색(실습용 경량 구현)
- `chunking.py`: 마크다운 헤더/코드블록 인식 청킹


