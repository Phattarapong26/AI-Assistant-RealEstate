"""Zero-Bullet Conversational Engine.

The system prompt forbids lists, but a model can still slip. This module is the
last line of defence: it rewrites any list-like markup the model produced back
into flowing prose before the answer ever reaches the customer.
"""

from __future__ import annotations

import re
from typing import List

BULLET_PATTERN = re.compile(r"^\s*(?:[-*•‣▪◦✓→]+|\d+[.)]|[ก-ฮ][.)])\s+")
HEADING_PATTERN = re.compile(r"^\s*#{1,6}\s*")
FIELD_LABEL_PATTERN = re.compile(
    r"(ราคา|ประเภท|โครงการ|ทำเล|ตำแหน่ง|รูปแบบ|จุดเด่น|ข้อดี|ข้อควรพิจารณา)\s*[:：]\s*"
)
MAX_PARAGRAPHS = 6


def _strip_inline_markup(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", text)
    text = text.replace("|", " ")
    return text


def enforce_paragraph_style(answer: str, max_paragraphs: int = MAX_PARAGRAPHS) -> str:
    """Collapse any list formatting into at most `max_paragraphs` paragraphs."""
    if not answer:
        return answer

    answer = _strip_inline_markup(answer.replace("\r\n", "\n"))

    paragraphs: List[str] = []
    buffer: List[str] = []

    def flush() -> None:
        if buffer:
            merged = " ".join(part.strip() for part in buffer if part.strip())
            merged = re.sub(r"\s{2,}", " ", merged).strip()
            if merged:
                paragraphs.append(merged)
            buffer.clear()

    for raw_line in answer.split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            flush()
            continue

        was_list_item = bool(BULLET_PATTERN.match(line))
        line = BULLET_PATTERN.sub("", line)
        line = HEADING_PATTERN.sub("", line)
        line = FIELD_LABEL_PATTERN.sub(lambda m: f"{m.group(1)} ", line)
        line = line.strip()
        if not line:
            continue

        if was_list_item and buffer:
            previous = buffer[-1].rstrip()
            if previous.endswith(":") or previous.endswith("："):
                buffer[-1] = previous[:-1].rstrip()
            elif previous and previous[-1] not in ".!?ๆ":
                buffer[-1] = previous + " และ"
        buffer.append(line)

    flush()

    if not paragraphs:
        return answer.strip()

    if len(paragraphs) > max_paragraphs:
        head = paragraphs[: max_paragraphs - 1]
        tail = " ".join(paragraphs[max_paragraphs - 1 :])
        paragraphs = head + [tail]

    cleaned = "\n\n".join(paragraphs)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()
