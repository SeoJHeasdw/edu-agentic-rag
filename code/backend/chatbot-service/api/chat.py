"""
Chat API routes.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models import ChatRequest, ChatResponse, ChatMessage
from services.llm_service import llm_service
from services.orchestrator import (
    orchestrator,
    _extract_city,
    _extract_time,
    infer_intent,
)
from agents.intent_classifier import IntentClassifier
from agents.task_planner import TaskPlannerAgent
import json
import httpx

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

            # Orchestrator (structured stream): emit To-Do list + step completion
            classifier = IntentClassifier()
            analysis = classifier.analyze_intent(request.message, context=None)
            intent = analysis.get("intent", infer_intent(request.message))
            planner = TaskPlannerAgent()
            plan = planner.plan(user_input=request.message, analysis=analysis)
            tasks = plan.get("tasks") or []

            def _todo_items(completed_count: int):
                items = []
                for i, t in enumerate(tasks):
                    items.append({"id": f"todo-{i+1}", "text": t, "completed": i < completed_count})
                return items

            def _payload(*, completed_count: int, current_status: str, final_response: str | None = None, is_thinking: bool = True, is_streaming: bool = True):
                return {
                    "content": "",
                    "conversation_id": request.conversation_id,
                    "role": "assistant",
                    "breakpoints": [
                        {
                            "id": "todo-breakpoint",
                            "isTodoList": True,
                            "todoList": _todo_items(completed_count),
                        }
                    ],
                    "currentStatus": current_status,
                    "currentResponse": "",
                    "finalResponse": final_response or "",
                    "isThinking": is_thinking,
                    "isStreaming": is_streaming,
                }

            # 0) initial plan
            yield f"data: {json.dumps(_payload(completed_count=0, current_status='계획 수립 중...', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

            # 1) intent classified (의도분류는 To-Do에 포함하지 않음: planner 이전 단계이기 때문)
            completed = 0
            yield f"data: {json.dumps(_payload(completed_count=completed, current_status='의도 분석 완료', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

            async with httpx.AsyncClient(timeout=10.0) as client:
                # weather
                if intent in ("weather", "weather_query"):
                    city = _extract_city(request.message)
                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='파라미터 추출 완료', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='weather-service 호출 중...', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"
                    r = await client.get(f"{orchestrator.weather_base_url}/weather/{city}")
                    r.raise_for_status()
                    data = r.json()

                    completed = min(completed + 1, len(tasks))
                    final = f"{data['city']} 현재 날씨는 {data['condition']}, {data['temperature']}°C 입니다."
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='완료', final_response=final, is_thinking=False, is_streaming=False), ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                # calendar query
                if intent in ("calendar", "calendar_query"):
                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='날짜 해석 완료', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='calendar-service 호출 중...', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

                    endpoint = "/calendar/tomorrow" if "내일" in request.message else "/calendar/today"
                    r = await client.get(f"{orchestrator.calendar_base_url}{endpoint}")
                    r.raise_for_status()
                    data = r.json()

                    completed = min(completed + 1, len(tasks))
                    if data.get("total_events", 0) == 0:
                        final = f"{data.get('date')} 일정이 없습니다."
                    else:
                        events = data.get("events", [])
                        lines = [f"- {e.get('start_time')} {e.get('title')}" for e in events[:10]]
                        final = f"{data.get('date')} 일정 {data.get('total_events')}개:\n" + "\n".join(lines)
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='완료', final_response=final, is_thinking=False, is_streaming=False), ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                # calendar create
                if intent in ("calendar_create",):
                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='파라미터 추출 완료', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

                    title = request.message
                    for k in ["일정", "회의", "미팅", "잡아줘", "추가해줘", "생성해줘", "만들어줘"]:
                        title = title.replace(k, "").strip()
                    if not title:
                        title = "새 일정"
                    payload = {"title": title, "start_time": _extract_time(request.message)}

                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='calendar-service 생성 요청 중...', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"
                    r = await client.post(f"{orchestrator.calendar_base_url}/calendar/events", json=payload)
                    r.raise_for_status()
                    data = r.json()

                    completed = min(completed + 1, len(tasks))
                    final = f"일정을 생성했어요: {data.get('start_time')} - {data.get('title')} (id={data.get('id')})"
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='완료', final_response=final, is_thinking=False, is_streaming=False), ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                # file search
                if intent in ("file_search",):
                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='키워드 정제 완료', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='file-service 검색 중...', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"
                    r = await client.get(f"{orchestrator.file_base_url}/files/search", params={"q": request.message})
                    r.raise_for_status()
                    data = r.json()
                    files = data.get("files", [])

                    completed = min(completed + 1, len(tasks))
                    if not files:
                        final = f"'{request.message}' 검색 결과가 없습니다."
                    else:
                        lines = [f"- {f.get('name')} ({f.get('path')})" for f in files[:8]]
                        final = f"검색 결과 {data.get('total_matches')}개:\n" + "\n".join(lines)
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='완료', final_response=final, is_thinking=False, is_streaming=False), ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                # notify
                if intent in ("notify", "notification_send"):
                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='채널/수신자 결정 완료', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"

                    channel = "slack" if ("슬랙" in request.message or "slack" in request.message.lower()) else "email" if ("이메일" in request.message or "email" in request.message.lower()) else "sms" if ("문자" in request.message or "sms" in request.message.lower()) else "slack"
                    payload = {"title": "알림", "message": request.message, "recipient": "team", "channel": channel}

                    completed = min(completed + 1, len(tasks))
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='notification-service 발송 중...', is_thinking=True, is_streaming=True), ensure_ascii=False)}\n\n"
                    r = await client.post(f"{orchestrator.notification_base_url}/notifications/send", json=payload)
                    r.raise_for_status()
                    data = r.json()

                    completed = min(completed + 1, len(tasks))
                    final = f"[mock] {channel} 알림 발송 완료 (id={data.get('id')})"
                    yield f"data: {json.dumps(_payload(completed_count=completed, current_status='완료', final_response=final, is_thinking=False, is_streaming=False), ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

            # help / fallback: just run existing orchestrator once and finish (todo all checked)
            result = await orchestrator.handle(message=request.message, conversation_history=conversation_history)
            final_text = result.get("message", "")
            completed = len(tasks)
            yield f"data: {json.dumps(_payload(completed_count=completed, current_status='완료', final_response=final_text, is_thinking=False, is_streaming=False), ensure_ascii=False)}\n\n"
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

