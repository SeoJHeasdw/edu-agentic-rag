# Backend - Edu Agentic RAG

이 디렉토리는 Agentic RAG 실습을 위한 백엔드 애플리케이션을 포함합니다.

## 상태

현재 백엔드는 구현 예정입니다.

## 예상 기술 스택

- **FastAPI** - 웹 프레임워크
- **Python 3.10+** - 프로그래밍 언어
- **LangChain** - LLM 통합 프레임워크
- **Vector Store** - 임베딩 벡터 저장소 (예: Chroma, Pinecone)
- **LLM API** - OpenAI, Anthropic 등

## 예상 프로젝트 구조

```
backend/
├── app/
│   ├── main.py           # FastAPI 애플리케이션 엔트리 포인트
│   ├── models/           # 데이터 모델
│   ├── services/         # 비즈니스 로직
│   │   ├── rag.py        # RAG 서비스
│   │   └── agent.py      # Agent 서비스
│   ├── api/              # API 라우터
│   └── utils/            # 유틸리티 함수
├── requirements.txt      # Python 의존성
└── README.md            # 이 파일
```

## 설치 및 실행 (예정)

### 1. 가상 환경 생성

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 개발 서버 실행

```bash
uvicorn app.main:app --reload
```

개발 서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

## 주요 기능 (예정)

### 1. RAG 시스템
- 문서 임베딩 및 벡터 저장
- 검색 기반 문서 검색
- LLM을 통한 응답 생성

### 2. Agent 시스템
- 작업 계획 수립
- 도구 사용 및 실행
- 결과 평가 및 반복

### 3. Agentic RAG
- RAG와 Agent의 통합
- 동적 검색 전략
- 멀티 스텝 추론

## API 엔드포인트 (예정)

- `POST /api/chat` - 채팅 메시지 전송
- `POST /api/upload` - 문서 업로드
- `GET /api/conversations` - 대화 목록 조회
- `GET /api/conversations/{id}` - 특정 대화 조회

## 환경 변수

`.env` 파일을 생성하여 환경 변수를 설정:

```env
OPENAI_API_KEY=your_api_key
VECTOR_STORE_TYPE=chroma
DATABASE_URL=sqlite:///./rag.db
```

## 개발 가이드

백엔드 구현이 시작되면 이 섹션이 업데이트됩니다.

