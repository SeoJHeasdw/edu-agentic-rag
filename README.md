# Edu Agentic RAG

Agentic RAG(Retrieval-Augmented Generation)에 대한 이론과 실습을 통합한 교육용 프로젝트입니다.

## 📚 프로젝트 개요

이 프로젝트는 AI 에이전트의 개념부터 RAG 시스템의 작동 원리, 그리고 이 둘을 결합한 Agentic RAG 및 Multi-Agent 시스템에 대한 이론적 내용과 실습 코드를 제공합니다.

### 학습 목표

- RAG(Retrieval-Augmented Generation)의 기본 개념 이해
- AI Agent의 작동 원리와 구조 학습
- Agentic RAG 시스템 설계 및 구현
- Multi-Agent 시스템 구축 방법 습득

## 📁 프로젝트 구조

```
edu-agentic-rag/
├── README.md              # 프로젝트 전체 소개 및 실행 가이드
├── docs/                  # 이론 자료
│   ├── Agentic_RAG_Basic.md
│   └── lecture_outline.md
├── code/                  # 실습 코드 모음
│   ├── frontend/          # 프론트엔드 소스 (Vue 3)
│   │   ├── src/
│   │   │   ├── config/    # API 설정
│   │   │   ├── utils/     # API 유틸리티
│   │   │   └── stores/    # 상태 관리
│   │   ├── package.json
│   │   └── README.md      # 프론트 실행법
│   └── backend/           # 백엔드 서비스들
│       └── chatbot-service/  # 챗봇 서비스
│           ├── app/          # FastAPI 앱
│           ├── config.yml    # LLM 제공자 설정
│           ├── requirements.txt
│           └── README.md     # 서비스 실행법
├── (Docker 미사용)        # 로컬 실행 스크립트 사용
└── .gitignore             # 전체 공통 제외 파일 설정
```

## 🚀 빠른 시작

### 전체 시스템 실행 (로컬)

백엔드는 Python 런처로 한 번에 띄울 수 있습니다:

```bash
cd code/backend
python start_services.py
```

### 개별 실행

#### 프론트엔드 실행

```bash
cd code/frontend
npm install
npm run dev
```

프론트엔드는 `http://localhost:5173`에서 실행됩니다.

자세한 내용은 [프론트엔드 README](code/frontend/README.md)를 참고하세요.

#### 백엔드 실행 (Chatbot Service)

```bash
cd code/backend/chatbot-service
pip install -r requirements.txt

# 환경 변수 설정 (.env 파일 생성)
cp .env.example .env
# .env 파일을 편집하여 API 키 설정

# 개발 서버 실행
python -m uvicorn app.main:app --reload
```

백엔드는 `http://localhost:8000`에서 실행됩니다.

자세한 내용은 [Chatbot Service README](code/backend/chatbot-service/README.md)를 참고하세요.

## 📖 학습 경로

### 1단계: 이론 학습
`docs/` 디렉토리의 이론 자료를 순서대로 학습합니다:

1. **01_intro.md** - Agentic RAG 소개
2. **02_rag_concept.md** - RAG 개념 이해
3. (추가 이론 자료...)

### 2단계: 실습 코드 분석
`code/` 디렉토리의 실습 코드를 분석하고 실행해봅니다:

- **프론트엔드**: Vue 3 기반 채팅 인터페이스
- **백엔드**: FastAPI 기반 챗봇 API (OpenAI / Azure OpenAI 지원)

### 3단계: 직접 구현
이론과 실습 코드를 바탕으로 자신만의 Agentic RAG 시스템을 구현합니다.

## 🛠 기술 스택

### 프론트엔드
- Vue 3 (Composition API)
- Vite
- Pinia (상태 관리)
- Vue Router
- Tailwind CSS

### 백엔드
- ✅ FastAPI
- ✅ Python 3.10+
- ✅ OpenAI / Azure OpenAI 지원
- ✅ config.yml을 통한 LLM 제공자 전환

## 📝 주요 기능

### 프론트엔드
- ✅ 실시간 채팅 인터페이스
- ✅ Mock AI 어시스턴트 데모
- ✅ 메시지 히스토리 관리
- ✅ 마크다운 렌더링
- ✅ 반응형 디자인

### 백엔드
- ✅ 기본 챗봇 API 구현
- ✅ OpenAI / Azure OpenAI 통합
- ✅ 스트리밍 응답 지원
- ✅ 대화 히스토리 관리
- 🔄 RAG 시스템 구현 (예정)
- 🔄 Vector Store 연동 (예정)
- 🔄 Agent 워크플로우 (예정)

## 🎯 실습 목표

각 실습을 통해 다음을 학습할 수 있습니다:

1. **RAG 기본 구현**: 문서 검색 및 생성 파이프라인 구축
2. **Agent 구조**: AI 에이전트의 의사결정 프로세스 이해
3. **Agentic RAG**: RAG와 Agent를 결합한 시스템 설계
4. **Multi-Agent**: 여러 에이전트 간 협업 시스템 구축

## 📚 참고 자료

- [LangChain 공식 문서](https://python.langchain.com/)
- [LlamaIndex 공식 문서](https://www.llamaindex.ai/)
- [Vue 3 공식 문서](https://vuejs.org/)

## 🤝 기여

이 프로젝트는 교육용 자료입니다. 개선 사항이나 버그 리포트는 이슈로 등록해주세요.

## 📄 라이선스

이 프로젝트는 교육 목적으로 자유롭게 사용할 수 있습니다.

## 🔗 관련 링크

- 이론 자료: `docs/` 디렉토리
- 프론트엔드 코드: `code/frontend/` 디렉토리
- 백엔드 코드: `code/backend/` 디렉토리

---

**시작하기**: [프론트엔드 README](code/frontend/README.md)를 확인하여 첫 번째 실습을 시작하세요!
