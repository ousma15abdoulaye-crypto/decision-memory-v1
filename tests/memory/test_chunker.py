"""Tests — SemanticChunker."""

from __future__ import annotations

import pytest

from src.memory.chunker import SemanticChunker
from src.memory.chunker_models import DocumentChunk


class TestChunkerBasic:
    def test_empty_text_returns_empty(self) -> None:
        ch = SemanticChunker()
        assert ch.chunk("") == []
        assert ch.chunk("   ") == []

    def test_short_text_single_chunk(self) -> None:
        ch = SemanticChunker()
        chunks = ch.chunk("Hello world, this is a test.")
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert "Hello" in chunks[0].text

    def test_section_headers_split(self) -> None:
        text = "# Section A\nContent A paragraph.\n# Section B\nContent B paragraph."
        ch = SemanticChunker()
        chunks = ch.chunk(text)
        assert len(chunks) >= 2
        titles = [c.section_title for c in chunks if c.section_title]
        assert any("Section A" in t for t in titles)
        assert any("Section B" in t for t in titles)

    def test_article_header_detected(self) -> None:
        text = "ARTICLE 1\nFirst article content.\nARTICLE 2\nSecond article."
        ch = SemanticChunker()
        chunks = ch.chunk(text)
        assert len(chunks) >= 2


class TestChunkerSlidingWindow:
    def test_long_text_produces_multiple_chunks(self) -> None:
        text = "A " * 2000
        ch = SemanticChunker(max_chars=200, overlap_chars=50)
        chunks = ch.chunk(text)
        assert len(chunks) > 1

    def test_overlap_between_chunks(self) -> None:
        text = "word " * 500
        ch = SemanticChunker(max_chars=100, overlap_chars=30)
        chunks = ch.chunk(text)
        assert len(chunks) >= 2


class TestChunkerValidation:
    def test_max_chars_too_low(self) -> None:
        with pytest.raises(ValueError, match="max_chars"):
            SemanticChunker(max_chars=10)

    def test_negative_overlap(self) -> None:
        with pytest.raises(ValueError, match="overlap_chars"):
            SemanticChunker(overlap_chars=-1)


class TestDocumentChunkModel:
    def test_extra_forbid(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extra"):
            DocumentChunk(
                chunk_index=0,
                text="t",
                start_char=0,
                end_char=1,
                rogue="x",
            )
