from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import mimetypes

app = FastAPI(title="Mock File Manager API", version="1.0.0")


class FileInfo(BaseModel):
    id: str
    name: str
    path: str
    size: int
    type: str  # file
    mime_type: Optional[str] = None
    created_at: str
    modified_at: str
    tags: List[str] = []
    content_preview: Optional[str] = None


class SearchResult(BaseModel):
    files: List[FileInfo]
    total_matches: int
    query: str
    search_time_ms: int


class FileCreate(BaseModel):
    name: str
    content: str
    tags: List[str] = []
    directory: str = "/"


FILE_SYSTEM: Dict[str, Dict] = {
    "files": {
        "f001": FileInfo(
            id="f001",
            name="프로젝트_계획서.md",
            path="/documents/프로젝트_계획서.md",
            size=2048,
            type="file",
            mime_type="text/markdown",
            created_at="2024-01-15T09:00:00",
            modified_at="2024-01-20T14:30:00",
            tags=["프로젝트", "계획", "문서"],
            content_preview="# 프로젝트 계획서\n\n## 개요\n이 프로젝트는 AI 챗봇 시스템을 구축하는 것을 목표로 합니다...",
        ),
        "f002": FileInfo(
            id="f002",
            name="API_명세서.json",
            path="/api/API_명세서.json",
            size=1524,
            type="file",
            mime_type="application/json",
            created_at="2024-01-10T11:00:00",
            modified_at="2024-01-18T16:45:00",
            tags=["API", "명세", "개발"],
            content_preview='{"version":"1.0.0","endpoints":[{"path":"/weather","method":"GET"}]}',
        ),
    }
}


@app.get("/")
async def root():
    return {"service": "file-service", "status": "running"}


@app.get("/files/search", response_model=SearchResult)
async def search_files(q: str, tags: Optional[str] = None, file_type: Optional[str] = None):
    start = datetime.now()
    query_lower = q.lower()
    query_words = query_lower.split()

    matched: List[FileInfo] = []
    for fi in FILE_SYSTEM["files"].values():
        score = 0
        name_lower = fi.name.lower()
        for w in query_words:
            if w and w in name_lower:
                score += 1
            if any(w and w in t.lower() for t in fi.tags):
                score += 1
            if fi.content_preview and w and w in fi.content_preview.lower():
                score += 1
        if score > 0:
            matched.append(fi)

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        matched = [f for f in matched if any(t in f.tags for t in tag_list)]

    if file_type:
        matched = [f for f in matched if f.mime_type and file_type.lower() in f.mime_type.lower()]

    ms = int((datetime.now() - start).total_seconds() * 1000)
    return SearchResult(files=matched, total_matches=len(matched), query=q, search_time_ms=ms)


@app.get("/files/{file_id}", response_model=FileInfo)
async def get_file(file_id: str):
    if file_id not in FILE_SYSTEM["files"]:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    return FILE_SYSTEM["files"][file_id]


@app.get("/files/content/{file_id}")
async def get_file_content(file_id: str):
    if file_id not in FILE_SYSTEM["files"]:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    fi = FILE_SYSTEM["files"][file_id]
    return {"file_id": file_id, "name": fi.name, "content": fi.content_preview or "", "size": fi.size, "mime_type": fi.mime_type}


@app.post("/files", response_model=FileInfo)
async def create_file(file_data: FileCreate):
    file_id = str(uuid.uuid4())[:8]
    mime_type, _ = mimetypes.guess_type(file_data.name)
    if not mime_type:
        mime_type = "text/plain"
    path = f"{file_data.directory.rstrip('/')}/{file_data.name}"
    now = datetime.now().isoformat()
    fi = FileInfo(
        id=file_id,
        name=file_data.name,
        path=path,
        size=len(file_data.content),
        type="file",
        mime_type=mime_type,
        created_at=now,
        modified_at=now,
        tags=file_data.tags,
        content_preview=(file_data.content[:200] + "...") if len(file_data.content) > 200 else file_data.content,
    )
    FILE_SYSTEM["files"][file_id] = fi
    return fi

"""
File service (mock) - FastAPI app.
Derived from code/example/mock_apis/file_manager_api.py
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import mimetypes

app = FastAPI(title="File Service (Mock)", version="1.0.0")


class FileInfo(BaseModel):
    id: str
    name: str
    path: str
    size: int
    type: str
    mime_type: Optional[str] = None
    created_at: str
    modified_at: str
    tags: List[str] = []
    content_preview: Optional[str] = None


class FileCreate(BaseModel):
    name: str
    content: str
    tags: List[str] = []
    directory: str = "/"


FILE_SYSTEM: Dict[str, Dict] = {
    "files": {},
    "directories": {
        "/": ["documents", "api", "meetings", "assets"],
        "/documents": ["프로젝트_계획서.md", "사용자_가이드.pdf"],
        "/api": ["API_명세서.json"],
        "/meetings": ["회의록_0125.txt"],
        "/assets": [],
    },
}


def _seed_files():
    def mk(fid: str, name: str, path: str, mime: str, tags: List[str], preview: str, size: int):
        now = datetime.now().isoformat()
        FILE_SYSTEM["files"][fid] = FileInfo(
            id=fid,
            name=name,
            path=path,
            size=size,
            type="file",
            mime_type=mime,
            created_at=now,
            modified_at=now,
            tags=tags,
            content_preview=preview,
        )

    mk(
        "f001",
        "프로젝트_계획서.md",
        "/documents/프로젝트_계획서.md",
        "text/markdown",
        ["프로젝트", "계획", "문서"],
        "# 프로젝트 계획서\n\n## 개요\n이 프로젝트는 AI 챗봇 시스템을 구축하는 것을 목표로 합니다...",
        2048,
    )
    mk(
        "f002",
        "API_명세서.json",
        "/api/API_명세서.json",
        "application/json",
        ["API", "명세", "개발"],
        "{\n  \"version\": \"1.0.0\",\n  \"endpoints\": [{\"path\": \"/weather\", \"method\": \"GET\"}] ...",
        1524,
    )
    mk(
        "f003",
        "회의록_0125.txt",
        "/meetings/회의록_0125.txt",
        "text/plain",
        ["회의록", "팀미팅"],
        "2024-01-25 팀 미팅\n\n참석자: 김개발, 박디자인, 이기획\n\n안건:\n1. 프로젝트 진행 상황...",
        892,
    )


_seed_files()


@app.get("/")
async def root():
    return {"service": "file-service", "status": "running"}


@app.get("/files", response_model=List[FileInfo])
async def list_files():
    return list(FILE_SYSTEM["files"].values())


@app.get("/files/search")
async def search_files(q: str, tags: Optional[str] = None, file_type: Optional[str] = None):
    start = datetime.now()
    query_words = q.lower().split()
    matched: List[FileInfo] = []
    for f in FILE_SYSTEM["files"].values():
        score = 0
        name_lower = f.name.lower()
        for w in query_words:
            if w in name_lower:
                score += 1
            if any(w in t.lower() for t in f.tags):
                score += 1
            if f.content_preview and w in f.content_preview.lower():
                score += 1
        if score > 0:
            matched.append(f)

    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        matched = [f for f in matched if any(t in f.tags for t in tag_list)]

    if file_type:
        matched = [f for f in matched if (f.mime_type or "").lower().find(file_type.lower()) >= 0]

    search_time_ms = int((datetime.now() - start).total_seconds() * 1000)
    return {"files": matched, "total_matches": len(matched), "query": q, "search_time_ms": search_time_ms}


@app.get("/files/{file_id}", response_model=FileInfo)
async def get_file(file_id: str):
    if file_id not in FILE_SYSTEM["files"]:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    return FILE_SYSTEM["files"][file_id]


@app.get("/files/content/{file_id}")
async def get_file_content(file_id: str):
    if file_id not in FILE_SYSTEM["files"]:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    f: FileInfo = FILE_SYSTEM["files"][file_id]
    content = f.content_preview or ""
    return {"file_id": file_id, "name": f.name, "content": content, "size": len(content), "mime_type": f.mime_type}


@app.get("/directories", response_model=Dict[str, List[str]])
async def directory_structure():
    return FILE_SYSTEM["directories"]


@app.post("/files", response_model=FileInfo)
async def create_file(file_data: FileCreate):
    file_id = str(uuid.uuid4())[:8]
    mime_type, _ = mimetypes.guess_type(file_data.name)
    if not mime_type:
        mime_type = "text/plain"
    now = datetime.now().isoformat()
    new_file = FileInfo(
        id=file_id,
        name=file_data.name,
        path=f"{file_data.directory.rstrip('/')}/{file_data.name}",
        size=len(file_data.content),
        type="file",
        mime_type=mime_type,
        created_at=now,
        modified_at=now,
        tags=file_data.tags,
        content_preview=file_data.content[:200] + "..." if len(file_data.content) > 200 else file_data.content,
    )
    FILE_SYSTEM["files"][file_id] = new_file
    return new_file

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional


app = FastAPI(title="File Service (Mock)", version="1.0.0")


class FileInfo(BaseModel):
    id: str
    name: str
    path: str
    size: int
    type: str  # file, directory
    mime_type: Optional[str] = None
    created_at: str
    modified_at: str
    tags: List[str] = []
    content_preview: Optional[str] = None


class SearchResult(BaseModel):
    files: List[FileInfo]
    total_matches: int
    query: str
    search_time_ms: int


FILES: Dict[str, FileInfo] = {
    "f001": FileInfo(
        id="f001",
        name="프로젝트_계획서.md",
        path="/documents/프로젝트_계획서.md",
        size=2048,
        type="file",
        mime_type="text/markdown",
        created_at="2024-01-15T09:00:00",
        modified_at="2024-01-20T14:30:00",
        tags=["프로젝트", "계획", "문서"],
        content_preview="# 프로젝트 계획서 ...",
    ),
    "f002": FileInfo(
        id="f002",
        name="API_명세서.json",
        path="/api/API_명세서.json",
        size=1524,
        type="file",
        mime_type="application/json",
        created_at="2024-01-10T11:00:00",
        modified_at="2024-01-18T16:45:00",
        tags=["API", "명세", "개발"],
        content_preview='{"version":"1.0.0","endpoints":[...]}',
    ),
}


@app.get("/")
async def root():
    return {"service": "file-service", "status": "running"}


@app.get("/files/search", response_model=SearchResult)
async def search_files(q: str, tags: Optional[str] = None, file_type: Optional[str] = None):
    start = datetime.now()
    query_words = q.lower().split()
    matched: List[FileInfo] = []
    for f in FILES.values():
        score = 0
        name = f.name.lower()
        preview = (f.content_preview or "").lower()
        for w in query_words:
            if w in name:
                score += 1
            if any(w in t.lower() for t in f.tags):
                score += 1
            if w in preview:
                score += 1
        if score > 0:
            matched.append(f)

    if tags:
        wanted = [t.strip() for t in tags.split(",") if t.strip()]
        matched = [f for f in matched if any(t in f.tags for t in wanted)]

    if file_type:
        ft = file_type.lower()
        matched = [f for f in matched if (f.mime_type or "").lower().find(ft) >= 0]

    ms = int((datetime.now() - start).total_seconds() * 1000)
    return SearchResult(files=matched, total_matches=len(matched), query=q, search_time_ms=ms)


@app.get("/files/content/{file_id}")
async def get_file_content(file_id: str):
    if file_id not in FILES:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    f = FILES[file_id]
    content = f"Mock content for {f.name}\n\n{f.content_preview or ''}"
    return {"file_id": file_id, "name": f.name, "content": content, "size": len(content), "mime_type": f.mime_type}


