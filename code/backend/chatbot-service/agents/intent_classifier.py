"""
실습용 의도 분류기(외부 공용 모듈 의존성 없음).

`backend/agents/intent_classifier.py`에서 이동:
- `chatbot-service`가 단독으로 실행되도록 하기 위함
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class IntentClassifier:
    def _wants_notification(self, s: str) -> bool:
        # 예시:
        # - "팀에게 알려줘", "팀에 공유해줘", "동료들에게 전달해줘"
        recipients = ["팀", "팀원", "동료", "사람들", "전체", "전원", "모두"]
        verbs = ["알려", "공유", "전달", "공지", "알림", "보내", "전송"]
        channels = ["슬랙", "slack", "이메일", "email", "sms", "문자", "메일"]

        has_recipient = any(k in s for k in recipients)
        has_verb = any(k in s for k in verbs)
        has_channel = any(k in s for k in channels)

        # 수신자+동사 조합이 명시되거나, 채널 키워드가 포함되면 notification 의도로 판단
        return (has_recipient and has_verb) or has_channel

    def analyze_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        s = user_input.lower()

        apis = []
        intent = "chat"
        confidence = 0.7
        parameters: Dict[str, Any] = {"user_input": user_input}

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

        # 복합 요청: 도구 호출 의도 + "팀에게 알려줘" 류의 알림 요청 (예: "오늘 날씨를 팀에게 알려줘")
        if intent in ("weather_query", "calendar_query", "calendar_create", "file_search"):
            if self._wants_notification(s) and "notification" not in apis:
                apis = list(apis) + ["notification"]
                parameters["notify"] = True
                parameters["notify_recipient"] = "team"

        return {
            "intent": intent,
            "apis": apis,
            "confidence": confidence,
            "parameters": parameters,
            "reasoning": "키워드 기반(실습용)",
        }


