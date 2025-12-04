# Agentic RAG 강의 개요

## 1. 대략적인 강의 구성안 (총 약 2.5시간 / 5개 챕터)

※ 픽스된 상태는 아니며, MCP 등도 고려하고 있습니다.

Chapter 1 : RAG & Agent 기초 이해 (50-60분)
 - RAG(Retrieval-Augmented Generation)의 개념과 실무 활용 사례
 - AI Agent의 정의, 자율성, 그리고 의사결정 메커니즘
 - 기존 RAG의 한계점과 Agentic RAG의 필요성
 - LLM의 제약사항과 외부 지식 활용의 중요성

Chapter 2 : 기본 RAG 시스템 구현 (20-30분)
 - Vector DB(Qdrant)를 활용한 문서 임베딩(OpenAI에서 제공하는 text-embedding-3-small 모델) 및 검색 (코드 리뷰)
 - 기본 RAG 파이프라인 구현 및 실행 시연

Chapter 3 : Agentic RAG로의 전환 (20-25분)
 - Tool-using Agent 설계 패턴
 - ReAct (Reasoning + Acting) 패러다임
 - Multi-Agent 협업 아키텍처 개요

Chapter 4 : Agentic RAG 실전 구현 (35-40분)
 - 사전에 작성된 Agent 코드 리뷰
 - 동적 검색 전략 및 자율적 의사결정 로직
 - 실행 시연 : 복잡한 질의응답 처리 과정

Chapter 5 : 실전 활용 및 최적화 (15-20분)
 - 성능 최적화 및 LLM 토큰 비용 관리 전략
 - 향후 학습 방향 및 고급편 소개

---

## 2. 후속 강의 제안

첫 강의가 성공적으로 진행된다면, "Agentic RAG 고급편 - 메모리 시스템과 Graph DB 활용"을 후속 강의로 제안드립니다.

- **Mem0 등 메모리 시스템을 활용한 컨텍스트 유지 및 개인화**
- **Graph DB를 활용한 지식 그래프 구축 및 고급 검색**
- **엔터프라이즈급 Agentic RAG 시스템 설계**

기초편과 고급편을 시리즈로 구성하여 학습자들이 단계적으로 실력을 쌓을 수 있도록 하면 좋을 것 같습니다.

---

촬영 전까지 교안 완성 후 검토 요청드리겠으며, 필요시 사전 미팅 요청드리겠습니다.
