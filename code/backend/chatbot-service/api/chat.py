"""
채팅 API 라우트.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models import ChatRequest, ChatResponse, ChatMessage
from services.llm_service import llm_service
from services.agent_runtime import agent_runtime
import json

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    채팅 메시지를 전송하고 응답을 반환합니다.
    """
    try:
        # messages가 있으면 ChatMessage 객체로 변환
        conversation_history = None
        if request.messages:
            conversation_history = [
                ChatMessage(role=msg["role"], content=msg["content"])
                if isinstance(msg, dict)
                else msg
                for msg in request.messages
            ]
        
        # 런타임이 LLM on/off 모두 처리합니다.
        conversation_id = request.conversation_id
        result = await agent_runtime.handle(
            message=request.message,
            conversation_id=request.conversation_id,
            conversation_history=conversation_history,
        )
        response_text = result["message"]
        meta = result.get("meta")
        # 런타임이 생성/반환한 session id(conversation_id)를 사용
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
    채팅 응답을 스트리밍(SSE)으로 반환합니다.
    """
    try:
        # messages가 있으면 ChatMessage 객체로 변환
        conversation_history = None
        if request.messages:
            conversation_history = [
                ChatMessage(role=msg["role"], content=msg["content"])
                if isinstance(msg, dict)
                else msg
                for msg in request.messages
            ]
        
        async def generate():
            def _todo_items(todo: list[str], completed_count: int):
                items = []
                for i, t in enumerate(todo):
                    items.append({"id": f"todo-{i+1}", "text": t, "completed": i < completed_count})
                return items

            def _payload(*, todo: list[str], completed_count: int, current_status: str, final_response: str | None = None, is_thinking: bool = True, is_streaming: bool = True):
                return {
                    "content": "",
                    "conversation_id": request.conversation_id,
                    "role": "assistant",
                    "breakpoints": [
                        {
                            "id": "todo-breakpoint",
                            "isTodoList": True,
                            "todoList": _todo_items(todo, completed_count),
                        }
                    ],
                    "currentStatus": current_status,
                    "currentResponse": "",
                    "finalResponse": final_response or "",
                    "isThinking": is_thinking,
                    "isStreaming": is_streaming,
                }

            async for ev in agent_runtime.stream(message=request.message, conversation_id=request.conversation_id, conversation_history=conversation_history):
                todo = ev.get("todo") or []
                completed = int(ev.get("completed") or 0)
                status = ev.get("status") or ""
                done = bool(ev.get("done"))
                final = ev.get("final")

                if done:
                    yield f"data: {json.dumps(_payload(todo=todo, completed_count=len(todo), current_status='완료', final_response=str(final or ''), is_thinking=False, is_streaming=False), ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                yield f"data: {json.dumps(_payload(todo=todo, completed_count=completed, current_status=status, is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps(_payload(todo=[], completed_count=0, current_status='완료', final_response='', is_thinking=False, is_streaming=False), ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return
        
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
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "provider": llm_service.provider
    }

