"""Vérifie le payload /predict — parité Label Studio (document_role dans task.data).

M-ANNOTATION-CONTRACT-02 : contrat sortie corrigé côté backend ; ce test garantit
que le payload émis par couche A reste aligné (text + document_role + enveloppe).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.couche_a import extraction as extraction_module


def test_predict_payload_includes_document_role_in_task_data(monkeypatch):
    json_sent: dict = {}

    async def fake_post(_url, json=None, **_kwargs):
        json_sent.clear()
        json_sent.update(json or {})
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json = MagicMock(
            return_value={
                "results": [
                    {
                        "id": 1,
                        "score": 0.9,
                        "result": [
                            {
                                "from_name": "extracted_json",
                                "to_name": "document_text",
                                "type": "textarea",
                                "value": {"text": ['{"_meta":{}}']},
                            }
                        ],
                    }
                ]
            }
        )
        return r

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=fake_post)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(extraction_module.router, "_timeout", 30)
    monkeypatch.setattr(extraction_module.router, "_backend_url", "http://test-backend")

    async def _run():
        with patch(
            "src.couche_a.extraction.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await extraction_module._call_annotation_backend(
                document_id="doc-1",
                text="corps du document",
                document_role="financial_offer",
            )

    asyncio.run(_run())

    assert len(json_sent["tasks"]) == 1
    assert json_sent["tasks"][0]["data"]["text"] == "corps du document"
    assert json_sent["tasks"][0]["data"]["document_role"] == "financial_offer"
    assert json_sent["document_role"] == "financial_offer"
    assert json_sent["document_id"] == "doc-1"
    assert "tasks" in json_sent and isinstance(json_sent["tasks"], list)
