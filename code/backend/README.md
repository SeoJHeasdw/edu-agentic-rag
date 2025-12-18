# Backend Services - Edu Agentic RAG

이 디렉토리는 Agentic RAG 실습을 위한 백엔드 서비스들을 포함합니다.

## 공용 설정 (모든 서비스 공통)

- **환경 변수**: `backend/.env` (커밋하지 않음)
- **환경 변수 예시**: `backend/.env.example`
- **공용 설정 파일**: `backend/config.yml` (커밋해도 안전: provider/model 등 “비-시크릿”만)
- **(실습용) 공용 의존성**: `backend/shared_requirements.txt` (백엔드 전체를 venv 1개로 실행)

권장 흐름:

```bash
cd code/backend
cp .env.example .env
# .env에 API 키/엔드포인트/디플로이먼트 이름 입력
```

실습용(권장): venv 하나로 백엔드 전체 의존성 설치

```bash
cd code/backend
python -m venv venv
source venv/bin/activate
pip install -r shared_requirements.txt
```

## 로컬 실행 (권장)

한 번에 전체 마이크로서비스를 띄우는 런처가 있습니다:

```bash
cd code/backend
python start_services.py
```

정상 기동 후 간단 점검:

```bash
cd code/backend
python smoke_test.py
```

## 서비스 목록 / 포트

`start_services.py` 기준 기본 포트는 아래와 같습니다:

- **chatbot-service**: `http://localhost:8000` (FastAPI, `/docs`)
- **weather-service**: `http://localhost:8001`
- **calendar-service**: `http://localhost:8002`
- **file-service**: `http://localhost:8003`
- **notification-service**: `http://localhost:8004`
- **rag-service**: `http://localhost:8005` (Qdrant 필요)

## 서비스 구조

```
backend/
├── .env              # (로컬) 공용 환경 변수 (커밋하지 않음)
├── .env.example      # 공용 환경 변수 예시
├── config.yml        # 공용 설정(비-시크릿)
├── shared_config.py     # 공용 설정 로더(.env 로드 포함)
├── shared_utils.py      # 공용 유틸(Qdrant/청킹/문서 로드 등)
├── shared_requirements.txt  # (실습용) 백엔드 전체 공용 의존성
├── start_services.py    # 로컬 런처(서비스 일괄 실행)
├── smoke_test.py        # 로컬 스모크 테스트(기본 HTTP/통합 체크)
├── chatbot-service/     # 챗봇/오케스트레이터 (8000)
│   ├── api/
│   ├── services/
│   ├── agents/
│   ├── config.yml
│   ├── requirements.txt
│   └── README.md
├── weather-service/     # 날씨 서비스 (8001)
├── calendar-service/    # 캘린더 서비스 (8002)
├── file-service/        # 파일 서비스 (8003)
├── notification-service/ # 알림 서비스 (8004)
└── rag-service/         # RAG(Qdrant) 서비스 (8005)
```

## 현재 서비스

### 1. Chatbot Service
- 기본 챗봇 API 제공
- OpenAI 및 Azure OpenAI 지원
- 스트리밍 응답 지원

자세한 내용은 [chatbot-service README](./chatbot-service/README.md)를 참고하세요.

### 2. RAG Service (Qdrant)
`rag-service`는 벡터 검색을 위해 **Qdrant**가 필요합니다. (기본: `localhost:6333`)

Qdrant 실행(가장 쉬운 방법: Docker):

```bash
# ✅ 권장: 레포 밖 경로에 Qdrant 데이터를 저장(용량 큼 / git에 올리면 안 됨)
mkdir -p ~/.local/share/edu-agentic-rag/qdrant_storage
docker run --name edu-qdrant --rm \
  -p 6333:6333 -p 6334:6334 \
  -v ~/.local/share/edu-agentic-rag/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

그리고 `rag-service`는 검색/인덱싱 시 임베딩이 필요하므로 다음 중 하나를 설정해야 합니다:

- `OPENAI_API_KEY`
- 또는 `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_EMBEDDING_DEPLOYMENT_NAME`

문서 인덱싱(선택, 첫 실행 시 권장):

```bash
curl -X POST http://localhost:8005/rag/index/docs \
  -H "Content-Type: application/json" \
  -d "{}"
```

## 트러블슈팅

- **포트가 이미 사용 중이라 서비스가 스킵됨**
  - `start_services.py`는 해당 포트가 점유되어 있으면 그 서비스를 “skipping” 합니다.
  - 기존에 떠 있는 프로세스를 종료하거나, 서비스 포트를 바꾸고 싶으면 `start_services.py`의 `SERVICES` 목록을 조정하세요.

- **`rag-service`가 503을 반환함**
  - 보통 **Qdrant 미기동**(기본 `localhost:6333`) 또는 **임베딩 키 미설정**입니다.
  - Qdrant 실행 후(`docker run ...`) 다시 시도하거나, `.env`에 `OPENAI_API_KEY` 또는 `AZURE_OPENAI_* + AZURE_EMBEDDING_DEPLOYMENT_NAME`를 설정하세요.


