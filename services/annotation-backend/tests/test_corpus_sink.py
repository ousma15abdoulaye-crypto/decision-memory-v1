"""Tests configuration S3 / corpus sink."""

import pytest

from corpus_sink import _botocore_config_for_s3


class TestBotocoreConfigForS3:
    def test_r2_endpoint_enables_payload_signing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("S3_PAYLOAD_SIGNING", raising=False)
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)

        c = _botocore_config_for_s3(
            endpoint_url="https://abc123.r2.cloudflarestorage.com"
        )
        assert c.s3 is not None
        assert c.s3.get("payload_signing_enabled") is True

    def test_non_r2_default_no_payload_signing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("S3_PAYLOAD_SIGNING", raising=False)
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)

        c = _botocore_config_for_s3(endpoint_url="https://minio.local:9000")
        assert c.s3 is None

    def test_s3_payload_signing_env_forces_on(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)
        monkeypatch.setenv("S3_PAYLOAD_SIGNING", "1")

        c = _botocore_config_for_s3(endpoint_url=None)
        assert c.s3 is not None
        assert c.s3.get("payload_signing_enabled") is True

    def test_r2_payload_signing_can_disable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)
        monkeypatch.setenv("S3_PAYLOAD_SIGNING", "0")

        c = _botocore_config_for_s3(
            endpoint_url="https://abc123.r2.cloudflarestorage.com"
        )
        assert c.s3 is None

    def test_addressing_style_merge_with_r2_payload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("S3_PAYLOAD_SIGNING", raising=False)
        monkeypatch.setenv("S3_ADDRESSING_STYLE", "path")

        c = _botocore_config_for_s3(
            endpoint_url="https://abc123.r2.cloudflarestorage.com"
        )
        assert c.s3 is not None
        assert c.s3.get("addressing_style") == "path"
        assert c.s3.get("payload_signing_enabled") is True
