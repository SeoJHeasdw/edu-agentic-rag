"""
rag-service 전용 청킹 로직.

목표:
- md는 헤더 기반으로 섹션을 나누고, 섹션 내부는 문단 단위로 chunk_size를 맞춥니다.
- 코드블록(```` ... `````)은 가능하면 깨지지 않도록 같은 덩어리로 유지합니다.
- 각 청크에 섹션 경로(heading_path) 등 메타데이터를 같이 반환합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
import re


_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Chunk:
    text: str
    meta: Dict[str, Any]


def _split_md_blocks(text: str) -> List[Tuple[str, str]]:
    """
    마크다운을 '텍스트 블록'과 '코드블록'으로 나눕니다.
    반환: [(kind, block_text)] where kind in {"text", "code"}
    """

    lines = (text or "").splitlines()
    out: List[Tuple[str, str]] = []
    buf: List[str] = []
    in_code = False

    def flush(kind: str) -> None:
        nonlocal buf
        if not buf:
            return
        out.append((kind, "\n".join(buf).strip("\n")))
        buf = []

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                # 코드블록 종료 라인 포함 후 flush
                buf.append(line)
                flush("code")
                in_code = False
            else:
                # 기존 텍스트를 먼저 flush하고 코드 시작
                flush("text")
                in_code = True
                buf.append(line)
            continue

        buf.append(line)

    # 잔여 flush
    flush("code" if in_code else "text")
    return out


def _paragraphs(block_text: str) -> List[str]:
    """
    빈 줄 기준으로 문단 분리.
    """

    parts = [p.strip() for p in re.split(r"\n\s*\n", block_text or "") if p.strip()]
    return parts


def chunk_markdown(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
) -> List[Chunk]:
    """
    마크다운 전용 청킹.

    - 헤더(# ... ######)를 만나면 섹션 경계를 갱신합니다.
    - 섹션 내부는 문단을 누적해서 chunk_size를 넘지 않게 나눕니다.
    - overlap은 문자 단위로 직전 chunk의 tail을 다음 chunk 앞에 붙이는 방식입니다.
    """

    blocks = _split_md_blocks(text)
    heading_stack: List[Tuple[int, str]] = []  # (level, title)

    def set_heading(level: int, title: str) -> None:
        # level보다 깊은 헤더를 pop
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, title.strip()))

    def heading_path() -> str:
        return " > ".join([h[1] for h in heading_stack if h[1]])

    chunks: List[Chunk] = []

    def emit(text_piece: str, *, section_path: str) -> None:
        t = (text_piece or "").strip()
        if not t:
            return
        meta = {"heading_path": section_path}
        chunks.append(Chunk(text=t, meta=meta))

    # 섹션 누적 버퍼
    buf = ""
    cur_section = ""

    def flush_buf() -> None:
        nonlocal buf
        if buf.strip():
            emit(buf, section_path=cur_section)
        buf = ""

    for kind, btxt in blocks:
        if kind == "code":
            # 코드블록은 되도록 통째로 넣되, 너무 길면 그냥 분할(최소한으로)
            code = btxt.strip("\n")
            if not code.strip():
                continue
            if len(code) > chunk_size:
                # 긴 코드블록: hard split
                flush_buf()
                start = 0
                while start < len(code):
                    part = code[start : start + chunk_size]
                    emit(part, section_path=cur_section)
                    start += chunk_size
            else:
                # 버퍼가 차있고 합치면 넘치면 flush 후 추가
                if buf and (len(buf) + 2 + len(code) > chunk_size):
                    flush_buf()
                buf = f"{buf}\n\n{code}".strip() if buf else code
            continue

        # 텍스트 블록: 라인별로 헤더 체크
        lines = (btxt or "").splitlines()
        tmp: List[str] = []
        for line in lines:
            m = _MD_HEADING_RE.match(line.strip())
            if m:
                # 헤더를 만나면 이전 tmp를 처리하고 섹션 변경
                if tmp:
                    # tmp를 문단으로 잘라 chunk_size에 맞게 buf 누적
                    for p in _paragraphs("\n".join(tmp)):
                        if not buf:
                            buf = p
                        elif len(buf) + 2 + len(p) <= chunk_size:
                            buf = f"{buf}\n\n{p}"
                        else:
                            flush_buf()
                            buf = p
                    tmp = []
                # 기존 buf도 섹션 경계로 flush
                flush_buf()
                level = len(m.group(1))
                title = m.group(2).strip()
                set_heading(level, title)
                cur_section = heading_path()
                continue
            tmp.append(line)

        if tmp:
            for p in _paragraphs("\n".join(tmp)):
                if not buf:
                    buf = p
                elif len(buf) + 2 + len(p) <= chunk_size:
                    buf = f"{buf}\n\n{p}"
                else:
                    flush_buf()
                    buf = p

    flush_buf()

    # overlap(문자 단위)
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    out: List[Chunk] = []
    prev_tail = ""
    for ch in chunks:
        if prev_tail:
            out.append(Chunk(text=prev_tail + ch.text, meta=dict(ch.meta)))
        else:
            out.append(ch)
        t = ch.text
        prev_tail = t[-overlap:] if len(t) > overlap else t
    return out


def chunk_text_fallback(text: str, *, chunk_size: int, overlap: int) -> List[Chunk]:
    """
    md가 아닌 일반 텍스트용 fallback 청킹(문단 기반).
    """

    parts = _paragraphs(text or "")
    raw: List[str] = []
    buf = ""
    for p in parts:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= chunk_size:
            buf = f"{buf}\n\n{p}"
        else:
            raw.append(buf)
            buf = p
    if buf:
        raw.append(buf)

    if overlap > 0 and len(raw) > 1:
        out_text: List[str] = []
        prev_tail = ""
        for c in raw:
            if prev_tail:
                out_text.append(prev_tail + c)
            else:
                out_text.append(c)
            prev_tail = c[-overlap:] if len(c) > overlap else c
        raw = out_text

    return [Chunk(text=t, meta={}) for t in raw if t.strip()]


