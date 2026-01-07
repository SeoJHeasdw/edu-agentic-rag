"""
백엔드 공용 유틸 (backend 루트 모듈).

- 이 파일은 "가벼운 공용 기능"만 남깁니다:
  - 텍스트 유틸(간단 토크나이즈/청킹)
  - 문서 파일 탐색(iter_docs_files)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import os
import re

from shared_config import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
)


_TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]+")


class TextUtils:
    @staticmethod
    def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
        # paragraph-first chunking with soft limit
        parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: List[str] = []
        buf = ""
        for p in parts:
            if not buf:
                buf = p
                continue
            if len(buf) + 2 + len(p) <= chunk_size:
                buf = f"{buf}\n\n{p}"
            else:
                chunks.append(buf)
                buf = p
        if buf:
            chunks.append(buf)

        # add overlap by simple tail prefix (character overlap)
        if overlap <= 0 or len(chunks) <= 1:
            return chunks
        out: List[str] = []
        prev_tail = ""
        for c in chunks:
            if prev_tail:
                out.append(prev_tail + c)
            else:
                out.append(c)
            prev_tail = c[-overlap:] if len(c) > overlap else c
        return out

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return [t.lower() for t in _TOKEN_RE.findall(text)]

def iter_docs_files(docs_root: Path, exts: Tuple[str, ...] = (".md", ".txt")) -> Iterable[Path]:
    for p in docs_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


