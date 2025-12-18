"""
TaskPlannerAgent (LLM 기반).

역할:
- 복잡한 사용자 요청을 실행 가능한 서브태스크로 분해
- 태스크 실행 순서/의존성 결정
- 관찰(observation) 결과에 따라 동적으로 재계획(replan)

주의: 이 에이전트는 툴을 직접 실행하지 않습니다. (실행은 `ToolExecutor`가 담당)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import json


def _extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}
    return {}


def _safe_str(x: Any, limit: int = 1800) -> str:
    try:
        s = json.dumps(x, ensure_ascii=False)
    except Exception:
        s = str(x)
    return s if len(s) <= limit else (s[:limit] + "…")


@dataclass
class TaskPlannerAgent:
    """
    LLM 기반 계획(Plan) / 재계획(Replan) 에이전트.
    """

    llm_chat_fn: Any  # callable(prompt:str)->str
    tools_prompt: str

    def plan(self, *, user_input: str, intent: str, apis: List[str], recent_turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = (
            "당신은 태스크 플래너 에이전트입니다.\n"
            "목표: 사용자 요청을 실행 가능한 서브태스크로 분해하고, 각 태스크의 실행 순서/의존성을 포함한 계획을 JSON으로 작성하세요.\n"
            "반드시 JSON만 출력.\n\n"
            "사용 가능한 도구:\n"
            f"{self.tools_prompt}\n\n"
            f"의도(intent): {intent}\n"
            f"API 후보: {apis}\n\n"
            f"최근 대화(참고): {_safe_str(recent_turns, 800)}\n\n"
            "반환 형식(키 고정):\n"
            '{ "tasks":[{"id":"t1","text":"...","tool":"weather.get|...|none","args":{...},"depends_on":["t0"],"produces":"짧게"}], "final_step":"tN" }\n\n'
            "규칙:\n"
            "- tool이 필요 없으면 \"none\"\n"
            "- args는 가능한 채워서 주고, 불확실하면 비워두고 실행기(Executor)가 채우게 하세요.\n"
            "- depends_on은 task id 리스트\n\n"
            f"사용자 요청: {user_input}\n"
        )
        return _extract_json_object(self.llm_chat_fn(prompt))

    def replan(
        self,
        *,
        user_input: str,
        intent: str,
        apis: List[str],
        current_tasks: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = (
            "당신은 태스크 플래너 에이전트입니다. 실행 중 관찰 결과를 반영해 계획을 업데이트하세요.\n"
            "반드시 JSON만 출력.\n\n"
            "사용 가능한 도구:\n"
            f"{self.tools_prompt}\n\n"
            f"의도(intent): {intent}\n"
            f"API 후보: {apis}\n\n"
            f"현재 계획(tasks): {_safe_str(current_tasks, 1400)}\n\n"
            f"관찰(observations): {_safe_str(observations, 1400)}\n\n"
            "반환 형식(키 고정):\n"
            '{ "tasks":[{"id":"t1","text":"...","tool":"...|none","args":{...},"depends_on":["..."],"produces":"..."}], "final_step":"tN" }\n\n'
            f"사용자 요청: {user_input}\n"
        )
        return _extract_json_object(self.llm_chat_fn(prompt))


