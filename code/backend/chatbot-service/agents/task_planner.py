"""
Task Planner Agent (Cursor-style To-Do output) for education.

This agent plans high-level steps before tools are called.
It does NOT execute; orchestrator executes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class TaskPlannerAgent:
    def plan(self, user_input: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        intent = analysis.get("intent", "chat")
        apis: List[str] = list(analysis.get("apis") or [])

        tasks: List[str] = []
        tasks.append("사용자 요청의 의도를 확인한다")

        # Multi-tool / composite heuristic
        is_multi = ("그리고" in user_input) or ("한 다음" in user_input) or ("후에" in user_input)

        if intent in ("weather_query",):
            tasks += ["도시/기간 등 파라미터를 추출한다", "weather-service를 호출해 데이터를 가져온다", "결과를 요약해 답변한다"]
        elif intent in ("calendar_query",):
            tasks += ["날짜(오늘/내일/특정일)를 해석한다", "calendar-service를 호출해 일정을 가져온다", "일정/빈시간을 요약한다"]
        elif intent in ("calendar_create",):
            tasks += ["제목/시간/날짜를 추출한다", "calendar-service에 이벤트 생성을 요청한다", "생성 결과를 확인해 사용자에게 안내한다"]
        elif intent in ("file_search",):
            tasks += ["검색 키워드를 정제한다", "file-service를 호출해 검색한다", "상위 결과를 리스트업한다"]
        elif intent in ("notification_send",):
            tasks += ["채널(email/slack/sms)과 수신자를 결정한다", "notification-service로 발송한다", "발송 결과를 확인한다"]
        elif intent in ("help",):
            tasks += ["가능한 기능/예시를 정리해서 안내한다"]
        else:
            # chat / rag fallback
            tasks += ["rag-service(Qdrant)를 질의해 관련 문서를 찾는다", "근거(출처)와 함께 간단히 답한다"]

        if is_multi and len(apis) > 1:
            tasks.insert(1, "요청이 여러 작업으로 구성되어 있는지 분해한다")

        return {"tasks": tasks, "intent": intent, "apis": apis}


