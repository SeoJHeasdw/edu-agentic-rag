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

import subprocess
import sys
import time
import socket
from pathlib import Path


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


def start_service(backend_dir: Path, svc: dict) -> subprocess.Popen[str] | None:
    name = svc["name"]
    port = svc["port"]
    cwd = backend_dir / svc["cwd"]

    if not cwd.exists():
        print(f"❌ {name}: directory not found: {cwd}")
        return None

    if not check_port_available(port):
        print(f"⚠️  {name}: port {port} is already in use, skipping")
        return None

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
            return p
        print(f"❌ {name} failed to start (exit={p.poll()})")
        return None
    except Exception as e:
        print(f"❌ {name} error: {e}")
        return None


def main() -> int:
    backend_dir = Path(__file__).resolve().parent

    # RAG prereqs (Qdrant) - we don't start it here, but we warn loudly.
    # Default config expects Qdrant on localhost:6333.
    if not check_port_listening("localhost", 6333):
        print(
            "⚠️  qdrant is not reachable at localhost:6333. "
            "rag-service /rag/query will return 503 until Qdrant is started.\n"
            "   Start Qdrant (Docker): docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant"
        )

    procs: list[tuple[dict, subprocess.Popen[str]]] = []
    for svc in SERVICES:
        p = start_service(backend_dir, svc)
        if p:
            procs.append((svc, p))

    if not procs:
        print("❌ no services started")
        return 1

    print("\n📋 running services:")
    for svc, _ in procs:
        print(f"- {svc['name']}: http://localhost:{svc['port']}")
    print("\n🛑 stop: Ctrl+C\n")

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


