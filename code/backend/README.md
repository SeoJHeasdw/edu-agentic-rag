# Backend Services - Edu Agentic RAG

이 디렉토리는 Agentic RAG 실습을 위한 백엔드 서비스들을 포함합니다.

## 서비스 구조

```
backend/
├── chatbot-service/    # 기본 챗봇 서비스 (OpenAI / Azure OpenAI)
│   ├── app/           # FastAPI 애플리케이션
│   ├── config.yml     # LLM 제공자 설정
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


