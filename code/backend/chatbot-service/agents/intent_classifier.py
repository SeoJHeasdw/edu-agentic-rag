"""
Lab-friendly intent classifier (no shared dependencies).

Moved from backend/agents/intent_classifier.py to keep chatbot-service self-contained.
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
            "parameters": {"user_input": user_input},
            "reasoning": "keyword-based (lab)",
        }


