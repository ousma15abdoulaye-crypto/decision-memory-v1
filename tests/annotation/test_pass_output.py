"""PASS_OUTPUT_STANDARD — AnnotationPassOutput contract."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.annotation.pass_output import AnnotationPassOutput, PassError, PassRunStatus


def test_annotation_pass_output_roundtrip():
    rid = uuid4()
    t0 = datetime(2026, 3, 24, 12, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 3, 24, 12, 0, 1, tzinfo=UTC)
    out = AnnotationPassOutput(
        pass_name="pass_0_ingestion",
        pass_version="1.0.0",
        document_id="doc-1",
        run_id=rid,
        started_at=t0,
        completed_at=t1,
        status=PassRunStatus.SUCCESS,
        output_data={"normalized_text": "hello", "features": {"char_count": 5}},
        errors=[],
        metadata={"duration_ms": 12},
    )
    dumped = out.model_dump(mode="json")
    restored = AnnotationPassOutput.model_validate(dumped)
    assert restored.pass_name == "pass_0_ingestion"
    assert restored.status == PassRunStatus.SUCCESS
    assert restored.output_data["normalized_text"] == "hello"


def test_annotation_pass_output_rejects_invalid_pass_version_suffix():
    with pytest.raises(ValidationError):
        AnnotationPassOutput(
            pass_name="p",
            pass_version="1.0.0foo",
            document_id="d",
            run_id=uuid4(),
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            status=PassRunStatus.SUCCESS,
        )


def test_annotation_pass_output_rejects_naive_timestamps():
    t0 = datetime(2026, 3, 24, 12, 0, 0)
    t1 = datetime(2026, 3, 24, 12, 0, 1)
    with pytest.raises(ValidationError):
        AnnotationPassOutput(
            pass_name="p",
            pass_version="1.0.0",
            document_id="d",
            run_id=uuid4(),
            started_at=t0,
            completed_at=t1,
            status=PassRunStatus.SUCCESS,
        )


def test_annotation_pass_output_rejects_completed_before_started():
    t0 = datetime(2026, 3, 24, 12, 0, 1, tzinfo=UTC)
    t1 = datetime(2026, 3, 24, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        AnnotationPassOutput(
            pass_name="p",
            pass_version="1.0.0",
            document_id="d",
            run_id=uuid4(),
            started_at=t0,
            completed_at=t1,
            status=PassRunStatus.SUCCESS,
        )


def test_annotation_pass_output_with_errors():
    out = AnnotationPassOutput(
        pass_name="pass_0_5_quality_gate",
        pass_version="1.0.0",
        document_id="ls_task:99",
        run_id=uuid4(),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        status=PassRunStatus.FAILED,
        errors=[PassError(code="EMPTY_TEXT", message="No normalized text from Pass 0")],
    )
    assert len(out.errors) == 1
    assert out.errors[0].code == "EMPTY_TEXT"
