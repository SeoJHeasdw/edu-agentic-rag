"""
Notification service (mock) - FastAPI app.

IMPORTANT:
- Keep a single FastAPI `app` instance.
- Keep `/notifications/send` because chatbot-service orchestrator calls it.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Notification Service (Mock)", version="1.0.0")


class NotificationCreate(BaseModel):
    title: str
    message: str
    recipient: str
    type: str = "info"
    channel: str = "email"  # email | slack | sms | push
    priority: str = "normal"  # low | normal | high | urgent
    scheduled_at: Optional[str] = None


class Notification(BaseModel):
    id: str
    title: str
    message: str
    recipient: str
    type: str
    channel: str
    priority: str
    status: str
    created_at: str
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None


NOTIFICATIONS: Dict[str, Notification] = {}
HISTORY: List[Notification] = []


def _simulate_delivery_success(channel: str, priority: str) -> float:
    base = {"email": 0.95, "slack": 0.98, "sms": 0.92, "push": 0.88}.get(channel, 0.85)
    mult = {"low": 0.9, "normal": 1.0, "high": 1.05, "urgent": 1.1}.get(priority, 1.0)
    return min(base * mult, 1.0)


@app.get("/")
async def root():
    return {"service": "notification-service", "status": "running"}


@app.post("/notifications/send", response_model=Notification)
async def send_notification(notification_data: NotificationCreate):
    notification_id = str(uuid.uuid4())[:8]
    success_rate = _simulate_delivery_success(notification_data.channel, notification_data.priority)
    status = "sent" if success_rate > 0.8 else "failed"
    now = datetime.now().isoformat()

    n = Notification(
        id=notification_id,
        title=notification_data.title,
        message=notification_data.message,
        recipient=notification_data.recipient,
        type=notification_data.type,
        channel=notification_data.channel,
        priority=notification_data.priority,
        status=status,
        created_at=now,
        sent_at=now if status == "sent" else None,
        delivered_at=(datetime.now() + timedelta(seconds=2)).isoformat() if status == "sent" else None,
    )
    NOTIFICATIONS[notification_id] = n
    HISTORY.append(n)
    return n


@app.get("/notifications/{notification_id}", response_model=Notification)
async def get_notification(notification_id: str):
    if notification_id not in NOTIFICATIONS:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
    return NOTIFICATIONS[notification_id]


@app.get("/notifications/history")
async def get_notification_history(limit: int = 50):
    sorted_history = sorted(HISTORY, key=lambda x: x.created_at, reverse=True)
    return {
        "notifications": sorted_history[:limit],
        "total_count": len(HISTORY),
        "returned_count": min(limit, len(HISTORY)),
    }


@app.get("/notifications/stats")
async def get_notification_stats():
    total = len(HISTORY)
    if total == 0:
        return {"total_sent": 0, "success_rate": 0.0, "channel_distribution": {}, "type_distribution": {}}
    successful = len([n for n in HISTORY if n.status == "sent"])
    channel_dist: Dict[str, int] = {}
    type_dist: Dict[str, int] = {}
    for n in HISTORY:
        channel_dist[n.channel] = channel_dist.get(n.channel, 0) + 1
        type_dist[n.type] = type_dist.get(n.type, 0) + 1
    return {
        "total_sent": total,
        "success_rate": round(successful / total * 100, 2),
        "channel_distribution": channel_dist,
        "type_distribution": type_dist,
    }


