#!/usr/bin/env python3
"""
Start backend microservices locally (Python launcher).

Inspired by code/example/start_apis.py, but targets the repo microservice layout:
- chatbot-service (8000)
- weather-service (8001)
- calendar-service (8002)
- file-service (8003)
- notification-service (8004)

Usage:
  cd code/backend
  python start_services.py
"""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys
import time
import socket
from pathlib import Path
import os


SERVICES = [
    {"name": "chatbot-service", "cwd": "chatbot-service", "port": 8000, "app": "main:app"},
    {"name": "weather-service", "cwd": "weather-service", "port": 8001, "app": "main:app"},
    {"name": "calendar-service", "cwd": "calendar-service", "port": 8002, "app": "main:app"},
    {"name": "file-service", "cwd": "file-service", "port": 8003, "app": "main:app"},
    {"name": "notification-service", "cwd": "notification-service", "port": 8004, "app": "main:app"},
    {"name": "rag-service", "cwd": "rag-service", "port": 8005, "app": "main:app"},
]


def check_port_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", port))
            return True
    except OSError:
        return False


def check_port_listening(host: str, port: int, timeout_s: float = 0.25) -> bool:
    """
    Returns True if something is listening on host:port.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


@dataclass(frozen=True)
class ServiceStartResult:
    svc: dict
    proc: subprocess.Popen[str] | None
    status: str  # started | dir_missing | failed | skipped_port_in_use
    detail: str = ""


def _list_listening_pids(port: int) -> list[int]:
    """
    Best-effort: return PIDs listening on localhost TCP port.
    Uses `lsof` (macOS/Linux). Returns [] if lsof isn't available.
    """
    try:
        r = subprocess.run(
            ["lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []

    pids: list[int] = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    # de-dupe but keep stable order
    seen: set[int] = set()
    uniq: list[int] = []
    for pid in pids:
        if pid not in seen:
            seen.add(pid)
            uniq.append(pid)
    return uniq


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # exists but we can't signal it
        return True


def _stop_listeners_on_port(port: int, *, timeout_s: float = 2.0) -> tuple[bool, str]:
    """
    Attempt to stop any process listening on port.
    Returns (True, detail) if the port is free afterwards, else (False, detail).
    """
    pids = _list_listening_pids(port)
    if not pids:
        return True, "no existing listener"

    print(f"🧹 port {port} is in use by pid(s) {pids}. Stopping them...")

    # Try graceful stop first
    for pid in pids:
        try:
            subprocess.run(["kill", "-TERM", str(pid)], check=False, capture_output=True, text=True)
        except Exception:
            pass

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if check_port_available(port):
            return True, f"stopped existing listener pid(s) {pids}"
        # If all PIDs are gone, give the OS a tiny breath to release the socket.
        if all(not _pid_exists(pid) for pid in pids):
            time.sleep(0.15)
        else:
            time.sleep(0.1)

    # Force kill if still around
    for pid in pids:
        try:
            subprocess.run(["kill", "-KILL", str(pid)], check=False, capture_output=True, text=True)
        except Exception:
            pass
    time.sleep(0.2)

    if check_port_available(port):
        return True, f"killed existing listener pid(s) {pids}"
    return False, f"port still in use (pid(s) {pids})"


def start_service(backend_dir: Path, svc: dict) -> ServiceStartResult:
    name = svc["name"]
    port = svc["port"]
    cwd = backend_dir / svc["cwd"]

    if not cwd.exists():
        print(f"❌ {name}: directory not found: {cwd}")
        return ServiceStartResult(svc=svc, proc=None, status="dir_missing", detail=f"directory not found: {cwd}")

    if not check_port_available(port):
        ok, detail = _stop_listeners_on_port(port)
        if not ok:
            print(f"⚠️  {name}: port {port} is still in use, skipping ({detail})")
            return ServiceStartResult(svc=svc, proc=None, status="skipped_port_in_use", detail=detail)

    env = dict(**{**dict(**(dict())), **dict()})
    env.update(dict(**(dict())))
    env.update(dict(**(dict())))
    env.update(dict(**(dict())))

    # Base env + PYTHONPATH:
    # - keeps backend root importable (shared_config/shared_utils)
    # - each service can stay self-contained within its directory
    import os

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env["PYTHONPATH"] = f"{cwd}:{backend_dir}:{env.get('PYTHONPATH','')}".strip(":")

    # Service discovery for chatbot-service/orchestrator
    env.setdefault("WEATHER_SERVICE_URL", "http://localhost:8001")
    env.setdefault("CALENDAR_SERVICE_URL", "http://localhost:8002")
    env.setdefault("FILE_SERVICE_URL", "http://localhost:8003")
    env.setdefault("NOTIFICATION_SERVICE_URL", "http://localhost:8004")
    env.setdefault("RAG_SERVICE_URL", "http://localhost:8005")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        svc["app"],
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
        "--reload",
    ]

    print(f"🚀 starting {name} on :{port} (cwd={cwd})")
    try:
        p = subprocess.Popen(cmd, cwd=str(cwd), env=env)
        time.sleep(0.8)
        if p.poll() is None:
            print(f"✅ {name} started")
            return ServiceStartResult(svc=svc, proc=p, status="started")
        print(f"❌ {name} failed to start (exit={p.poll()})")
        return ServiceStartResult(svc=svc, proc=None, status="failed", detail=f"exit={p.poll()}")
    except Exception as e:
        print(f"❌ {name} error: {e}")
        return ServiceStartResult(svc=svc, proc=None, status="failed", detail=str(e))


def main() -> int:
    backend_dir = Path(__file__).resolve().parent

    # RAG prereqs (Qdrant) - we don't start it here, but we warn loudly.
    # Default config expects Qdrant on localhost:6333.
    if not check_port_listening("localhost", 6333):
        print(
            "⚠️  qdrant is not reachable at localhost:6333. "
            "rag-service /rag/query will return 503 until Qdrant is started.\n"
            "   Start Qdrant (Docker, recommended volume outside repo):\n"
            "     mkdir -p ~/.local/share/edu-agentic-rag/qdrant_storage\n"
            "     docker run --name edu-qdrant --rm -p 6333:6333 -p 6334:6334 "
            "-v ~/.local/share/edu-agentic-rag/qdrant_storage:/qdrant/storage qdrant/qdrant"
        )

    results: list[ServiceStartResult] = []
    procs: list[tuple[dict, subprocess.Popen[str]]] = []
    for svc in SERVICES:
        res = start_service(backend_dir, svc)
        results.append(res)
        if res.proc:
            procs.append((svc, res.proc))

    print("\n📋 running services:")
    for res in results:
        svc = res.svc
        name = svc["name"]
        port = svc["port"]
        if res.proc:
            print(f"- {name}: http://localhost:{port}")
        else:
            reason = res.detail or res.status
            print(f"- {name}: 안뜸 ({reason})")
    print("\n🛑 stop: Ctrl+C\n")

    if not procs:
        print("❌ no services started")
        return 1

    try:
        while True:
            time.sleep(1)
            for svc, p in procs:
                if p.poll() is not None:
                    print(f"⚠️  {svc['name']} exited unexpectedly (code={p.poll()})")
                    return 1
    except KeyboardInterrupt:
        print("\n🛑 stopping services...")
        for svc, p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        time.sleep(1)
        for svc, p in procs:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
        print("✅ stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())


