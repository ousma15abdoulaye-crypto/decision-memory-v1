"""Tests configuration S3 / corpus sink."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_AB = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _annotation_backend_path() -> None:
    if str(_AB) not in sys.path:
        sys.path.insert(0, str(_AB))


class TestBotocoreConfigForS3:
    def test_r2_endpoint_enables_payload_signing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("S3_PAYLOAD_SIGNING", raising=False)
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)
        from corpus_sink import _botocore_config_for_s3

        c = _botocore_config_for_s3(
            endpoint_url="https://abc123.r2.cloudflarestorage.com")
        assert c.s3 is not None
        assert c.s3.get("payload_signing_enabled") is True

    def test_non_r2_default_no_payload_signing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("S3_PAYLOAD_SIGNING", raising=False)
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)
        from corpus_sink import _botocore_config_for_s3

        c = _botocore_config_for_s3(endpoint_url="https://minio.local:9000")
        assert c.s3 is None

    def test_s3_payload_signing_env_forces_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)
        monkeypatch.setenv("S3_PAYLOAD_SIGNING", "1")
        from corpus_sink import _botocore_config_for_s3

        c = _botocore_config_for_s3(endpoint_url=None)
        assert c.s3 is not None
        assert c.s3.get("payload_signing_enabled") is True

    def test_r2_payload_signing_can_disable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)
        monkeypatch.setenv("S3_PAYLOAD_SIGNING", "0")
        from corpus_sink import _botocore_config_for_s3

        c = _botocore_config_for_s3(
            endpoint_url="https://abc123.r2.cloudflarestorage.com")
        assert c.s3 is None

    def test_addressing_style_merge_with_r2_payload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("S3_PAYLOAD_SIGNING", raising=False)
        monkeypatch.setenv("S3_ADDRESSING_STYLE", "path")
        from corpus_sink import _botocore_config_for_s3

        c = _botocore_config_for_s3(
            endpoint_url="https://abc123.r2.cloudflarestorage.com")
        assert c.s3 is not None
        assert c.s3.get("addressing_style") == "path"
        assert c.s3.get("payload_signing_enabled") is True
