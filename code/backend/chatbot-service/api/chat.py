"""
Chat API routes.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models import ChatRequest, ChatResponse, ChatMessage
from services.llm_service import llm_service
from services.orchestrator import orchestrator
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
        
        # If LLM is configured, keep existing behavior; otherwise use microservice orchestrator.
        conversation_id = request.conversation_id
        if llm_service.provider in ("openai", "azure_openai"):
            response_text = llm_service.chat(message=request.message, conversation_history=conversation_history)
            meta = None
        else:
            result = await orchestrator.handle(
                message=request.message,
                conversation_id=request.conversation_id,
                conversation_history=conversation_history,
            )
            response_text = result["message"]
            meta = result.get("meta")
            # allow orchestrator to create/return a session id
            conversation_id = result.get("conversation_id") or request.conversation_id
        
        return ChatResponse(
            message=response_text,
            conversation_id=conversation_id,
            role="assistant",
            meta=meta,
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
        
        async def generate():
            # Stream by chunking the full response (works for LLM and orchestrator).
            if llm_service.provider in ("openai", "azure_openai"):
                for chunk in llm_service.stream_chat(message=request.message, conversation_history=conversation_history):
                    data = json.dumps({"content": chunk, "conversation_id": request.conversation_id, "role": "assistant"})
                    yield f"data: {data}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Orchestrator (non-stream) -> chunk
            result = await orchestrator.handle(message=request.message, conversation_history=conversation_history)
            text = result["message"]
            for i in range(0, len(text), 40):
                chunk = text[i : i + 40]
                data = json.dumps({"content": chunk, "conversation_id": request.conversation_id, "role": "assistant"})
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

