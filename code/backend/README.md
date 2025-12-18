# Backend Services - Edu Agentic RAG

이 디렉토리는 Agentic RAG 실습을 위한 백엔드 서비스들을 포함합니다.

## 공용 설정 (모든 서비스 공통)

- **환경 변수**: `backend/.env` (커밋하지 않음)
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

## 서비스 구조

```
backend/
├── .env              # (로컬) 공용 환경 변수 (커밋하지 않음)
├── .env.example      # 공용 환경 변수 예시
├── config.yml        # 공용 설정(비-시크릿)
├── chatbot-service/    # 기본 챗봇 서비스 (OpenAI / Azure OpenAI)
│   ├── api/            # API 엔드포인트
│   ├── services/       # 공통 서비스
│   ├── agents/         # 에이전트(향후)
│   ├── config.yml      # 서비스별 설정(주로 server 설정)
│   ├── requirements.txt
│   └── README.md      # 서비스별 실행 가이드
└── (추가 서비스들...) # 향후 추가될 서비스들
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
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
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

## 향후 추가 예정

- RAG Service (임베딩 및 벡터 검색)
- Agent Service (에이전트 워크플로우)
- Multi-Agent Service (멀티 에이전트 시스템)


