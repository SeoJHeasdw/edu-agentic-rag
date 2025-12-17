"""
Chat models for request/response schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Chat request from frontend"""
    message: str
    conversation_id: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None  # Conversation history


class ChatResponse(BaseModel):
    """Chat response to frontend"""
    message: str
    conversation_id: Optional[str] = None
    role: str = "assistant"
    meta: Optional[Dict[str, Any]] = None

