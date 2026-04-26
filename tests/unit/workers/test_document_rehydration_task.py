from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.assembler.document_rehydration_service import (
    RehydrationResult,
    RehydrationStatus,
)


@pytest.mark.asyncio
async def test_rehydrate_bundle_document_raw_text_task_calls_service() -> None:
    from src.workers.arq_tasks import rehydrate_bundle_document_raw_text_task

    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    service = AsyncMock(
        return_value=RehydrationResult(
            status=RehydrationStatus.SUCCESS,
            workspace_id=str(workspace_id),
            document_id=str(document_id),
            raw_text_len=42,
            ocr_engine="none",
            ocr_confidence=1.0,
            updated=True,
        )
    )

    with patch(
        "src.assembler.document_rehydration_service."
        "rehydrate_bundle_document_raw_text",
        service,
    ):
        result = await rehydrate_bundle_document_raw_text_task(
            {}, str(workspace_id), str(document_id), force=True
        )

    service.assert_awaited_once_with(
        document_id=document_id,
        workspace_id=workspace_id,
        force=True,
    )
    assert result["status"] == "SUCCESS"
    assert result["raw_text_len"] == 42
    assert result["ocr_engine"] == "none"
    assert "duration_ms" in result
