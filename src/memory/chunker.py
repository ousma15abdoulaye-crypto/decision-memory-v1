"""Semantic chunker — splits documents into logical sections.

Strategy: section-header detection + sliding window fallback.
No external dependencies beyond stdlib + re.
"""

from __future__ import annotations

import re
from typing import Any

from src.memory.chunker_models import DocumentChunk

_SECTION_RE = re.compile(
    r"^(?:#{1,4}\s+.+|(?:ARTICLE|SECTION|CHAPITRE|TITRE|ANNEXE)\s+\w+.*)",
    re.IGNORECASE | re.MULTILINE,
)

_DEFAULT_MAX_CHARS = 2000
_DEFAULT_OVERLAP_CHARS = 200


class SemanticChunker:
    """Splits text into chunks by section headers, with sliding-window fallback."""

    def __init__(
        self,
        max_chars: int = _DEFAULT_MAX_CHARS,
        overlap_chars: int = _DEFAULT_OVERLAP_CHARS,
    ) -> None:
        if max_chars < 100:
            raise ValueError("max_chars must be >= 100")
        if overlap_chars < 0:
            raise ValueError("overlap_chars must be >= 0")
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars

    def chunk(self, text: str) -> list[DocumentChunk]:
        if not text.strip():
            return []
        sections = self._split_by_headers(text)
        chunks: list[DocumentChunk] = []
        idx = 0
        for title, body, start in sections:
            for sub in self._sliding_window(body):
                chunks.append(
                    DocumentChunk(
                        chunk_index=idx,
                        text=sub["text"],
                        start_char=start + sub["offset"],
                        end_char=start + sub["offset"] + len(sub["text"]),
                        section_title=title,
                        token_count=len(sub["text"].split()),
                    )
                )
                idx += 1
        return chunks

    def _split_by_headers(self, text: str) -> list[tuple[str | None, str, int]]:
        matches = list(_SECTION_RE.finditer(text))
        if not matches:
            return [(None, text, 0)]
        sections: list[tuple[str | None, str, int]] = []
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()]
            if preamble.strip():
                sections.append((None, preamble, 0))
        for i, m in enumerate(matches):
            title = m.group().strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end]
            if body.strip():
                sections.append((title, body, start))
        return sections

    def _sliding_window(self, text: str) -> list[dict[str, Any]]:
        if len(text) <= self._max_chars:
            return [{"text": text.strip(), "offset": 0}]
        windows: list[dict[str, Any]] = []
        pos = 0
        while pos < len(text):
            end = min(pos + self._max_chars, len(text))
            snippet = text[pos:end].strip()
            if snippet:
                windows.append({"text": snippet, "offset": pos})
            pos += self._max_chars - self._overlap_chars
            if pos >= len(text):
                break
        return windows
