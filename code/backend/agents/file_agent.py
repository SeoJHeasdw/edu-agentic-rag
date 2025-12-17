"""
File agent (HTTP client) - calls file-service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import os

import httpx


@dataclass
class FileAgent:
    api_base_url: str = ""

    def __post_init__(self):
        if not self.api_base_url:
            self.api_base_url = os.getenv("FILE_SERVICE_URL", "http://localhost:8003").rstrip("/")

    async def search(self, query: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self.api_base_url}/files/search", params={"q": query})
            r.raise_for_status()
            return r.json()

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import httpx


@dataclass
class FileAgent:
    api_base_url: str = "http://localhost:8003"

    def search_files(self, query: str, tags: Optional[str] = None, file_type: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"q": query}
        if tags:
            params["tags"] = tags
        if file_type:
            params["file_type"] = file_type
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{self.api_base_url.rstrip('/')}/files/search", params=params)
            r.raise_for_status()
            return r.json()

    def get_content(self, file_id: str) -> Dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{self.api_base_url.rstrip('/')}/files/content/{file_id}")
            r.raise_for_status()
            return r.json()

    def process_file_request(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        action = parameters.get("action") or "search"
        try:
            if action == "get_content":
                file_id = parameters.get("file_id") or ""
                if not file_id:
                    return {"success": False, "agent": "FileAgent", "error": "file_id is required"}
                data = self.get_content(file_id)
            else:
                query = parameters.get("query") or parameters.get("q") or ""
                if not query:
                    return {"success": False, "agent": "FileAgent", "error": "query is required"}
                data = self.search_files(query=query, tags=parameters.get("tags"), file_type=parameters.get("file_type"))
            return {"success": True, "agent": "FileAgent", "data": data}
        except Exception as e:
            return {"success": False, "agent": "FileAgent", "error": str(e)}


