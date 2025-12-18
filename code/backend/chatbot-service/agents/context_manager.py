"""
대화 컨텍스트 매니저 (실습용: 외부 의존성 없이 동작).

`backend/agents/context_manager.py`에서 이동:
- `chatbot-service` 내부에서 오케스트레이션/에이전트 실습을 자급자족 형태로 유지하기 위함
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional
import threading
import time
import uuid
import json


@dataclass
class ConversationTurn:
    turn_id: str
    user_input: str
    assistant_response: str
    intent: str
    confidence: float
    apis_used: List[str]
    success: bool
    timestamp: str
    processing_time: float
    metadata: Dict[str, Any] | None = None


@dataclass
class SessionContext:
    session_id: str
    user_id: Optional[str]
    created_at: str
    last_activity: str
    conversation_turns: List[ConversationTurn]
    user_preferences: Dict[str, Any]
    active_topics: List[str]
    session_metadata: Dict[str, Any] | None = None


class ContextManager:
    def __init__(self, max_history_length: int = 20, session_timeout_hours: int = 24):
        self.max_history_length = max_history_length
        self.session_timeout_hours = session_timeout_hours

        self.active_sessions: Dict[str, SessionContext] = {}
        self.context_windows: Dict[str, Deque[ConversationTurn]] = {}

        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._start_cleanup_service()

    def _start_cleanup_service(self) -> None:
        def worker():
            while True:
                time.sleep(3600)
                try:
                    self.cleanup_expired_sessions()
                except Exception:
                    pass

        self._cleanup_thread = threading.Thread(target=worker, daemon=True)
        self._cleanup_thread.start()

    def create_session(self, user_id: Optional[str] = None, session_metadata: Optional[Dict[str, Any]] = None) -> str:
        with self._lock:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            now = datetime.now().isoformat()
            session = SessionContext(
                session_id=session_id,
                user_id=user_id,
                created_at=now,
                last_activity=now,
                conversation_turns=[],
                user_preferences={},
                active_topics=[],
                session_metadata=session_metadata or {},
            )
            self.active_sessions[session_id] = session
            self.context_windows[session_id] = deque(maxlen=self.max_history_length)
            return session_id

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        with self._lock:
            return self.active_sessions.get(session_id)

    def update_session_activity(self, session_id: str) -> None:
        with self._lock:
            if session_id in self.active_sessions:
                self.active_sessions[session_id].last_activity = datetime.now().isoformat()

    def add_conversation_turn(
        self,
        session_id: str,
        user_input: str,
        assistant_response: str,
        intent: str,
        confidence: float,
        apis_used: List[str],
        success: bool,
        processing_time: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        with self._lock:
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = SessionContext(
                    session_id=session_id,
                    user_id=None,
                    created_at=datetime.now().isoformat(),
                    last_activity=datetime.now().isoformat(),
                    conversation_turns=[],
                    user_preferences={},
                    active_topics=[],
                    session_metadata={},
                )
                self.context_windows[session_id] = deque(maxlen=self.max_history_length)

            session = self.active_sessions[session_id]
            turn_id = f"turn_{len(session.conversation_turns)}_{uuid.uuid4().hex[:6]}"
            turn = ConversationTurn(
                turn_id=turn_id,
                user_input=user_input,
                assistant_response=assistant_response,
                intent=intent,
                confidence=confidence,
                apis_used=apis_used,
                success=success,
                timestamp=datetime.now().isoformat(),
                processing_time=processing_time,
                metadata=metadata or {},
            )
            session.conversation_turns.append(turn)
            self.context_windows[session_id].append(turn)
            self.update_session_activity(session_id)
            return turn_id

    def get_recent_turns(self, session_id: str, n: int = 5) -> List[Dict[str, Any]]:
        with self._lock:
            window = list(self.context_windows.get(session_id, deque()))
            turns = window[-n:]
            return [
                {
                    "user_input": t.user_input,
                    "assistant_response": t.assistant_response,
                    "intent": t.intent,
                    "success": t.success,
                    "timestamp": t.timestamp,
                }
                for t in turns
            ]

    def export_session(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self.active_sessions.get(session_id)
            return asdict(session) if session else {}

    # ---- Tool-result cache (session-scoped) ----
    def _ensure_tool_cache(self, session_id: str) -> Dict[str, Any]:
        """
        Session-scoped cache for tool results.
        Structure: session.session_metadata["tool_cache"][cache_key] = {"ts": float, "value": Any}
        """
        with self._lock:
            session = self.active_sessions.get(session_id)
            if not session:
                # create minimal session if missing
                self.active_sessions[session_id] = SessionContext(
                    session_id=session_id,
                    user_id=None,
                    created_at=datetime.now().isoformat(),
                    last_activity=datetime.now().isoformat(),
                    conversation_turns=[],
                    user_preferences={},
                    active_topics=[],
                    session_metadata={},
                )
                self.context_windows[session_id] = deque(maxlen=self.max_history_length)
                session = self.active_sessions[session_id]

            session.session_metadata = session.session_metadata or {}
            tool_cache = session.session_metadata.get("tool_cache")
            if not isinstance(tool_cache, dict):
                tool_cache = {}
                session.session_metadata["tool_cache"] = tool_cache
            return tool_cache

    def make_cache_key(self, tool_name: str, args: Dict[str, Any]) -> str:
        try:
            args_s = json.dumps(args or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except Exception:
            args_s = str(args)
        return f"{tool_name}:{args_s}"

    def get_cached_tool_result(self, session_id: str, cache_key: str, ttl_seconds: Optional[float] = None) -> Optional[Any]:
        with self._lock:
            tool_cache = self._ensure_tool_cache(session_id)
            entry = tool_cache.get(cache_key)
            if not isinstance(entry, dict):
                return None
            ts = entry.get("ts")
            if not isinstance(ts, (int, float)):
                return None
            if ttl_seconds is not None and (time.time() - float(ts)) > float(ttl_seconds):
                return None
            return entry.get("value")

    def set_cached_tool_result(self, session_id: str, cache_key: str, value: Any) -> None:
        with self._lock:
            tool_cache = self._ensure_tool_cache(session_id)
            tool_cache[cache_key] = {"ts": time.time(), "value": value}

    def cleanup_expired_sessions(self) -> None:
        with self._lock:
            now = datetime.now()
            expired: List[str] = []
            for sid, session in self.active_sessions.items():
                last = datetime.fromisoformat(session.last_activity)
                if (now - last).total_seconds() > (self.session_timeout_hours * 3600):
                    expired.append(sid)
            for sid in expired:
                self.active_sessions.pop(sid, None)
                self.context_windows.pop(sid, None)


context_manager = ContextManager()


def get_or_create_session(session_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
    if session_id and context_manager.get_session(session_id):
        context_manager.update_session_activity(session_id)
        return session_id
    if session_id and not context_manager.get_session(session_id):
        context_manager.active_sessions[session_id] = SessionContext(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
            conversation_turns=[],
            user_preferences={},
            active_topics=[],
            session_metadata={},
        )
        context_manager.context_windows[session_id] = deque(maxlen=context_manager.max_history_length)
        return session_id
    return context_manager.create_session(user_id=user_id)


