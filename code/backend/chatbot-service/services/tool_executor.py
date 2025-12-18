"""
툴 실행기 (실행/Execute + ReAct 스타일의 인자 보완 + 세션 캐시).

역할:
- 계획된 툴 호출을 순서대로 실행
- 관찰(observation) 기록
- 세션 캐시를 사용하여 툴 결과 재사용
- 실패 시 플래너 재계획(replan) 트리거 (Planner & Execute 패턴/흐름)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

from agents.context_manager import context_manager


DEFAULT_TOOL_SPECS: List[Dict[str, Any]] = [
    {"name": "weather.get", "description": "특정 도시의 현재 날씨를 조회한다.", "args_schema": {"city": "string (e.g., 서울)"}, "ttl": 300},
    {"name": "calendar.get", "description": "오늘/내일 일정을 조회한다.", "args_schema": {"when": "string (today|tomorrow)"}, "ttl": 60},
    {"name": "calendar.create", "description": "일정을 생성한다.", "args_schema": {"title": "string", "start_time": "string (HH:MM)"}, "ttl": None},
    {"name": "file.search", "description": "파일/문서를 키워드로 검색한다.", "args_schema": {"q": "string"}, "ttl": 120},
    {
        "name": "notification.send",
        "description": "팀/수신자에게 알림을 보낸다(모의).",
        "args_schema": {"title": "string", "message": "string", "recipient": "string", "channel": "string (slack|email|sms)"},
        "ttl": None,
    },
    {"name": "rag.query", "description": "RAG 서비스에 질의하여 관련 문서를 찾는다.", "args_schema": {"query": "string", "top_k": "int"}, "ttl": 120},
]


def tools_prompt(tool_specs: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    플래너(Planner)에게 보여줄 “툴 레지스트리” 문자열을 렌더링합니다. (MCP의 tool list와 유사)
    """
    specs = tool_specs or DEFAULT_TOOL_SPECS
    return "\n".join([f"- {t['name']}: {t.get('description','')} | args={t.get('args_schema',{})}" for t in specs])


def tool_defs(tool_specs: Optional[List[Dict[str, Any]]] = None) -> List["ToolDef"]:
    """
    툴 레지스트리(dict)를 실행기용 `ToolDef` 리스트로 변환합니다.
    """
    specs = tool_specs or DEFAULT_TOOL_SPECS
    return [ToolDef(name=t["name"], args_schema=t.get("args_schema") or {}, ttl_seconds=t.get("ttl")) for t in specs]


@dataclass
class ToolDef:
    name: str
    args_schema: Dict[str, Any]
    ttl_seconds: Optional[float] = None


@dataclass
class ToolExecutor:
    weather_base_url: str
    calendar_base_url: str
    file_base_url: str
    notification_base_url: str
    rag_base_url: str
    tools: List[ToolDef]

    def tool_schema(self, tool_name: str) -> Dict[str, Any]:
        for t in self.tools:
            if t.name == tool_name:
                return t.args_schema
        return {}

    def tool_ttl(self, tool_name: str) -> Optional[float]:
        for t in self.tools:
            if t.name == tool_name:
                return t.ttl_seconds
        return None

    async def call_tool(self, client: httpx.AsyncClient, tool: str, args: Dict[str, Any]) -> Any:
        if tool == "weather.get":
            city = (args.get("city") or "서울").strip()
            r = await client.get(f"{self.weather_base_url}/weather/{city}")
            r.raise_for_status()
            return r.json()

        if tool == "calendar.get":
            when = (args.get("when") or "today").strip().lower()
            endpoint = "/calendar/tomorrow" if when in ("tomorrow", "내일") else "/calendar/today"
            r = await client.get(f"{self.calendar_base_url}{endpoint}")
            r.raise_for_status()
            return r.json()

        if tool == "calendar.create":
            title = (args.get("title") or "새 일정").strip()
            start_time = (args.get("start_time") or "09:00").strip()
            r = await client.post(f"{self.calendar_base_url}/calendar/events", json={"title": title, "start_time": start_time})
            r.raise_for_status()
            return r.json()

        if tool == "file.search":
            q = (args.get("q") or "").strip()
            r = await client.get(f"{self.file_base_url}/files/search", params={"q": q})
            r.raise_for_status()
            return r.json()

        if tool == "notification.send":
            payload = {
                "title": (args.get("title") or "알림").strip(),
                "message": (args.get("message") or "").strip(),
                "recipient": (args.get("recipient") or "team").strip(),
                "channel": (args.get("channel") or "slack").strip(),
            }
            r = await client.post(f"{self.notification_base_url}/notifications/send", json=payload)
            r.raise_for_status()
            return r.json()

        if tool == "rag.query":
            query = (args.get("query") or "").strip()
            top_k = int(args.get("top_k") or 5)
            r = await client.post(f"{self.rag_base_url}/rag/query", json={"query": query, "top_k": top_k})
            r.raise_for_status()
            return r.json()

        raise ValueError(f"Unknown tool: {tool}")

    async def execute_plan(
        self,
        *,
        user_input: str,
        session_id: str,
        tasks: List[Dict[str, Any]],
        fill_args_fn,  # callable(tool:str, schema:dict, observations:list[dict])->dict(args)
        replan_fn=None,  # callable(tasks, observations)->new_tasks
        max_replans: int = 2,
    ) -> Tuple[List[Dict[str, Any]], List[str], List[Dict[str, Any]]]:
        """
        Returns: (observations, used_tools, final_tasks)
        """
        observations: List[Dict[str, Any]] = []
        used_tools: List[str] = []
        current_tasks = list(tasks)

        replans = 0
        async with httpx.AsyncClient(timeout=10.0) as client:
            i = 0
            while i < len(current_tasks):
                t = current_tasks[i]
                tool = str(t.get("tool") or "none").strip()
                args = t.get("args") if isinstance(t.get("args"), dict) else {}

                if tool and tool != "none":
                    if not args:
                        args = fill_args_fn(tool, self.tool_schema(tool), list(observations)) or {}

                    cache_key = context_manager.make_cache_key(tool, args)
                    ttl = self.tool_ttl(tool)
                    cached = context_manager.get_cached_tool_result(session_id, cache_key, ttl_seconds=ttl)
                    if cached is not None:
                        observations.append({"task_id": t.get("id"), "tool": tool, "args": args, "cached": True, "result": cached})
                    else:
                        try:
                            result = await self.call_tool(client, tool, args)
                            context_manager.set_cached_tool_result(session_id, cache_key, result)
                            observations.append({"task_id": t.get("id"), "tool": tool, "args": args, "cached": False, "result": result})
                        except Exception as e:
                            observations.append({"task_id": t.get("id"), "tool": tool, "args": args, "cached": False, "error": str(e)})

                            if replan_fn and replans < max_replans:
                                new_tasks = replan_fn(current_tasks, observations)
                                if isinstance(new_tasks, list) and new_tasks:
                                    current_tasks = list(new_tasks)
                                    replans += 1
                                    i = 0
                                    continue

                    used_tools.append(tool)
                else:
                    observations.append({"task_id": t.get("id"), "note": str(t.get("text") or "")})

                i += 1

        return observations, sorted(list(set(used_tools))), current_tasks


