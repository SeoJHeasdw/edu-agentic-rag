"""
Lab-friendly intent classifier (no shared dependencies).

Later you can replace this with your `shared` + embedding/LLM based classifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class IntentClassifier:
    def analyze_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        s = user_input.lower()

        apis = []
        intent = "chat"
        confidence = 0.7

        if any(k in s for k in ["날씨", "기온", "비", "눈", "우산"]):
            intent = "weather_query"
            apis = ["weather"]
        elif any(k in s for k in ["일정", "회의", "미팅", "스케줄"]):
            if any(k in s for k in ["잡아", "생성", "추가", "만들"]):
                intent = "calendar_create"
            else:
                intent = "calendar_query"
            apis = ["calendar"]
        elif any(k in s for k in ["파일", "문서", "자료", "명세", "회의록"]):
            intent = "file_search"
            apis = ["file"]
        elif any(k in s for k in ["알림", "공지", "보내", "전송", "슬랙", "이메일", "sms", "문자"]):
            intent = "notification_send"
            apis = ["notification"]
        elif any(k in s for k in ["도움말", "뭐 할 수", "할 수 있어"]):
            intent = "help"
            apis = []
            confidence = 0.9

        return {
            "intent": intent,
            "apis": apis,
            "confidence": confidence,
            "parameters": {
                "user_input": user_input,
            },
            "reasoning": "keyword-based (lab)",
        }

"""
Lightweight intent classifier (lab-friendly).

This intentionally avoids any dependency on `shared.*`.
You can later swap this with your own shared / RAG-based classifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class IntentClassifier:
    name: str = "IntentClassifier (simple)"

    def analyze_intent(self, user_input: str, context: Dict | None = None) -> Dict[str, Any]:
        s = user_input.lower()

        apis: List[str] = []
        intent = "rag_query"
        confidence = 0.7

        if any(k in s for k in ["날씨", "기온", "비", "눈", "wind", "weather"]):
            intent = "weather_query"
            apis = ["weather"]
        elif any(k in s for k in ["일정", "회의", "미팅", "스케줄", "calendar", "meeting"]):
            if any(k in s for k in ["잡아", "생성", "만들", "추가", "예약"]):
                intent = "calendar_create"
            else:
                intent = "calendar_query"
            apis = ["calendar"]
        elif any(k in s for k in ["파일", "문서", "자료", "검색", "readme", ".md", "file", "document"]):
            intent = "file_search"
            apis = ["file"]
        elif any(k in s for k in ["알림", "공지", "보내", "전송", "슬랙", "이메일", "sms", "문자", "notify"]):
            intent = "notification_send"
            apis = ["notification"]
        elif any(k in s for k in ["뭐 할 수", "할 수 있어", "도움말", "help"]):
            intent = "help"
            apis = []
            confidence = 0.9

        return {
            "user_input": user_input,
            "intent": intent,
            "apis": apis,
            "confidence": confidence,
            "reasoning": "keyword-based (lab default)",
            "parameters": {},
            "action_sequence": apis,
        }


