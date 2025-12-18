"""
FastAPI 애플리케이션 엔트리포인트.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import server_config
from api import chat

app = FastAPI(
    title="Edu Agentic RAG Chatbot API",
    description="OpenAI / Azure OpenAI를 지원하는 실습용 챗봇 API",
    version="1.0.0"
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat.router)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Edu Agentic RAG Chatbot API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

