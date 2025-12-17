"""
Notification agent (HTTP client) - calls notification-service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import os

import httpx


@dataclass
class NotificationAgent:
    api_base_url: str = ""

    def __post_init__(self):
        if not self.api_base_url:
            self.api_base_url = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8004").rstrip("/")

    async def send(self, title: str, message: str, recipient: str, channel: str = "email") -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"title": title, "message": message, "recipient": recipient, "channel": channel}
            r = await client.post(f"{self.api_base_url}/notifications/send", json=payload)
            r.raise_for_status()
            return r.json()

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx


@dataclass
class NotificationAgent:
    api_base_url: str = "http://localhost:8004"

    def send_slack(self, channel: str, text: str, username: str = "ChatBot", icon: str = ":robot_face:") -> Dict[str, Any]:
        payload = {"channel": channel, "text": text, "username": username, "icon": icon, "attachments": []}
        with httpx.Client(timeout=10.0) as client:
            r = client.post(f"{self.api_base_url.rstrip('/')}/notifications/slack", json=payload)
            r.raise_for_status()
            return r.json()

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        payload = {"to": to, "subject": subject, "body": body, "cc": [], "attachments": []}
        with httpx.Client(timeout=10.0) as client:
            r = client.post(f"{self.api_base_url.rstrip('/')}/notifications/email", json=payload)
            r.raise_for_status()
            return r.json()

    def send_sms(self, phone: str, message: str, priority: str = "normal") -> Dict[str, Any]:
        params = {"phone": phone, "message": message, "priority": priority}
        with httpx.Client(timeout=10.0) as client:
            r = client.post(f"{self.api_base_url.rstrip('/')}/notifications/sms", params=params)
            r.raise_for_status()
            return r.json()

    def process_notification_request(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        channel = (parameters.get("channel") or "slack").lower()
        message = parameters.get("message") or parameters.get("text") or ""
        if not message:
            return {"success": False, "agent": "NotificationAgent", "error": "message is required"}
        try:
            if channel == "email":
                to = parameters.get("to") or parameters.get("recipient") or "test@example.com"
                subject = parameters.get("subject") or parameters.get("title") or "알림"
                data = self.send_email(to=to, subject=subject, body=message)
            elif channel == "sms":
                phone = parameters.get("phone") or parameters.get("recipient") or "010-0000-0000"
                data = self.send_sms(phone=phone, message=message, priority=parameters.get("priority") or "normal")
            else:
                slack_channel = parameters.get("recipient") or parameters.get("channel_name") or "#general"
                data = self.send_slack(channel=slack_channel, text=message)
            return {"success": True, "agent": "NotificationAgent", "data": data}
        except Exception as e:
            return {"success": False, "agent": "NotificationAgent", "error": str(e)}


