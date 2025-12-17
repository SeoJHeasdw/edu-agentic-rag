from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

app = FastAPI(title="Mock Calendar API", version="1.0.0")


class Event(BaseModel):
    id: Optional[str] = None
    title: str
    start_time: str
    end_time: Optional[str] = None
    type: str = "meeting"
    location: Optional[str] = None
    attendees: List[str] = []
    description: Optional[str] = None
    created_at: Optional[str] = None


class EventCreate(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    type: str = "meeting"
    location: Optional[str] = None
    attendees: List[str] = []
    description: Optional[str] = None


class DaySchedule(BaseModel):
    date: str
    events: List[Event]
    total_events: int
    free_time_slots: List[str]


def calculate_free_time(events: List[Event]) -> List[str]:
    busy_hours = set()
    for event in events:
        try:
            start_hour = int(event.start_time.split(":")[0])
            if 9 <= start_hour < 18:
                busy_hours.add(start_hour)
        except Exception:
            continue
    free_slots = []
    for hour in range(9, 18):
        if hour not in busy_hours:
            free_slots.append(f"{hour:02d}:00-{hour+1:02d}:00")
    return free_slots


CALENDAR_DATA = {
    "today": [
        Event(
            id="evt001",
            title="팀 스탠드업 미팅",
            start_time="09:00",
            end_time="09:30",
            type="meeting",
            location="회의실 A",
            attendees=["김개발", "박디자인", "이기획"],
            created_at=datetime.now().isoformat(),
        ),
        Event(
            id="evt002",
            title="프로젝트 리뷰",
            start_time="14:00",
            end_time="15:00",
            type="review",
            location="회의실 B",
            attendees=["최팀장", "김개발"],
            created_at=datetime.now().isoformat(),
        ),
    ],
    "tomorrow": [
        Event(
            id="evt003",
            title="클라이언트 미팅",
            start_time="10:00",
            end_time="11:30",
            type="external",
            location="외부 미팅룸",
            attendees=["김대표", "박부장"],
            created_at=datetime.now().isoformat(),
        )
    ],
}


@app.get("/")
async def root():
    return {"service": "calendar-service", "status": "running"}


@app.get("/calendar/today", response_model=DaySchedule)
async def get_today_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    events = CALENDAR_DATA.get("today", [])
    return DaySchedule(date=today, events=events, total_events=len(events), free_time_slots=calculate_free_time(events))


@app.get("/calendar/tomorrow", response_model=DaySchedule)
async def get_tomorrow_schedule():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    events = CALENDAR_DATA.get("tomorrow", [])
    return DaySchedule(date=tomorrow, events=events, total_events=len(events), free_time_slots=calculate_free_time(events))


@app.get("/calendar/date/{target_date}", response_model=DaySchedule)
async def get_schedule_by_date(target_date: str):
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")
    events = CALENDAR_DATA.get(target_date, [])
    return DaySchedule(date=target_date, events=events, total_events=len(events), free_time_slots=calculate_free_time(events))


@app.post("/calendar/events", response_model=Event)
async def create_event(event_data: EventCreate):
    new_event = Event(
        id=str(uuid.uuid4())[:8],
        title=event_data.title,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        type=event_data.type,
        location=event_data.location,
        attendees=event_data.attendees,
        description=event_data.description,
        created_at=datetime.now().isoformat(),
    )
    CALENDAR_DATA.setdefault("today", []).append(new_event)
    return new_event


@app.get("/calendar/summary")
async def get_calendar_summary():
    total_events = sum(len(events) for events in CALENDAR_DATA.values())
    return {
        "total_events": total_events,
        "today_events": len(CALENDAR_DATA.get("today", [])),
        "tomorrow_events": len(CALENDAR_DATA.get("tomorrow", [])),
        "summary": f"총 {total_events}개 일정",
    }

"""
Calendar service (mock) - FastAPI app.
Derived from code/example/mock_apis/calendar_api.py
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

app = FastAPI(title="Calendar Service (Mock)", version="1.0.0")


class Event(BaseModel):
    id: Optional[str] = None
    title: str
    start_time: str
    end_time: Optional[str] = None
    type: str = "meeting"
    location: Optional[str] = None
    attendees: List[str] = []
    description: Optional[str] = None
    created_at: Optional[str] = None


class EventCreate(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    type: str = "meeting"
    location: Optional[str] = None
    attendees: List[str] = []
    description: Optional[str] = None


class DaySchedule(BaseModel):
    date: str
    events: List[Event]
    total_events: int
    free_time_slots: List[str]


CALENDAR_DATA: Dict[str, List[Event]] = {
    "today": [
        Event(
            id="evt001",
            title="팀 스탠드업 미팅",
            start_time="09:00",
            end_time="09:30",
            type="meeting",
            location="회의실 A",
            attendees=["김개발", "박디자인", "이기획"],
            created_at=datetime.now().isoformat(),
        ),
        Event(
            id="evt002",
            title="프로젝트 리뷰",
            start_time="14:00",
            end_time="15:00",
            type="review",
            location="회의실 B",
            attendees=["최팀장", "김개발"],
            created_at=datetime.now().isoformat(),
        ),
    ],
    "tomorrow": [
        Event(
            id="evt003",
            title="클라이언트 미팅",
            start_time="10:00",
            end_time="11:30",
            type="external",
            location="외부 미팅룸",
            attendees=["김대표", "박부장"],
            created_at=datetime.now().isoformat(),
        )
    ],
}


def calculate_free_time(events: List[Event]) -> List[str]:
    busy_hours = []
    for e in events:
        start_hour = int(e.start_time.split(":")[0])
        if 9 <= start_hour < 18:
            busy_hours.append(start_hour)
    free = []
    for hour in range(9, 18):
        if hour not in busy_hours:
            free.append(f"{hour:02d}:00-{hour+1:02d}:00")
    return free


@app.get("/")
async def root():
    return {"service": "calendar-service", "status": "running"}


@app.get("/calendar/today", response_model=DaySchedule)
async def today():
    d = datetime.now().strftime("%Y-%m-%d")
    events = CALENDAR_DATA.get("today", [])
    return DaySchedule(date=d, events=events, total_events=len(events), free_time_slots=calculate_free_time(events))


@app.get("/calendar/tomorrow", response_model=DaySchedule)
async def tomorrow():
    d = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    events = CALENDAR_DATA.get("tomorrow", [])
    return DaySchedule(date=d, events=events, total_events=len(events), free_time_slots=calculate_free_time(events))


@app.get("/calendar/date/{target_date}", response_model=DaySchedule)
async def by_date(target_date: str):
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")
    events = CALENDAR_DATA.get(target_date, [])
    return DaySchedule(
        date=target_date, events=events, total_events=len(events), free_time_slots=calculate_free_time(events)
    )


@app.get("/calendar/events", response_model=List[Event])
async def all_events():
    out: List[Event] = []
    for _, events in CALENDAR_DATA.items():
        out.extend(events)
    return out


@app.get("/calendar/events/{event_id}", response_model=Event)
async def get_event(event_id: str):
    for _, events in CALENDAR_DATA.items():
        for e in events:
            if e.id == event_id:
                return e
    raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다")


@app.post("/calendar/events", response_model=Event)
async def create_event(event_data: EventCreate):
    new_event = Event(
        id=str(uuid.uuid4())[:8],
        title=event_data.title,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        type=event_data.type,
        location=event_data.location,
        attendees=event_data.attendees,
        description=event_data.description,
        created_at=datetime.now().isoformat(),
    )
    CALENDAR_DATA.setdefault("today", []).append(new_event)
    return new_event


@app.get("/calendar/free-time/{target_date}")
async def free_time(target_date: str):
    events = CALENDAR_DATA.get(target_date, [])
    free = calculate_free_time(events)
    return {
        "date": target_date,
        "free_time_slots": free,
        "total_free_hours": len(free),
        "recommendation": "가장 긴 빈 시간: " + (free[0] if free else "없음"),
    }


@app.get("/calendar/summary")
async def summary():
    total_events = sum(len(events) for events in CALENDAR_DATA.values())
    return {
        "total_events": total_events,
        "today_events": len(CALENDAR_DATA.get("today", [])),
        "tomorrow_events": len(CALENDAR_DATA.get("tomorrow", [])),
        "summary": f"총 {total_events}개 일정",
    }

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import uuid


app = FastAPI(title="Calendar Service (Mock)", version="1.0.0")


class Event(BaseModel):
    id: Optional[str] = None
    title: str
    start_time: str
    end_time: Optional[str] = None
    type: str = "meeting"
    location: Optional[str] = None
    attendees: List[str] = []
    description: Optional[str] = None
    created_at: Optional[str] = None


class EventCreate(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    type: str = "meeting"
    location: Optional[str] = None
    attendees: List[str] = []
    description: Optional[str] = None


class DaySchedule(BaseModel):
    date: str
    events: List[Event]
    total_events: int
    free_time_slots: List[str]


CALENDAR_DATA = {
    "today": [
        Event(
            id="evt001",
            title="팀 스탠드업 미팅",
            start_time="09:00",
            end_time="09:30",
            type="meeting",
            location="회의실 A",
            attendees=["김개발", "박디자인", "이기획"],
            created_at=datetime.now().isoformat(),
        ),
        Event(
            id="evt002",
            title="프로젝트 리뷰",
            start_time="14:00",
            end_time="15:00",
            type="review",
            location="회의실 B",
            attendees=["최팀장", "김개발"],
            created_at=datetime.now().isoformat(),
        ),
    ],
    "tomorrow": [
        Event(
            id="evt003",
            title="클라이언트 미팅",
            start_time="10:00",
            end_time="11:30",
            type="external",
            location="외부 미팅룸",
            attendees=["김대표", "박부장"],
            created_at=datetime.now().isoformat(),
        )
    ],
}


def calculate_free_time(events: List[Event]) -> List[str]:
    busy_hours = []
    for event in events:
        try:
            start_hour = int(event.start_time.split(":")[0])
            if 9 <= start_hour < 18:
                busy_hours.append(start_hour)
        except Exception:
            continue
    free_slots = []
    for hour in range(9, 18):
        if hour not in busy_hours:
            free_slots.append(f"{hour:02d}:00-{hour+1:02d}:00")
    return free_slots


@app.get("/")
async def root():
    return {"service": "calendar-service", "status": "running"}


@app.get("/calendar/today", response_model=DaySchedule)
async def get_today_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    events = CALENDAR_DATA.get("today", [])
    return DaySchedule(date=today, events=events, total_events=len(events), free_time_slots=calculate_free_time(events))


@app.get("/calendar/tomorrow", response_model=DaySchedule)
async def get_tomorrow_schedule():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    events = CALENDAR_DATA.get("tomorrow", [])
    return DaySchedule(date=tomorrow, events=events, total_events=len(events), free_time_slots=calculate_free_time(events))


@app.post("/calendar/events", response_model=Event)
async def create_event(event_data: EventCreate):
    new_event = Event(
        id=str(uuid.uuid4())[:8],
        title=event_data.title,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        type=event_data.type,
        location=event_data.location,
        attendees=event_data.attendees,
        description=event_data.description,
        created_at=datetime.now().isoformat(),
    )
    CALENDAR_DATA.setdefault("today", []).append(new_event)
    return new_event


@app.get("/calendar/summary")
async def get_calendar_summary():
    total_events = sum(len(events) for events in CALENDAR_DATA.values())
    return {
        "total_events": total_events,
        "today_events": len(CALENDAR_DATA.get("today", [])),
        "tomorrow_events": len(CALENDAR_DATA.get("tomorrow", [])),
        "summary": f"총 {total_events}개 일정",
    }


@app.get("/calendar/free-time/{target_date}")
async def get_free_time(target_date: str):
    # For mock: if target_date not in dict, assume empty
    events = CALENDAR_DATA.get(target_date, [])
    free_slots = calculate_free_time(events)
    return {
        "date": target_date,
        "free_time_slots": free_slots,
        "total_free_hours": len(free_slots),
        "recommendation": "가장 긴 빈 시간: " + (free_slots[0] if free_slots else "없음"),
    }


