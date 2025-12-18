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
from agents.task_planner_agent import TaskPlannerAgent
from services.llm_service import llm_service
from services.tool_executor import ToolExecutor, tool_defs, tools_prompt
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

def _format_todo(tasks: List[str]) -> str:
    if not tasks:
        return ""
    lines = ["### To-Do", *[f"{i+1}. {t}" for i, t in enumerate(tasks)]]
    return "\n".join(lines)

def _with_plan(response_text: str, plan: Dict[str, Any]) -> str:
    tasks = plan.get("tasks") or []
    todo = _format_todo(tasks)
    if not todo:
        return response_text
    return f"{todo}\n\n### 실행 결과\n{response_text}"


def _rule_todo_list(user_input: str, analysis: Dict[str, Any]) -> List[str]:
    """
    룰 기반 To-Do 생성기 (UI 전용 폴백).
    - 에이전트가 아니라 “화면 표시용” 단계 목록 생성만 담당
    - LLM이 비활성화된 경우에만 사용
    """
    intent = analysis.get("intent", "chat")
    apis: List[str] = list(analysis.get("apis") or [])
    wants_notify = "notification" in apis or bool((analysis.get("parameters") or {}).get("notify"))

    tasks: List[str] = []
    if intent in ("weather_query", "weather"):
        tasks += ["도시/기간 등 파라미터를 추출한다", "weather-service를 호출해 데이터를 가져온다", "결과를 요약해 답변한다"]
        if wants_notify:
            tasks += ["팀에게 전달할 메시지를 구성한다", "notification-service로 발송한다", "발송 결과를 확인한다"]
        return tasks
    if intent in ("calendar_query", "calendar"):
        tasks += ["날짜(오늘/내일/특정일)를 해석한다", "calendar-service를 호출해 일정을 가져온다", "일정/빈시간을 요약한다"]
        if wants_notify:
            tasks += ["팀에게 전달할 메시지를 구성한다", "notification-service로 발송한다", "발송 결과를 확인한다"]
        return tasks
    if intent in ("calendar_create",):
        tasks += ["제목/시간/날짜를 추출한다", "calendar-service에 이벤트 생성을 요청한다", "생성 결과를 확인해 사용자에게 안내한다"]
        if wants_notify:
            tasks += ["팀에게 전달할 메시지를 구성한다", "notification-service로 발송한다", "발송 결과를 확인한다"]
        return tasks
    if intent in ("file_search",):
        tasks += ["검색 키워드를 정제한다", "file-service를 호출해 검색한다", "상위 결과를 리스트업한다"]
        if wants_notify:
            tasks += ["팀에게 전달할 메시지를 구성한다", "notification-service로 발송한다", "발송 결과를 확인한다"]
        return tasks
    if intent in ("notification_send", "notify"):
        return ["채널(email/slack/sms)과 수신자를 결정한다", "notification-service로 발송한다", "발송 결과를 확인한다"]
    if intent in ("help",):
        return ["가능한 기능/예시를 정리해서 안내한다"]
    return ["rag-service(Qdrant)를 질의해 관련 문서를 찾는다", "근거(출처)와 함께 간단히 답한다"]


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

        # If LLM is enabled, run agentic pipeline:
        # IntentClassifier(lightweight) -> TaskPlannerAgent(plan/replan) -> ToolExecutor(execute+cache) -> final answer
        if llm_service.is_enabled():
            try:
                agent_result = await self._agentic_run(message=message, session_id=session_id)
                response_text = agent_result.get("final", "")
                meta: Dict[str, Any] = {
                    "intent": "agentic",
                    "analysis": {
                        "intent": agent_result.get("intent", "agentic"),
                        "apis": agent_result.get("apis", []),
                        "confidence": float(agent_result.get("confidence", 0.7)),
                    },
                    "plan": {"tasks": agent_result.get("todo", [])},
                    "agent": {"executed": agent_result.get("executed", []), "used_tools": agent_result.get("used_tools", [])},
                    "session_id": session_id,
                    "recent_turns": context_manager.get_recent_turns(session_id, n=5),
                }
                context_manager.add_conversation_turn(
                    session_id=session_id,
                    user_input=message,
                    assistant_response=response_text,
                    intent="agentic",
                    confidence=float(agent_result.get("confidence", 0.7)),
                    apis_used=agent_result.get("used_tools", []) or [],
                    success=True,
                    processing_time=time.time() - start,
                    metadata={"agent": agent_result},
                )
                return {"message": response_text, "meta": meta, "conversation_id": session_id}
            except Exception as e:
                # Fail-safe: if LLM is misconfigured or temporarily unavailable,
                # fall back to the rule-based orchestrator instead of crashing the API.
                llm_error = str(e)
        else:
            llm_error = None

        classifier = IntentClassifier()
        analysis = classifier.analyze_intent(message, context=None)
        intent = analysis.get("intent", infer_intent(message))
        apis = list(analysis.get("apis") or [])
        wants_notify = "notification" in apis or bool((analysis.get("parameters") or {}).get("notify"))
        plan = {"tasks": _rule_todo_list(message, analysis), "intent": intent, "apis": apis}
        meta: Dict[str, Any] = {
            "intent": intent,
            "analysis": analysis,
            "plan": plan,
            "session_id": session_id,
            "recent_turns": context_manager.get_recent_turns(session_id, n=5),
        }
        if llm_error:
            meta["llm_fallback"] = {
                "provider": llm_service.provider,
                "error": llm_error,
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
                weather_summary = f"{data['city']} 현재 날씨는 {data['condition']}, {data['temperature']}°C 입니다."

                # Optional follow-up: notify team (composite request)
                notify_meta = None
                if wants_notify:
                    channel = (
                        "slack"
                        if ("슬랙" in message or "slack" in message.lower())
                        else "email"
                        if ("이메일" in message or "email" in message.lower() or "메일" in message.lower())
                        else "sms"
                        if ("문자" in message or "sms" in message.lower())
                        else "slack"
                    )
                    payload = {
                        "title": "날씨 알림",
                        "message": weather_summary,
                        "recipient": "team",
                        "channel": channel,
                    }
                    nr = await client.post(f"{self.notification_base_url}/notifications/send", json=payload)
                    nr.raise_for_status()
                    notify_meta = nr.json()
                    meta["notification"] = notify_meta

                if wants_notify and notify_meta:
                    response_text = _with_plan(
                        f"{weather_summary}\n\n[mock] {notify_meta.get('channel', 'slack')} 알림 발송 완료 (id={notify_meta.get('id')})",
                        plan,
                    )
                else:
                    response_text = _with_plan(weather_summary, plan)

                context_manager.add_conversation_turn(
                    session_id=session_id,
                    user_input=message,
                    assistant_response=response_text,
                    intent=intent,
                    confidence=float(analysis.get("confidence", 0.7)),
                    apis_used=["weather", "notification"] if wants_notify and notify_meta else ["weather"],
                    success=True,
                    processing_time=time.time() - start,
                    metadata={"tool_result": data, "notification": notify_meta} if notify_meta else {"tool_result": data},
                )
                return {"message": response_text, "meta": meta, "conversation_id": session_id}

            if intent in ("calendar", "calendar_query"):
                endpoint = "/calendar/tomorrow" if "내일" in message else "/calendar/today"
                r = await client.get(f"{self.calendar_base_url}{endpoint}")
                r.raise_for_status()
                data = r.json()
                meta["calendar"] = data
                if data.get("total_events", 0) == 0:
                    response_text = _with_plan(f"{data.get('date')} 일정이 없습니다.", plan)
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
                response_text = _with_plan(
                    f"{data.get('date')} 일정 {data.get('total_events')}개:\n" + "\n".join(lines),
                    plan,
                )
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
                response_text = _with_plan(
                    f"일정을 생성했어요: {data.get('start_time')} - {data.get('title')} (id={data.get('id')})",
                    plan,
                )
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
                    response_text = _with_plan(f"'{message}' 검색 결과가 없습니다.", plan)
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
                response_text = _with_plan(
                    f"검색 결과 {data.get('total_matches')}개:\n" + "\n".join(lines),
                    plan,
                )
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
                response_text = _with_plan(f"[mock] {channel} 알림 발송 완료 (id={data.get('id')})", plan)
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
                        response_text = _with_plan(
                            f"관련 문서 기반 답변(Top1):\n- {top.get('text','')}\n(출처: {top.get('source','')})",
                            plan,
                        )
                    else:
                        response_text = _with_plan("관련 문서를 찾지 못했어요.", plan)
                except Exception as e:
                    meta["rag_error"] = str(e)
                    response_text = _with_plan(message, plan)

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
        response_text = _with_plan(message, plan)
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

    # ---------------- Agentic internals (keep orchestrator as the single runtime) ----------------
    def _agentic_executor(self) -> ToolExecutor:
        return ToolExecutor(
            weather_base_url=self.weather_base_url,
            calendar_base_url=self.calendar_base_url,
            file_base_url=self.file_base_url,
            notification_base_url=self.notification_base_url,
            rag_base_url=self.rag_base_url,
            tools=tool_defs(),
        )

    @staticmethod
    def _agentic_extract_json_object(text: str) -> Dict[str, Any]:
        import json as _json

        if not text:
            return {}
        text = text.strip()
        try:
            obj = _json.loads(text)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            pass
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                obj = _json.loads(text[start : end + 1])
                return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
        return {}

    def _agentic_fill_args_prompt(self, *, user_input: str, tool: str, args_schema: Dict[str, Any], recent_turns: List[Dict[str, Any]]) -> str:
        import json as _json

        def _safe(x, limit=800):
            try:
                s = _json.dumps(x, ensure_ascii=False)
            except Exception:
                s = str(x)
            return s if len(s) <= limit else (s[:limit] + "…")

        return (
            "당신은 Executor를 돕는 ReAct 서브루틴입니다.\n"
            "주어진 tool을 실행하기 위한 args만 JSON으로 채우세요. 반드시 JSON만 출력.\n\n"
            f"tool: {tool}\n"
            f"args_schema: {args_schema}\n"
            f"최근 대화(참고): {_safe(recent_turns)}\n\n"
            f"사용자 요청: {user_input}\n"
            '반환 형식: {"args":{...}}\n'
        )

    def _agentic_final_answer_prompt(self, *, user_input: str, intent: str, tasks: List[Dict[str, Any]], observations: List[Dict[str, Any]]) -> str:
        import json as _json

        def _safe(x, limit=1600):
            try:
                s = _json.dumps(x, ensure_ascii=False)
            except Exception:
                s = str(x)
            return s if len(s) <= limit else (s[:limit] + "…")

        return (
            "당신은 Assistant입니다. 실행 관찰 결과를 바탕으로 사용자에게 최종 답변을 생성하세요.\n"
            "불필요한 내부 계획/JSON/디버그를 노출하지 말고, 자연어로 간결하게 답하세요.\n\n"
            f"Intent: {intent}\n"
            f"사용자 요청: {user_input}\n\n"
            f"계획(tasks): {_safe(tasks, 1200)}\n\n"
            f"관찰(observations): {_safe(observations, 1800)}\n"
        )

    @staticmethod
    def _agentic_topo_sort(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_id = {t.get("id"): t for t in tasks if isinstance(t, dict) and t.get("id")}
        visiting = set()
        visited = set()
        out: List[Dict[str, Any]] = []

        def dfs(tid: str):
            if tid in visited:
                return
            if tid in visiting:
                return
            visiting.add(tid)
            t = by_id.get(tid)
            deps = t.get("depends_on") if isinstance(t, dict) else []
            if isinstance(deps, list):
                for d in deps:
                    if isinstance(d, str) and d in by_id:
                        dfs(d)
            visiting.remove(tid)
            visited.add(tid)
            if t:
                out.append(t)

        for tid in list(by_id.keys()):
            dfs(tid)

        seen = set()
        stable: List[Dict[str, Any]] = []
        for t in out:
            tid = t.get("id")
            if tid in seen:
                continue
            seen.add(tid)
            stable.append(t)
        return stable

    async def _agentic_run(self, *, message: str, session_id: str) -> Dict[str, Any]:
        recent_turns = context_manager.get_recent_turns(session_id, n=5)

        # 1) lightweight intent classification
        cls = IntentClassifier()
        analysis = cls.analyze_intent(message, context=None)
        intent = str(analysis.get("intent") or "chat")
        apis = list(analysis.get("apis") or [])
        confidence = float(analysis.get("confidence") or 0.7)

        # 2) LLM plan/replan
        planner = TaskPlannerAgent(
            llm_chat_fn=lambda prompt: llm_service.chat(message=prompt, conversation_history=None),
            tools_prompt=tools_prompt(),
        )
        plan_obj = planner.plan(user_input=message, intent=intent, apis=apis, recent_turns=recent_turns)
        tasks = plan_obj.get("tasks") if isinstance(plan_obj.get("tasks"), list) else []
        if not tasks:
            tasks = [{"id": "t1", "text": "요청을 처리한다", "tool": "none", "args": {}, "depends_on": [], "produces": "final"}]
        tasks = self._agentic_topo_sort(tasks)
        todo = [str(t.get("text") or "") for t in tasks if isinstance(t, dict) and t.get("text")]

        # 3) execute with cache + replans
        executor = self._agentic_executor()

        def fill_args(tool: str, schema: Dict[str, Any]) -> Dict[str, Any]:
            filled = self._agentic_extract_json_object(
                llm_service.chat(message=self._agentic_fill_args_prompt(user_input=message, tool=tool, args_schema=schema, recent_turns=recent_turns), conversation_history=None)
            )
            return filled.get("args") if isinstance(filled.get("args"), dict) else {}

        def replan(current_tasks: List[Dict[str, Any]], observations: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
            rp = planner.replan(user_input=message, intent=intent, apis=apis, current_tasks=current_tasks, observations=observations)
            new_tasks = rp.get("tasks") if isinstance(rp.get("tasks"), list) else None
            return self._agentic_topo_sort(new_tasks) if new_tasks else None

        observations, used_tools, final_tasks = await executor.execute_plan(
            user_input=message,
            session_id=session_id,
            tasks=tasks,
            fill_args_fn=fill_args,
            replan_fn=replan,
        )

        # 4) final answer
        final_text = str(
            llm_service.chat(
                message=self._agentic_final_answer_prompt(user_input=message, intent=intent, tasks=final_tasks, observations=observations),
                conversation_history=None,
            )
            or ""
        ).strip()
        if not final_text:
            final_text = "요청을 처리했지만 답변 생성에 실패했어요."

        return {
            "final": final_text,
            "todo": todo,
            "executed": observations,
            "used_tools": used_tools,
            "intent": intent,
            "confidence": confidence,
            "apis": apis,
        }

    async def stream(self, *, message: str, conversation_id: Optional[str] = None, conversation_history: Optional[List[ChatMessage]] = None):
        """
        Yields event dicts:
        - {todo: list[str], completed: int, status: str, final?: str, done?: bool}
        """
        session_id = get_or_create_session(conversation_id)

        if llm_service.is_enabled():
            try:
                # Agentic coarse streaming (planner + executor)
                recent_turns = context_manager.get_recent_turns(session_id, n=5)
                yield {"todo": [], "completed": 0, "status": "의도 분석 중..."}

                analysis = IntentClassifier().analyze_intent(message, context=None)
                intent = str(analysis.get("intent") or "chat")
                apis = list(analysis.get("apis") or [])

                yield {"todo": [], "completed": 0, "status": "계획 수립 중..."}
                planner = TaskPlannerAgent(
                    llm_chat_fn=lambda prompt: llm_service.chat(message=prompt, conversation_history=None),
                    tools_prompt=tools_prompt(),
                )
                plan_obj = planner.plan(user_input=message, intent=intent, apis=apis, recent_turns=recent_turns)
                tasks = plan_obj.get("tasks") if isinstance(plan_obj.get("tasks"), list) else []
                if not tasks:
                    tasks = [{"id": "t1", "text": "요청을 처리한다", "tool": "none", "args": {}, "depends_on": [], "produces": "final"}]
                tasks = self._agentic_topo_sort(tasks)
                todo = [str(t.get("text") or "") for t in tasks if isinstance(t, dict) and t.get("text")]
                yield {"todo": todo, "completed": 0, "status": "계획 수립 완료"}

                completed = 0
                for t in tasks:
                    completed = min(completed + 1, len(todo))
                    tool = str(t.get("tool") or "none").strip()
                    status = f"{tool} 실행 중..." if tool and tool != "none" else "진행 중..."
                    yield {"todo": todo, "completed": completed, "status": status}

                executor = self._agentic_executor()

                def fill_args(tool: str, schema: Dict[str, Any]) -> Dict[str, Any]:
                    filled = self._agentic_extract_json_object(
                        llm_service.chat(message=self._agentic_fill_args_prompt(user_input=message, tool=tool, args_schema=schema, recent_turns=recent_turns), conversation_history=None)
                    )
                    return filled.get("args") if isinstance(filled.get("args"), dict) else {}

                def replan(current_tasks: List[Dict[str, Any]], observations: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
                    rp = planner.replan(user_input=message, intent=intent, apis=apis, current_tasks=current_tasks, observations=observations)
                    new_tasks = rp.get("tasks") if isinstance(rp.get("tasks"), list) else None
                    return self._agentic_topo_sort(new_tasks) if new_tasks else None

                observations, _, final_tasks = await executor.execute_plan(
                    user_input=message,
                    session_id=session_id,
                    tasks=tasks,
                    fill_args_fn=fill_args,
                    replan_fn=replan,
                )

                final_text = str(
                    llm_service.chat(
                        message=self._agentic_final_answer_prompt(user_input=message, intent=intent, tasks=final_tasks, observations=observations),
                        conversation_history=None,
                    )
                    or ""
                ).strip()
                yield {"todo": todo, "completed": len(todo), "status": "완료", "final": final_text, "done": True}
                return
            except Exception as e:
                # Stream fail-safe: downgrade to rule-based stream so UI still completes.
                yield {"todo": [], "completed": 0, "status": f"LLM 오류로 rule-based로 전환: {e}"}

        # Rule-based structured stream (existing behavior moved from api/chat.py)
        classifier = IntentClassifier()
        analysis = classifier.analyze_intent(message, context=None)
        intent = analysis.get("intent", infer_intent(message))
        apis = list(analysis.get("apis") or [])
        wants_notify = "notification" in apis or bool((analysis.get("parameters") or {}).get("notify"))

        plan = {"tasks": _rule_todo_list(message, analysis), "intent": intent, "apis": apis}
        tasks = plan.get("tasks") or []

        # Emit initial state
        yield {"todo": tasks, "completed": 0, "status": "계획 수립 중..."}
        yield {"todo": tasks, "completed": 0, "status": "의도 분석 완료"}

        completed = 0
        async with httpx.AsyncClient(timeout=10.0) as client:
            # weather
            if intent in ("weather", "weather_query"):
                city = _extract_city(message)
                completed = min(completed + 1, len(tasks))
                yield {"todo": tasks, "completed": completed, "status": "파라미터 추출 완료"}

                completed = min(completed + 1, len(tasks))
                yield {"todo": tasks, "completed": completed, "status": "weather-service 호출 중..."}
                r = await client.get(f"{self.weather_base_url}/weather/{city}")
                r.raise_for_status()
                data = r.json()
                weather_summary = f"{data['city']} 현재 날씨는 {data['condition']}, {data['temperature']}°C 입니다."

                completed = min(completed + 1, len(tasks))
                if wants_notify:
                    yield {"todo": tasks, "completed": completed, "status": "결과 요약 완료"}
                    completed = min(completed + 1, len(tasks))
                    yield {"todo": tasks, "completed": completed, "status": "notification-service 발송 중..."}
                    channel = (
                        "slack"
                        if ("슬랙" in message or "slack" in message.lower())
                        else "email"
                        if ("이메일" in message or "email" in message.lower() or "메일" in message.lower())
                        else "sms"
                        if ("문자" in message or "sms" in message.lower())
                        else "slack"
                    )
                    payload = {"title": "날씨 알림", "message": weather_summary, "recipient": "team", "channel": channel}
                    nr = await client.post(f"{self.notification_base_url}/notifications/send", json=payload)
                    nr.raise_for_status()
                    notify_meta = nr.json()
                    completed = min(completed + 1, len(tasks))
                    yield {"todo": tasks, "completed": completed, "status": "발송 결과 확인 완료"}
                    final = f"{weather_summary}\n\n[mock] {notify_meta.get('channel', channel)} 알림 발송 완료 (id={notify_meta.get('id')})"
                else:
                    final = weather_summary

                yield {"todo": tasks, "completed": completed, "status": "완료", "final": final, "done": True}
                return

            # notify only
            if intent in ("notify", "notification_send"):
                completed = min(completed + 1, len(tasks))
                yield {"todo": tasks, "completed": completed, "status": "채널/수신자 결정 완료"}
                channel = (
                    "slack"
                    if ("슬랙" in message or "slack" in message.lower())
                    else "email"
                    if ("이메일" in message or "email" in message.lower() or "메일" in message.lower())
                    else "sms"
                    if ("문자" in message or "sms" in message.lower())
                    else "slack"
                )
                payload = {"title": "알림", "message": message, "recipient": "team", "channel": channel}
                completed = min(completed + 1, len(tasks))
                yield {"todo": tasks, "completed": completed, "status": "notification-service 발송 중..."}
                r = await client.post(f"{self.notification_base_url}/notifications/send", json=payload)
                r.raise_for_status()
                data = r.json()
                completed = min(completed + 1, len(tasks))
                final = f"[mock] {channel} 알림 발송 완료 (id={data.get('id')})"
                yield {"todo": tasks, "completed": completed, "status": "완료", "final": final, "done": True}
                return

        # fallback
        yield {"todo": tasks, "completed": len(tasks), "status": "완료", "final": message, "done": True}


orchestrator = Orchestrator.from_env()


