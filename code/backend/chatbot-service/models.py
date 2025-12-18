"""
채팅 API 요청/응답 스키마(Pydantic 모델).
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatMessage(BaseModel):
    """단일 채팅 메시지"""
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    """프론트엔드 → 백엔드 요청"""
    message: str
    conversation_id: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None  # 대화 히스토리


class ChatResponse(BaseModel):
    """백엔드 → 프론트엔드 응답"""
    message: str
    conversation_id: Optional[str] = None
    role: str = "assistant"
    meta: Optional[Dict[str, Any]] = None

