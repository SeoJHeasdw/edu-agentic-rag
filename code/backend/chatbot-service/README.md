# Chatbot Service - Edu Agentic RAG

이 디렉토리는 기본 챗봇 서비스를 제공하는 백엔드 애플리케이션입니다.

## 상태

✅ 기본 챗봇 API 구현 완료 (OpenAI 및 Azure OpenAI 지원)

## 기술 스택

- **FastAPI** - 웹 프레임워크
- **Python 3.10+** - 프로그래밍 언어
- **OpenAI SDK** - OpenAI 및 Azure OpenAI API 통합
- **Pydantic** - 데이터 검증 및 설정 관리
- **PyYAML** - 설정 파일 관리

## 프로젝트 구조

```
chatbot-service/
├── main.py              # FastAPI 애플리케이션 엔트리 포인트
├── config.py            # 설정 관리
├── config.yml            # LLM 제공자 설정 파일
├── models.py             # 데이터 모델 (Pydantic)
│
├── api/                  # API 엔드포인트들 (플랫 구조)
│   ├── __init__.py
│   └── chat.py          # 채팅 API 엔드포인트
│
├── services/             # 공통 서비스들 (플랫 구조)
│   ├── __init__.py
│   └── llm_service.py   # LLM 서비스 (OpenAI/Azure OpenAI)
│
├── agents/                # Agent 구현들 (플랫 구조)
│   ├── __init__.py
│   ├── (향후 추가 예정)
│   │   ├── task_planner.py
│   │   ├── task_planner_mock.py
│   │   ├── intent_classifier.py
│   │   └── intent_classifier_mock.py
│
├── requirements.txt      # Python 의존성
└── README.md            # 이 파일
```

## 설치 및 실행

### 1. 가상 환경 생성

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

이 프로젝트는 **backend 공용 `.env`**를 사용합니다:

```bash
cd ../
cp .env.example .env
```

`backend/.env` 파일을 편집하여 필요한 API 키를 입력합니다:

```env
# OpenAI 사용 시
OPENAI_API_KEY=your_openai_api_key_here

# Azure OpenAI 사용 시
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

# Azure Embedding (향후 사용)
AZURE_EMBEDDING_DEPLOYMENT=oss-embedding
AZURE_EMBEDDING_MODEL=text-embedding-3-large
AZURE_EMBEDDING_SMALL_MODEL=oss-embedding-small
```

### 4. LLM 제공자 선택

LLM 제공자/모델 같은 공용 설정은 `backend/config.yml`에서 제어하는 것을 권장합니다.

서비스별 `config.yml`은 주로 **server 설정(CORS/port 등)** 용도로 두는 것을 권장합니다.

예시(backend/config.yml):

```yaml
llm:
  provider: "openai"  # "openai" 또는 "azure_openai"
```

### 5. 개발 서버 실행

```bash
uvicorn main:app --reload
```

개발 서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

API 문서는 `http://localhost:8000/docs`에서 확인할 수 있습니다.

## 주요 기능

### 1. LLM 제공자 지원
- ✅ OpenAI API 지원
- ✅ Azure OpenAI API 지원
- ✅ `backend/config.yml`을 통한 쉬운 제공자 전환(공용)

### 2. 채팅 API
- ✅ 일반 채팅 응답 (`POST /api/chat`)
- ✅ 스트리밍 채팅 응답 (`POST /api/chat/stream`)
- ✅ 대화 히스토리 지원

## API 엔드포인트

### 채팅

- `POST /api/chat` - 채팅 메시지 전송 및 응답 받기
  ```json
  {
    "message": "안녕하세요",
    "conversation_id": "optional-conversation-id",
    "messages": [
      {"role": "user", "content": "이전 메시지"},
      {"role": "assistant", "content": "이전 응답"}
    ]
  }
  ```

- `POST /api/chat/stream` - 스트리밍 채팅 응답 (Server-Sent Events)
  
- `GET /api/chat/health` - 채팅 서비스 상태 확인

### 기타

- `GET /` - API 정보
- `GET /health` - 서버 상태 확인
- `GET /docs` - Swagger API 문서

## 설정 파일 (config.yml)

`config.yml` 파일을 통해 LLM 제공자와 서버 설정을 관리할 수 있습니다:

```yaml
llm:
  provider: "openai"  # "openai" or "azure_openai"
  
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4o-mini"
    base_url: "https://api.openai.com/v1"
    temperature: 0.7
    max_tokens: 2000
    
  azure_openai:
    api_key: "${AZURE_OPENAI_API_KEY}"
    api_version: "${AZURE_OPENAI_API_VERSION:-2024-12-01-preview}"
    endpoint: "${AZURE_OPENAI_ENDPOINT}"
    deployment_name: "${AZURE_OPENAI_DEPLOYMENT_NAME}"
    temperature: 0.7
    max_tokens: 2000

server:
  host: "0.0.0.0"
  port: 8000
  cors_origins:
    - "http://localhost:5173"
    - "http://localhost:3000"
```

## 환경 변수

`.env` 파일을 생성하여 환경 변수를 설정:

```env
# OpenAI 사용 시
OPENAI_API_KEY=your_api_key

# Azure OpenAI 사용 시
AZURE_OPENAI_API_KEY=your_azure_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

# Azure Embedding (향후 사용)
AZURE_EMBEDDING_DEPLOYMENT=oss-embedding
AZURE_EMBEDDING_MODEL=text-embedding-3-large
AZURE_EMBEDDING_SMALL_MODEL=oss-embedding-small
```

## 프론트엔드 연결

프론트엔드는 `http://localhost:5173`에서 실행되며, 백엔드는 `http://localhost:8000`에서 실행됩니다.

CORS 설정은 `config.yml`의 `server.cors_origins`에서 관리됩니다.

## 개발 가이드

### LLM 제공자 전환

1. `config.yml`에서 `llm.provider` 값을 변경
2. 해당 제공자의 환경 변수가 `.env`에 설정되어 있는지 확인
3. 서버 재시작

### 새로운 LLM 제공자 추가

1. `app/services/llm_service.py`에 새로운 제공자 로직 추가
2. `app/config.py`에 설정 추가
3. `config.yml`에 설정 항목 추가

