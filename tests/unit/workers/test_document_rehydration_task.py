from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.assembler.document_m12_service import (
    M12ClassificationResult,
    M12ClassificationStatus,
)
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


@pytest.mark.asyncio
async def test_classify_bundle_document_m12_task_calls_service() -> None:
    from src.workers.arq_tasks import classify_bundle_document_m12_task

    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    service = Mock(
        return_value=M12ClassificationResult(
            status=M12ClassificationStatus.SUCCESS,
            workspace_id=str(workspace_id),
            document_id=str(document_id),
            raw_text_len=42,
            m12_doc_kind="offer_combined",
            m12_confidence=0.8,
            m12_evidence=["source=classify_document_type_for_pass_minus_one"],
            updated=True,
        )
    )

    with patch(
        "src.assembler.document_m12_service.classify_bundle_document_m12",
        service,
    ):
        result = await classify_bundle_document_m12_task(
            {}, str(workspace_id), str(document_id), force=True
        )

    service.assert_called_once_with(
        document_id=document_id,
        workspace_id=workspace_id,
        force=True,
    )
    assert result["status"] == "SUCCESS"
    assert result["m12_doc_kind"] == "offer_combined"
    assert result["m12_confidence"] == 0.8
    assert "duration_ms" in result
