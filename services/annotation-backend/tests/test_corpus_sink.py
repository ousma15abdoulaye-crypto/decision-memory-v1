"""Tests configuration S3 / corpus sink."""

import logging

import pytest
from corpus_sink import _botocore_config_for_s3, log_s3_corpus_boot_diagnostics


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


_S3_ENV_VARS = (
    "CORPUS_SINK",
    "S3_BUCKET",
    "S3_ENDPOINT",
    "S3_REGION",
    "S3_CORPUS_PREFIX",
    "S3_ADDRESSING_STYLE",
    "S3_PAYLOAD_SIGNING",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
)


class TestLogS3CorpusBootDiagnostics:
    """log_s3_corpus_boot_diagnostics() — no raise, no secrets, correct [BOOT][CORPUS] line."""

    def _clear_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in _S3_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

    # ------------------------------------------------------------------ early-exit
    def test_no_op_when_corpus_sink_not_s3(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "noop")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "[BOOT][CORPUS]" not in caplog.text

    def test_no_op_when_corpus_sink_absent(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "[BOOT][CORPUS]" not in caplog.text

    def test_warning_when_bucket_empty(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        with caplog.at_level(logging.WARNING, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "[BOOT][CORPUS]" in caplog.text
        assert "S3_BUCKET" in caplog.text

    # ------------------------------------------------------------------ AWS default
    def test_aws_default_no_custom_endpoint(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "[BOOT][CORPUS]" in caplog.text
        assert "r2_host=False" in caplog.text
        assert "credentials=default_chain" in caplog.text
        assert "region=None" in caplog.text
        assert "addressing=default" in caplog.text

    # ------------------------------------------------------------------ R2 endpoint
    def test_r2_endpoint_sets_r2_host_payload_signing_region_auto(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-r2-bucket")
        monkeypatch.setenv("S3_ENDPOINT", "https://abc123.r2.cloudflarestorage.com")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "[BOOT][CORPUS]" in caplog.text
        assert "r2_host=True" in caplog.text
        assert "payload_signing=True" in caplog.text
        assert "region='auto'" in caplog.text

    def test_r2_payload_signing_disabled_via_env(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-r2-bucket")
        monkeypatch.setenv("S3_ENDPOINT", "https://abc123.r2.cloudflarestorage.com")
        monkeypatch.setenv("S3_PAYLOAD_SIGNING", "0")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "[BOOT][CORPUS]" in caplog.text
        assert "payload_signing=False" in caplog.text
        assert "S3_PAYLOAD_SIGNING=0" in caplog.text

    # ------------------------------------------------------------------ custom non-R2 endpoint
    def test_custom_non_r2_endpoint_logs_hint(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "minio-bucket")
        monkeypatch.setenv("S3_ENDPOINT", "https://minio.local:9000")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "[BOOT][CORPUS]" in caplog.text
        assert "r2_host=False" in caplog.text
        # hint about custom R2 domains and payload signing
        assert "S3_PAYLOAD_SIGNING=1" in caplog.text

    # ------------------------------------------------------------------ credentials
    def test_explicit_credentials_no_secret_values_in_log(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv("S3_ACCESS_KEY_ID", "AKIASUPERSECRETKEY")
        monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "supersecretvalue123456")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "[BOOT][CORPUS]" in caplog.text
        assert "credentials=explicit_env" in caplog.text
        # actual secret values must NOT appear in logs
        assert "AKIASUPERSECRETKEY" not in caplog.text
        assert "supersecretvalue123456" not in caplog.text

    def test_aws_explicit_credentials_no_secret_values_in_log(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIA_AWS_KEY")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws_super_secret")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "credentials=explicit_env" in caplog.text
        assert "AKIA_AWS_KEY" not in caplog.text
        assert "aws_super_secret" not in caplog.text

    # ------------------------------------------------------------------ region
    def test_region_from_s3_region_env(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv("S3_REGION", "eu-west-3")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "region='eu-west-3'" in caplog.text

    def test_region_auto_when_endpoint_set_and_no_s3_region(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv("S3_ENDPOINT", "https://minio.local:9000")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "region='auto'" in caplog.text

    # ------------------------------------------------------------------ addressing style
    def test_addressing_style_path_reflected_in_log(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv("S3_ADDRESSING_STYLE", "path")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "addressing=path" in caplog.text

    # ------------------------------------------------------------------ payload signing env
    def test_payload_signing_forced_on_no_r2(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv("S3_PAYLOAD_SIGNING", "1")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "payload_signing=True" in caplog.text
        assert "S3_PAYLOAD_SIGNING=1" in caplog.text

    # ------------------------------------------------------------------ prefix
    def test_custom_prefix_reflected_in_log(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._clear_env(monkeypatch)
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv("S3_CORPUS_PREFIX", "custom/prefix")
        with caplog.at_level(logging.INFO, logger="corpus_sink"):
            log_s3_corpus_boot_diagnostics()
        assert "prefix='custom/prefix'" in caplog.text
