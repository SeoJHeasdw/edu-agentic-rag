"""
Calendar agent (HTTP client) - calls calendar-service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import os

import httpx


@dataclass
class CalendarAgent:
    api_base_url: str = ""

    def __post_init__(self):
        if not self.api_base_url:
            self.api_base_url = os.getenv("CALENDAR_SERVICE_URL", "http://localhost:8002").rstrip("/")

    async def get_today(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.api_base_url}/calendar/today")
            r.raise_for_status()
            return r.json()

    async def get_tomorrow(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.api_base_url}/calendar/tomorrow")
            r.raise_for_status()
            return r.json()

    async def create_event(self, title: str, start_time: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"title": title, "start_time": start_time}
            r = await client.post(f"{self.api_base_url}/calendar/events", json=payload)
            r.raise_for_status()
            return r.json()

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import httpx


@dataclass
class CalendarAgent:
    api_base_url: str = "http://localhost:8002"

    def get_today(self) -> Dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{self.api_base_url.rstrip('/')}/calendar/today")
            r.raise_for_status()
            return r.json()

    def get_tomorrow(self) -> Dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{self.api_base_url.rstrip('/')}/calendar/tomorrow")
            r.raise_for_status()
            return r.json()

    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(f"{self.api_base_url.rstrip('/')}/calendar/events", json=event_data)
            r.raise_for_status()
            return r.json()

    def process_calendar_request(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        action = parameters.get("action") or "query"
        when = parameters.get("date") or "today"
        try:
            if action == "create":
                event = {
                    "title": parameters.get("title") or "새 일정",
                    "start_time": parameters.get("start_time") or parameters.get("time") or "09:00",
                    "end_time": parameters.get("end_time"),
                    "type": parameters.get("type") or "meeting",
                    "location": parameters.get("location"),
                    "attendees": parameters.get("attendees") or [],
                    "description": parameters.get("description"),
                }
                data = self.create_event(event)
            else:
                if str(when).lower() in ("tomorrow", "내일"):
                    data = self.get_tomorrow()
                else:
                    data = self.get_today()
            return {"success": True, "agent": "CalendarAgent", "data": data}
        except Exception as e:
            return {"success": False, "agent": "CalendarAgent", "error": str(e)}


