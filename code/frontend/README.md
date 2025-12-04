# Frontend - Edu Agentic RAG

이 디렉토리는 Agentic RAG 실습을 위한 프론트엔드 애플리케이션을 포함합니다.

## 기술 스택

- **Vue 3** - 프론트엔드 프레임워크
- **Vite** - 빌드 도구
- **Pinia** - 상태 관리
- **Vue Router** - 라우팅
- **Tailwind CSS** - 스타일링
- **Marked** - 마크다운 파싱

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/        # Vue 컴포넌트
│   │   ├── chat/         # 채팅 관련 컴포넌트
│   │   ├── common/       # 공통 컴포넌트
│   │   └── layout/       # 레이아웃 컴포넌트
│   ├── stores/           # Pinia 스토어
│   ├── views/            # 페이지 뷰
│   ├── router/           # 라우터 설정
│   ├── styles/           # 스타일 파일
│   └── utils/            # 유틸리티 함수
├── index.html
├── package.json
└── vite.config.js
```

## 설치 및 실행

### 1. 의존성 설치

```bash
npm install
```

### 2. 개발 서버 실행

```bash
npm run dev
```

개발 서버는 기본적으로 `http://localhost:5173`에서 실행됩니다.

### 3. 빌드

```bash
npm run build
```

빌드된 파일은 `dist/` 디렉토리에 생성됩니다.

## 주요 기능

### 1. 채팅 인터페이스
- 실시간 메시지 전송 및 수신
- 마크다운 렌더링
- 메시지 히스토리 관리

### 2. Mock 채팅 데모
- AI 어시스턴트의 사고 과정 시뮬레이션
- Breakpoint 기반 응답 표시
- Todo 리스트 컴포넌트

### 3. 사이드바
- 대화 목록 관리
- 사이드바 접기/펼치기
- Knowledge/Agent 모드 전환

## 환경 변수

프로젝트 루트에 `.env` 파일을 생성하여 환경 변수를 설정할 수 있습니다:

```env
VITE_API_BASE_URL=http://localhost:8080
```

## 개발 가이드

### 컴포넌트 추가
새로운 컴포넌트는 `src/components/` 디렉토리에 추가합니다.

### 스토어 추가
새로운 Pinia 스토어는 `src/stores/` 디렉토리에 추가합니다.

### 라우트 추가
새로운 라우트는 `src/router/index.js`에 추가합니다.

## 문제 해결

### 포트 충돌
다른 포트를 사용하려면 `vite.config.js`에서 포트를 변경하거나:

```bash
npm run dev -- --port 3000
```

### 의존성 문제
`node_modules`를 삭제하고 다시 설치:

```bash
rm -rf node_modules package-lock.json
npm install
```

