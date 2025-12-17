from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

app = FastAPI(title="Mock Notification API", version="1.0.0")


class NotificationCreate(BaseModel):
    title: str
    message: str
    recipient: str
    type: str = "info"
    channel: str = "email"
    priority: str = "normal"
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


def simulate_delivery_success(channel: str, priority: str) -> float:
    base = {"email": 0.95, "slack": 0.98, "sms": 0.92, "push": 0.88}.get(channel, 0.85)
    mult = {"low": 0.9, "normal": 1.0, "high": 1.05, "urgent": 1.1}.get(priority, 1.0)
    return min(base * mult, 1.0)


@app.get("/")
async def root():
    return {"service": "notification-service", "status": "running"}


@app.post("/notifications/send", response_model=Notification)
async def send_notification(notification_data: NotificationCreate):
    notification_id = str(uuid.uuid4())[:8]
    success_rate = simulate_delivery_success(notification_data.channel, notification_data.priority)
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
        delivered_at=(datetime.now() + timedelta(seconds=5)).isoformat() if status == "sent" else None,
    )
    NOTIFICATIONS[notification_id] = n
    HISTORY.append(n)
    return n


@app.get("/notifications/history")
async def get_notification_history(limit: int = 50):
    sorted_history = sorted(HISTORY, key=lambda x: x.created_at, reverse=True)
    return {"notifications": sorted_history[:limit], "total_count": len(HISTORY), "returned_count": min(limit, len(HISTORY))}


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


@app.get("/notifications/{notification_id}", response_model=Notification)
async def get_notification(notification_id: str):
    if notification_id not in NOTIFICATIONS:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
    return NOTIFICATIONS[notification_id]

"""
Notification service (mock) - FastAPI app.
Derived from code/example/mock_apis/notification_api.py
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

app = FastAPI(title="Notification Service (Mock)", version="1.0.0")


class NotificationCreate(BaseModel):
    title: str
    message: str
    recipient: str
    type: str = "info"
    channel: str = "email"
    priority: str = "normal"
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


class SlackMessage(BaseModel):
    channel: str
    text: str
    username: Optional[str] = "ChatBot"
    icon: Optional[str] = ":robot_face:"
    attachments: List[Dict] = []


class EmailMessage(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[List[str]] = []
    attachments: Optional[List[str]] = []


NOTIFICATIONS: Dict[str, Notification] = {}
NOTIFICATION_HISTORY: List[Notification] = []


@app.get("/")
async def root():
    return {"service": "notification-service", "status": "running"}


@app.post("/notifications/send", response_model=Notification)
async def send_notification(notification_data: NotificationCreate):
    notification_id = str(uuid.uuid4())[:8]
    status = "sent"
    n = Notification(
        id=notification_id,
        title=notification_data.title,
        message=notification_data.message,
        recipient=notification_data.recipient,
        type=notification_data.type,
        channel=notification_data.channel,
        priority=notification_data.priority,
        status=status,
        created_at=datetime.now().isoformat(),
        sent_at=datetime.now().isoformat(),
        delivered_at=(datetime.now() + timedelta(seconds=2)).isoformat(),
    )
    NOTIFICATIONS[notification_id] = n
    NOTIFICATION_HISTORY.append(n)
    return n


@app.post("/notifications/slack")
async def send_slack(slack_data: SlackMessage):
    msg_id = str(uuid.uuid4())[:8]
    n = Notification(
        id=msg_id,
        title=f"Slack: {slack_data.channel}",
        message=slack_data.text,
        recipient=slack_data.channel,
        type="info",
        channel="slack",
        priority="normal",
        status="sent",
        created_at=datetime.now().isoformat(),
        sent_at=datetime.now().isoformat(),
        delivered_at=(datetime.now() + timedelta(seconds=2)).isoformat(),
    )
    NOTIFICATIONS[msg_id] = n
    NOTIFICATION_HISTORY.append(n)
    return {
        "message_id": msg_id,
        "channel": slack_data.channel,
        "text": slack_data.text,
        "username": slack_data.username,
        "status": "sent",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/notifications/email")
async def send_email(email_data: EmailMessage):
    email_id = str(uuid.uuid4())[:8]
    n = Notification(
        id=email_id,
        title=email_data.subject,
        message=email_data.body,
        recipient=email_data.to,
        type="info",
        channel="email",
        priority="normal",
        status="sent",
        created_at=datetime.now().isoformat(),
        sent_at=datetime.now().isoformat(),
        delivered_at=(datetime.now() + timedelta(seconds=10)).isoformat(),
    )
    NOTIFICATIONS[email_id] = n
    NOTIFICATION_HISTORY.append(n)
    return {"email_id": email_id, "to": email_data.to, "subject": email_data.subject, "status": "sent"}


@app.post("/notifications/sms")
async def send_sms(phone: str, message: str, priority: str = "normal"):
    if len(message) > 160:
        raise HTTPException(status_code=400, detail="SMS 메시지는 160자를 초과할 수 없습니다")
    sms_id = str(uuid.uuid4())[:8]
    n = Notification(
        id=sms_id,
        title="SMS 알림",
        message=message,
        recipient=phone,
        type="info",
        channel="sms",
        priority=priority,
        status="sent",
        created_at=datetime.now().isoformat(),
        sent_at=datetime.now().isoformat(),
        delivered_at=(datetime.now() + timedelta(seconds=3)).isoformat(),
    )
    NOTIFICATIONS[sms_id] = n
    NOTIFICATION_HISTORY.append(n)
    return {"sms_id": sms_id, "phone": phone, "message": message, "status": "sent"}


@app.get("/notifications/history")
async def history(limit: int = 50):
    sorted_history = sorted(NOTIFICATION_HISTORY, key=lambda x: x.created_at, reverse=True)
    return {"notifications": sorted_history[:limit], "total_count": len(NOTIFICATION_HISTORY)}


@app.get("/notifications/stats")
async def stats():
    total = len(NOTIFICATION_HISTORY)
    successful = len([n for n in NOTIFICATION_HISTORY if n.status == "sent"])
    return {"total_sent": total, "success_rate": (successful / total * 100) if total else 0.0}

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid


app = FastAPI(title="Notification Service (Mock)", version="1.0.0")


class SlackMessage(BaseModel):
    channel: str
    text: str
    username: Optional[str] = "ChatBot"
    icon: Optional[str] = ":robot_face:"
    attachments: List[Dict] = []


class EmailMessage(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[List[str]] = []
    attachments: Optional[List[str]] = []


@app.get("/")
async def root():
    return {"service": "notification-service", "status": "running"}


@app.post("/notifications/slack")
async def send_slack_message(slack_data: SlackMessage):
    message_id = str(uuid.uuid4())[:8]
    return {
        "message_id": message_id,
        "channel": slack_data.channel,
        "text": slack_data.text,
        "username": slack_data.username,
        "status": "sent",
        "timestamp": datetime.now().isoformat(),
        "response": f"메시지가 {slack_data.channel} 채널에 성공적으로 전송되었습니다.",
    }


@app.post("/notifications/email")
async def send_email(email_data: EmailMessage):
    email_id = str(uuid.uuid4())[:8]
    return {
        "email_id": email_id,
        "to": email_data.to,
        "subject": email_data.subject,
        "cc": email_data.cc,
        "status": "sent",
        "timestamp": datetime.now().isoformat(),
        "response": f"이메일이 {email_data.to}로 성공적으로 전송되었습니다.",
    }


@app.post("/notifications/sms")
async def send_sms(phone: str, message: str, priority: str = "normal"):
    if len(message) > 160:
        raise HTTPException(status_code=400, detail="SMS 메시지는 160자를 초과할 수 없습니다")
    sms_id = str(uuid.uuid4())[:8]
    return {
        "sms_id": sms_id,
        "phone": phone,
        "message": message,
        "priority": priority,
        "status": "sent",
        "timestamp": datetime.now().isoformat(),
        "response": f"SMS가 {phone}로 성공적으로 전송되었습니다.",
    }


