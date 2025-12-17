"""
Weather agent (HTTP client) - calls weather-service.
Ported from code/example/agents/weather_agent.py but kept dependency-light.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import os

import httpx


@dataclass
class WeatherAgent:
    api_base_url: str = ""

    def __post_init__(self):
        if not self.api_base_url:
            self.api_base_url = os.getenv("WEATHER_SERVICE_URL", "http://localhost:8001").rstrip("/")

    async def get_current_weather(self, city: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.api_base_url}/weather/{city}")
            r.raise_for_status()
            return r.json()

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import httpx


@dataclass
class WeatherAgent:
    api_base_url: str = "http://localhost:8001"

    def get_current_weather(self, city: str) -> Dict[str, Any]:
        url = f"{self.api_base_url.rstrip('/')}/weather/{city}"
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url)
            r.raise_for_status()
            return r.json()

    def get_simple_weather(self, city: str) -> Dict[str, Any]:
        url = f"{self.api_base_url.rstrip('/')}/weather/current/{city}"
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url)
            r.raise_for_status()
            return r.json()

    def process_weather_request(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        city = (parameters.get("city") or "seoul").strip()
        request_type = parameters.get("type") or "simple"
        try:
            if request_type == "current":
                data = self.get_current_weather(city)
            else:
                data = self.get_simple_weather(city)
            return {"success": True, "agent": "WeatherAgent", "data": data}
        except Exception as e:
            return {"success": False, "agent": "WeatherAgent", "error": str(e)}


