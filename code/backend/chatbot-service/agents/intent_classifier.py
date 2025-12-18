"""
실습용 의도 분류기 - Few-shot LLM 기반으로 개선.

역할: 사용자 쿼리의 의도를 빠르게 파악하는 전문 에이전트
- "검색인가, 요약인가, 비교인가, 계산인가" 등을 판단
- 단일 분류 작업, 빠르고 가벼움
- 라우팅 결정에 주로 사용
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class IntentClassifier:
    llm_chat_fn: Any = None  # callable(prompt:str)->str, injected from orchestrator
    
    def _extract_primary_intent(self, llm_response: str) -> str:
        """LLM 응답에서 의도를 추출 (fallback 처리 포함)"""
        response = str(llm_response or "").strip().lower()
        
        # 정확한 매칭 우선
        valid_intents = ["weather_query", "calendar_query", "calendar_create", 
                        "file_search", "notification_send", "help", "chat"]
        
        for intent in valid_intents:
            if intent in response:
                return intent
        
        # 부분 매칭 fallback
        if "weather" in response:
            return "weather_query"
        elif "calendar" in response:
            if any(k in response for k in ["create", "생성", "추가", "만들"]):
                return "calendar_create"
            return "calendar_query"
        elif "file" in response or "문서" in response:
            return "file_search"
        elif "notification" in response or "알림" in response:
            return "notification_send"
        elif "help" in response or "도움" in response:
            return "help"
        
        return "chat"  # 기본값
    
    def _detect_notification_intent(self, user_input: str) -> bool:
        """복합 요청에서 알림 의도 감지"""
        s = user_input.lower()
        
        # "알려줘", "공유해줘", "전달해줘" 패턴
        notification_patterns = ["알려", "공유", "전달", "공지", "보내", "전송"]
        recipients = ["팀", "팀원", "동료", "사람들", "전체", "전원", "모두"]
        channels = ["슬랙", "slack", "이메일", "email", "sms", "문자", "메일"]
        
        has_notification_verb = any(pattern in s for pattern in notification_patterns)
        has_recipient = any(recipient in s for recipient in recipients)
        has_channel = any(channel in s for channel in channels)
        
        return has_notification_verb or has_channel or (has_recipient and "에게" in s)

    def analyze_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Few-shot LLM 기반 의도 분류"""
        
        # LLM이 비활성화된 경우 키워드 기반 fallback
        if not self.llm_chat_fn:
            return self._fallback_keyword_analysis(user_input)
        
        # Few-shot prompt for intent classification
        prompt = f"""사용자 입력의 의도를 빠르게 분류하세요. (도메인 라우팅용)

분류 기준:
- weather_query: 날씨 관련 조회
- calendar_query: 일정 조회  
- calendar_create: 일정 생성
- file_search: 문서/파일 검색
- notification_send: 알림/공지 발송
- help: 도움말/기능 설명
- chat: 일반 대화/질문

예시:
"서울 날씨 어때?" → weather_query
"오늘 일정 있어?" → calendar_query  
"3시에 회의 잡아줘" → calendar_create
"계약서 찾아줘" → file_search
"팀에게 알려줘" → notification_send
"뭐 할 수 있어?" → help
"안녕하세요" → chat
"우리 회사 매출이 얼마야?" → chat
"비가 올까?" → weather_query
"내일 미팅 있나?" → calendar_query

사용자 입력: "{user_input}"
분류 결과 (intent만 답변): """

        try:
            llm_response = self.llm_chat_fn(prompt)
            primary_intent = self._extract_primary_intent(llm_response)
        except Exception:
            # LLM 실패 시 키워드 기반 fallback
            return self._fallback_keyword_analysis(user_input)
        
        # API 매핑
        apis = []
        if primary_intent == "weather_query":
            apis = ["weather"]
        elif primary_intent in ("calendar_query", "calendar_create"):
            apis = ["calendar"]
        elif primary_intent == "file_search":
            apis = ["file"]
        elif primary_intent == "notification_send":
            apis = ["notification"]
        elif primary_intent == "help":
            apis = []
        else:  # chat
            apis = ["rag"]  # 일반 대화는 RAG 사용
        
        # 복합 요청 감지: "날씨 확인해서 팀에게 알려줘"
        if primary_intent in ("weather_query", "calendar_query", "calendar_create", "file_search"):
            if self._detect_notification_intent(user_input):
                if "notification" not in apis:
                    apis.append("notification")
        
        confidence = 0.85 if primary_intent != "chat" else 0.75  # LLM 기반이므로 높은 신뢰도
        
        return {
            "intent": primary_intent,
            "apis": apis,
            "confidence": confidence,
            "parameters": {
                "user_input": user_input,
                "notify": "notification" in apis and primary_intent != "notification_send"
            },
            "reasoning": "Few-shot LLM 분류",
        }
    
    def _fallback_keyword_analysis(self, user_input: str) -> Dict[str, Any]:
        """LLM 비활성화 시 키워드 기반 fallback"""
        s = user_input.lower()
        
        apis = []
        intent = "chat"
        confidence = 0.6  # 키워드 기반은 낮은 신뢰도
        
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
        
        # 복합 요청 감지
        if intent in ("weather_query", "calendar_query", "calendar_create", "file_search"):
            if self._detect_notification_intent(user_input):
                if "notification" not in apis:
                    apis.append("notification")
        
        return {
            "intent": intent,
            "apis": apis,
            "confidence": confidence,
            "parameters": {
                "user_input": user_input,
                "notify": "notification" in apis and intent != "notification_send"
            },
            "reasoning": "키워드 기반 (LLM 비활성화)",
        }


