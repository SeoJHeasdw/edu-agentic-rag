# Backend Services - Edu Agentic RAG

이 디렉토리는 Agentic RAG 실습을 위한 백엔드 서비스들을 포함합니다.

## 공용 설정 (모든 서비스 공통)

- **환경 변수**: `backend/.env` (커밋하지 않음)
- **공용 설정 파일**: `backend/config.yml` (커밋해도 안전: provider/model 등 “비-시크릿”만)

권장 흐름:

```bash
cd code/backend
cp .env.example .env
# .env에 API 키/엔드포인트/디플로이먼트 이름 입력
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

## 향후 추가 예정

- RAG Service (임베딩 및 벡터 검색)
- Agent Service (에이전트 워크플로우)
- Multi-Agent Service (멀티 에이전트 시스템)


