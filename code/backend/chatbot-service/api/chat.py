"""
Chat API routes.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models import ChatRequest, ChatResponse, ChatMessage
from services.llm_service import llm_service
import json

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat message and get a response.
    """
    try:
        # Convert messages to ChatMessage objects if provided
        conversation_history = None
        if request.messages:
            conversation_history = [
                ChatMessage(role=msg["role"], content=msg["content"])
                if isinstance(msg, dict)
                else msg
                for msg in request.messages
            ]
        
        # Get response from LLM
        response_text = llm_service.chat(
            message=request.message,
            conversation_history=conversation_history
        )
        
        return ChatResponse(
            message=response_text,
            conversation_id=request.conversation_id,
            role="assistant"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream a chat response.
    """
    try:
        # Convert messages to ChatMessage objects if provided
        conversation_history = None
        if request.messages:
            conversation_history = [
                ChatMessage(role=msg["role"], content=msg["content"])
                if isinstance(msg, dict)
                else msg
                for msg in request.messages
            ]
        
        def generate():
            for chunk in llm_service.stream_chat(
                message=request.message,
                conversation_history=conversation_history
            ):
                # Format as SSE (Server-Sent Events)
                data = json.dumps({
                    "content": chunk,
                    "conversation_id": request.conversation_id,
                    "role": "assistant"
                })
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "provider": llm_service.provider
    }

