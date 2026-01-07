"""
Backend smoke test (local).

다음 명령으로 시작된 로컬 마이크로서비스에 대해 간단한 HTTP 검사를 실행합니다.
  cd code/backend && python start_services.py

이 테스트의 목적:
- 반복 가능하고 자동화된 기본 기능 검사를 통해 "작동하는 것 같다"는 막연한 판단을 방지합니다.
- 개별 서비스와 하나의 통합 흐름
  (챗봇 서비스 -> 날씨 서비스 -> 알림 서비스)을 모두 검증합니다.

사용법:
  python smoke_test.py
  python smoke_test.py --base http://localhost
"""

# pyright: reportMissingImports=false

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def _ok(name: str, detail: str = "") -> CheckResult:
    return CheckResult(name=name, ok=True, detail=detail)


def _fail(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, ok=False, detail=detail)


async def _get_json(client: httpx.AsyncClient, url: str) -> Tuple[int, Any]:
    r = await client.get(url)
    status = r.status_code
    try:
        return status, r.json()
    except Exception:
        return status, r.text


async def _post_json(client: httpx.AsyncClient, url: str, payload: Dict[str, Any]) -> Tuple[int, Any]:
    r = await client.post(url, json=payload)
    status = r.status_code
    try:
        return status, r.json()
    except Exception:
        return status, r.text


async def check_services(base: str = "http://localhost") -> list[CheckResult]:
    # Ports are defined in code/backend/start_services.py
    urls = {
        "chatbot": f"{base}:8000",
        "weather": f"{base}:8001",
        "calendar": f"{base}:8002",
        "file": f"{base}:8003",
        "notification": f"{base}:8004",
        "rag": f"{base}:8005",
    }

    results: list[CheckResult] = []
    timeout = httpx.Timeout(5.0, connect=2.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Basic health/root checks
        status, body = await _get_json(client, f"{urls['chatbot']}/health")
        if status == 200 and isinstance(body, dict) and body.get("status") == "healthy":
            results.append(_ok("chatbot /health"))
        else:
            results.append(_fail("chatbot /health", f"status={status} body={body}"))

        for svc in ("weather", "calendar", "file", "notification"):
            status, body = await _get_json(client, f"{urls[svc]}/")
            if status == 200 and isinstance(body, dict) and body.get("status") == "running":
                results.append(_ok(f"{svc} /"))
            else:
                results.append(_fail(f"{svc} /", f"status={status} body={body}"))

        # rag-service can be degraded (503) if Qdrant is not running; accept both.
        status, body = await _get_json(client, f"{urls['rag']}/health")
        if status == 200:
            results.append(_ok("rag /health", "qdrant_ok"))
        elif status == 503:
            results.append(_ok("rag /health", "degraded (qdrant not running)"))
        else:
            results.append(_fail("rag /health", f"status={status} body={body}"))

        # Functional checks
        status, body = await _get_json(client, f"{urls['weather']}/weather/%EC%84%9C%EC%9A%B8")  # 서울
        if status == 200 and isinstance(body, dict) and body.get("city") and "temperature" in body:
            results.append(_ok("weather /weather/서울", f"{body.get('condition')} {body.get('temperature')}°C"))
        else:
            results.append(_fail("weather /weather/서울", f"status={status} body={body}"))

        # Integration: chatbot -> (weather + notification) with composite intent
        payload = {"message": "오늘 날씨를 팀한테 알려줘", "conversation_id": None, "messages": None}
        status, body = await _post_json(client, f"{urls['chatbot']}/api/chat", payload)
        msg = ""
        if isinstance(body, dict):
            msg = str(body.get("message") or "")
        if status == 200 and ("알림 발송" in msg or "알림" in msg) and ("날씨" in msg):
            results.append(_ok("integration chatbot -> weather -> notification", msg.replace("\n", " ")[:140]))
        else:
            results.append(_fail("integration chatbot -> weather -> notification", f"status={status} body={body}"))

        # notification history should be accessible (at least returns 200)
        status, body = await _get_json(client, f"{urls['notification']}/notifications/history?limit=5")
        if status == 200 and isinstance(body, dict) and "notifications" in body:
            results.append(_ok("notification /notifications/history", f"returned={len(body.get('notifications') or [])}"))
        else:
            results.append(_fail("notification /notifications/history", f"status={status} body={body}"))

    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost", help="Base host URL without port (default: http://localhost)")
    args = ap.parse_args()

    results = asyncio.run(check_services(base=args.base))

    failed = [r for r in results if not r.ok]
    for r in results:
        status = "OK " if r.ok else "FAIL"
        detail = f" - {r.detail}" if r.detail else ""
        print(f"[{status}] {r.name}{detail}")

    if failed:
        print(f"\n❌ smoke test failed: {len(failed)}/{len(results)} checks failed")
        return 1
    print(f"\n✅ smoke test passed: {len(results)}/{len(results)} checks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


