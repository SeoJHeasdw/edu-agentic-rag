"""
런타임 엔트리포인트(외부 노출용).

구현은 당분간 `services/orchestrator.py`에 두되,
외부(라우터/API)에서는 아키텍처 용어에 맞춰 `agent_runtime` 이름으로만 접근하게 합니다.
"""

from __future__ import annotations

from services.orchestrator import Orchestrator

# Single runtime instance used by API
agent_runtime = Orchestrator.from_env()


