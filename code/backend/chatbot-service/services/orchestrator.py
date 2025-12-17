"""
Microservice-based orchestrator (lab-friendly).

- Keyword-based intent routing (temporary; replace with shared intent classifier later)
- Calls mock microservices via HTTP:
  - weather-service: 8001
  - calendar-service: 8002
  - file-service: 8003
  - notification-service: 8004
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os
import re

import httpx

from models import ChatMessage
from agents.intent_classifier import IntentClassifier
from agents.context_manager import get_or_create_session, context_manager
import time


def infer_intent(text: str) -> str:
    s = text.lower()
    if any(k in s for k in ["날씨", "기온", "비", "눈", "우산"]):
        return "weather"
    if any(k in s for k in ["일정", "회의", "미팅", "스케줄"]):
        if any(k in s for k in ["잡아", "생성", "추가", "만들"]):
            return "calendar_create"
        return "calendar"
    if any(k in s for k in ["파일", "문서", "자료", "명세", "회의록"]):
        return "file_search"
    if any(k in s for k in ["알림", "공지", "보내", "전송", "슬랙", "이메일", "sms", "문자"]):
        return "notify"
    if any(k in s for k in ["도움말", "뭐 할 수", "할 수 있어"]):
        return "help"
    return "chat"


def _extract_city(text: str) -> str:
    cities = ["서울", "부산", "인천", "대구", "광주", "대전", "울산", "세종"]
    for c in cities:
        if c in text:
            return c
    return "서울"


def _extract_time(text: str) -> str:
    m = re.search(r"(\d{1,2})\s*시", text)
    if m:
        hour = int(m.group(1))
        return f"{hour:02d}:00"
    m = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
    if m:
        return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    return "09:00"


@dataclass
class Orchestrator:
    weather_base_url: str
    calendar_base_url: str
    file_base_url: str
    notification_base_url: str
    rag_base_url: str

    @classmethod
    def from_env(cls) -> "Orchestrator":
        return cls(
            weather_base_url=os.getenv("WEATHER_SERVICE_URL", "http://localhost:8001"),
            calendar_base_url=os.getenv("CALENDAR_SERVICE_URL", "http://localhost:8002"),
            file_base_url=os.getenv("FILE_SERVICE_URL", "http://localhost:8003"),
            notification_base_url=os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8004"),
            rag_base_url=os.getenv("RAG_SERVICE_URL", "http://localhost:8005"),
        )

    async def handle(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[ChatMessage]] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        session_id = get_or_create_session(conversation_id)
        classifier = IntentClassifier()
        analysis = classifier.analyze_intent(message, context=None)
        intent = analysis.get("intent", infer_intent(message))
        meta: Dict[str, Any] = {
            "intent": intent,
            "analysis": analysis,
            "session_id": session_id,
            "recent_turns": context_manager.get_recent_turns(session_id, n=5),
        }

        if intent in ("help",):
            return {
                "message": (
                    "Agentic RAG 실습용 챗봇(마이크로서비스 버전)입니다.\n\n"
                    "- weather: 날씨 조회\n"
                    "- calendar: 일정 조회/생성\n"
                    "- file: 파일 검색\n"
                    "- notification: 알림 발송(mock)\n"
                ),
                "meta": meta,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            if intent in ("weather", "weather_query"):
                city = _extract_city(message)
                r = await client.get(f"{self.weather_base_url}/weather/{city}")
                r.raise_for_status()
                data = r.json()
                meta["weather"] = data
                response_text = f"{data['city']} 현재 날씨는 {data['condition']}, {data['temperature']}°C 입니다."
                context_manager.add_conversation_turn(
                    session_id=session_id,
                    user_input=message,
                    assistant_response=response_text,
                    intent=intent,
                    confidence=float(analysis.get("confidence", 0.7)),
                    apis_used=["weather"],
                    success=True,
                    processing_time=time.time() - start,
                    metadata={"tool_result": data},
                )
                return {"message": response_text, "meta": meta, "conversation_id": session_id}

            if intent in ("calendar", "calendar_query"):
                endpoint = "/calendar/tomorrow" if "내일" in message else "/calendar/today"
                r = await client.get(f"{self.calendar_base_url}{endpoint}")
                r.raise_for_status()
                data = r.json()
                meta["calendar"] = data
                if data.get("total_events", 0) == 0:
                    response_text = f"{data.get('date')} 일정이 없습니다."
                    context_manager.add_conversation_turn(
                        session_id=session_id,
                        user_input=message,
                        assistant_response=response_text,
                        intent=intent,
                        confidence=float(analysis.get("confidence", 0.7)),
                        apis_used=["calendar"],
                        success=True,
                        processing_time=time.time() - start,
                        metadata={"tool_result": data},
                    )
                    return {"message": response_text, "meta": meta, "conversation_id": session_id}
                events = data.get("events", [])
                lines = [f"- {e.get('start_time')} {e.get('title')}" for e in events[:10]]
                response_text = f"{data.get('date')} 일정 {data.get('total_events')}개:\n" + "\n".join(lines)
                context_manager.add_conversation_turn(
                    session_id=session_id,
                    user_input=message,
                    assistant_response=response_text,
                    intent=intent,
                    confidence=float(analysis.get("confidence", 0.7)),
                    apis_used=["calendar"],
                    success=True,
                    processing_time=time.time() - start,
                    metadata={"tool_result": data},
                )
                return {"message": response_text, "meta": meta, "conversation_id": session_id}

            if intent in ("calendar_create",):
                title = message
                for k in ["일정", "회의", "미팅", "잡아줘", "추가해줘", "생성해줘", "만들어줘"]:
                    title = title.replace(k, "").strip()
                if not title:
                    title = "새 일정"
                payload = {"title": title, "start_time": _extract_time(message)}
                r = await client.post(f"{self.calendar_base_url}/calendar/events", json=payload)
                r.raise_for_status()
                data = r.json()
                meta["calendar_create"] = data
                response_text = f"일정을 생성했어요: {data.get('start_time')} - {data.get('title')} (id={data.get('id')})"
                context_manager.add_conversation_turn(
                    session_id=session_id,
                    user_input=message,
                    assistant_response=response_text,
                    intent=intent,
                    confidence=float(analysis.get("confidence", 0.7)),
                    apis_used=["calendar"],
                    success=True,
                    processing_time=time.time() - start,
                    metadata={"tool_result": data},
                )
                return {"message": response_text, "meta": meta, "conversation_id": session_id}

            if intent in ("file_search",):
                r = await client.get(f"{self.file_base_url}/files/search", params={"q": message})
                r.raise_for_status()
                data = r.json()
                meta["file_search"] = data
                files = data.get("files", [])
                if not files:
                    response_text = f"'{message}' 검색 결과가 없습니다."
                    context_manager.add_conversation_turn(
                        session_id=session_id,
                        user_input=message,
                        assistant_response=response_text,
                        intent=intent,
                        confidence=float(analysis.get("confidence", 0.7)),
                        apis_used=["file"],
                        success=True,
                        processing_time=time.time() - start,
                        metadata={"tool_result": data},
                    )
                    return {"message": response_text, "meta": meta, "conversation_id": session_id}
                lines = []
                for f in files[:8]:
                    lines.append(f"- {f.get('name')} ({f.get('path')})")
                response_text = f"검색 결과 {data.get('total_matches')}개:\n" + "\n".join(lines)
                context_manager.add_conversation_turn(
                    session_id=session_id,
                    user_input=message,
                    assistant_response=response_text,
                    intent=intent,
                    confidence=float(analysis.get("confidence", 0.7)),
                    apis_used=["file"],
                    success=True,
                    processing_time=time.time() - start,
                    metadata={"tool_result": data},
                )
                return {"message": response_text, "meta": meta, "conversation_id": session_id}

            if intent in ("notify", "notification_send"):
                channel = "slack" if ("슬랙" in message or "slack" in message.lower()) else "email" if ("이메일" in message or "email" in message.lower()) else "sms" if ("문자" in message or "sms" in message.lower()) else "slack"
                payload = {"title": "알림", "message": message, "recipient": "team", "channel": channel}
                r = await client.post(f"{self.notification_base_url}/notifications/send", json=payload)
                r.raise_for_status()
                data = r.json()
                meta["notification"] = data
                response_text = f"[mock] {channel} 알림 발송 완료 (id={data.get('id')})"
                context_manager.add_conversation_turn(
                    session_id=session_id,
                    user_input=message,
                    assistant_response=response_text,
                    intent=intent,
                    confidence=float(analysis.get("confidence", 0.7)),
                    apis_used=["notification"],
                    success=True,
                    processing_time=time.time() - start,
                    metadata={"tool_result": data},
                )
                return {"message": response_text, "meta": meta, "conversation_id": session_id}

            # RAG fallback for general chat/questions (uses Qdrant-backed rag-service)
            if intent in ("chat",):
                try:
                    r = await client.post(f"{self.rag_base_url}/rag/query", json={"query": message, "top_k": 5})
                    r.raise_for_status()
                    data = r.json()
                    meta["rag"] = data
                    hits = data.get("hits", [])
                    if hits:
                        top = hits[0]
                        response_text = f"관련 문서 기반 답변(Top1):\n- {top.get('text','')}\n(출처: {top.get('source','')})"
                    else:
                        response_text = "관련 문서를 찾지 못했어요."
                except Exception as e:
                    meta["rag_error"] = str(e)
                    response_text = message

                context_manager.add_conversation_turn(
                    session_id=session_id,
                    user_input=message,
                    assistant_response=response_text,
                    intent=intent,
                    confidence=float(analysis.get("confidence", 0.7)),
                    apis_used=["rag"] if "rag" in meta else [],
                    success=True,
                    processing_time=time.time() - start,
                    metadata={},
                )
                return {"message": response_text, "meta": meta, "conversation_id": session_id}

        # Fallback
        response_text = message
        context_manager.add_conversation_turn(
            session_id=session_id,
            user_input=message,
            assistant_response=response_text,
            intent=intent,
            confidence=float(analysis.get("confidence", 0.7)),
            apis_used=[],
            success=True,
            processing_time=time.time() - start,
            metadata={},
        )
        return {"message": response_text, "meta": meta, "conversation_id": session_id}


orchestrator = Orchestrator.from_env()


