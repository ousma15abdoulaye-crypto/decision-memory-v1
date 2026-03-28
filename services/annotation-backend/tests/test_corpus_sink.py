"""Tests configuration S3 / corpus sink."""

import io
import json
import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from corpus_sink import (
    _botocore_config_for_s3,
    _s3_endpoint_safe_for_log,
    iter_corpus_m12_lines_from_s3,
    iter_corpus_m12_objects_from_s3,
    log_s3_corpus_boot_diagnostics,
)


def test_iter_corpus_m12_lines_from_s3_wraps_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import corpus_sink as cs

    payload = {"export_schema_version": "m12-v2", "source_text": "x"}

    def _fake_objects(**_kwargs):
        yield payload, "m12-v2/1/1_2_h.json", None

    monkeypatch.setattr(cs, "iter_corpus_m12_objects_from_s3", _fake_objects)
    lines = list(cs.iter_corpus_m12_lines_from_s3(prefix="m12-v2"))
    assert lines == [payload]


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


class TestS3EndpointSafeForLog:
    def test_empty_none(self) -> None:
        assert "endpoint_url_sans" not in _s3_endpoint_safe_for_log(None).lower()
        assert "AWS par défaut" in _s3_endpoint_safe_for_log(None)

    def test_strips_userinfo_and_query(self) -> None:
        raw = (
            "https://user:supersecret@abc.r2.cloudflarestorage.com"
            "/bucket?token=sekret&x=1#frag"
        )
        safe = _s3_endpoint_safe_for_log(raw)
        assert "supersecret" not in safe
        assert "user:" not in safe
        assert "sekret" not in safe
        assert "token" not in safe
        assert "abc.r2.cloudflarestorage.com" in safe
        assert safe.startswith("https://")

    def test_host_port(self) -> None:
        assert _s3_endpoint_safe_for_log("http://minio.local:9000") == (
            "http://minio.local:9000"
        )


class TestIterCorpusM12LinesFromS3:
    def test_lists_and_reads_json_objects(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("S3_BUCKET", "bucket-test")
        monkeypatch.setenv("S3_ENDPOINT", "https://abc.r2.cloudflarestorage.com")
        monkeypatch.setenv("S3_ACCESS_KEY_ID", "k")
        monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "s")
        monkeypatch.delenv("S3_CORPUS_PREFIX", raising=False)
        monkeypatch.setenv("S3_CLOCK_SKEW_AUTO", "0")

        payload = {
            "export_schema_version": "m12-v2",
            "source_text": "hello",
            "ls_meta": {"task_id": 1, "annotation_status": "annotated_validated"},
        }
        fake = MagicMock()
        paginator = MagicMock()
        fake.get_paginator.return_value = paginator
        lm = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "m12-v2/1/1_2_abcd1234.json", "LastModified": lm},
                ]
            }
        ]
        def _fresh_body(**_kwargs):
            return {
                "Body": io.BytesIO(json.dumps(payload).encode("utf-8")),
            }

        fake.get_object.side_effect = _fresh_body

        import corpus_sink as cs

        monkeypatch.setattr(cs, "_make_s3_client", lambda ep: fake)

        objs = list(iter_corpus_m12_objects_from_s3(prefix="m12-v2"))
        assert len(objs) == 1
        line, key, got_lm = objs[0]
        assert line["source_text"] == "hello"
        assert key == "m12-v2/1/1_2_abcd1234.json"
        assert got_lm == lm
        fake.get_paginator.assert_called_once_with("list_objects_v2")
        paginator.paginate.assert_called_once_with(
            Bucket="bucket-test", Prefix="m12-v2/"
        )
        fake.get_object.assert_called_once_with(
            Bucket="bucket-test", Key="m12-v2/1/1_2_abcd1234.json"
        )

    def test_skips_non_json_keys_and_invalid_json(
        self, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        monkeypatch.setenv("S3_BUCKET", "b")
        monkeypatch.setenv("S3_ENDPOINT", "https://abc.r2.cloudflarestorage.com")
        monkeypatch.setenv("S3_ACCESS_KEY_ID", "k")
        monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "s")
        monkeypatch.delenv("S3_CORPUS_PREFIX", raising=False)
        monkeypatch.setenv("S3_CLOCK_SKEW_AUTO", "0")

        fake = MagicMock()
        paginator = MagicMock()
        fake.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "m12-v2/1/readme.txt"},
                    {"Key": "m12-v2/1/bad.json"},
                    {"Key": "m12-v2/1/good.json"},
                ]
            }
        ]

        def _go(**kwargs):
            key = kwargs.get("Key")
            if key and str(key).endswith("good.json"):
                return {"Body": io.BytesIO(b'{"ok": true}')}
            return {"Body": io.BytesIO(b"not json")}

        fake.get_object.side_effect = _go

        import corpus_sink as cs

        monkeypatch.setattr(cs, "_make_s3_client", lambda ep: fake)
        caplog.set_level(logging.WARNING)
        lines = list(iter_corpus_m12_lines_from_s3(prefix="m12-v2"))
        assert lines == [{"ok": True}]
        paginator.paginate.assert_called_once_with(Bucket="b", Prefix="m12-v2/")

    def test_raises_without_bucket(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("S3_BUCKET", raising=False)
        with pytest.raises(ValueError, match="S3_BUCKET"):
            list(iter_corpus_m12_lines_from_s3())


class TestLogS3CorpusBootDiagnostics:
    def test_skips_when_not_s3(self, monkeypatch: pytest.MonkeyPatch, caplog) -> None:
        monkeypatch.setenv("CORPUS_SINK", "noop")
        caplog.set_level(logging.INFO)
        log_s3_corpus_boot_diagnostics()
        assert not any("[BOOT][CORPUS] S3/R2" in r.message for r in caplog.records)

    def test_warns_when_bucket_missing(
        self, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.delenv("S3_BUCKET", raising=False)
        caplog.set_level(logging.WARNING)
        log_s3_corpus_boot_diagnostics()
        assert any("S3_BUCKET vide" in r.message for r in caplog.records)

    def test_r2_explicit_env_line_and_no_secret_in_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv(
            "S3_ENDPOINT",
            "https://u:LEAK_SECRET@abc123.r2.cloudflarestorage.com?k=TOKEN",
        )
        monkeypatch.setenv("S3_ACCESS_KEY_ID", "AKIA_LEAK")
        monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "SECRET_LEAK_LONG")
        monkeypatch.delenv("S3_REGION", raising=False)
        monkeypatch.delenv("S3_ADDRESSING_STYLE", raising=False)
        monkeypatch.delenv("S3_PAYLOAD_SIGNING", raising=False)
        caplog.set_level(logging.INFO)
        log_s3_corpus_boot_diagnostics()
        text = " ".join(r.message for r in caplog.records)
        assert "[BOOT][CORPUS] S3/R2" in text
        assert "r2_host=True" in text
        assert "payload_signing=True" in text
        assert "credentials=explicit_env" in text
        assert "LEAK_SECRET" not in text
        assert "TOKEN" not in text
        assert "AKIA_LEAK" not in text
        assert "SECRET_LEAK" not in text
        assert "https://abc123.r2.cloudflarestorage.com" in text

    def test_default_chain_and_minio_second_line(
        self, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "b")
        monkeypatch.setenv("S3_ENDPOINT", "https://minio.example:9000")
        monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("S3_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("S3_REGION", raising=False)
        caplog.set_level(logging.INFO)
        log_s3_corpus_boot_diagnostics()
        text = " ".join(r.message for r in caplog.records)
        assert "credentials=default_chain" in text
        assert "r2_host=False" in text
        assert "domaine R2 custom" in text

    def test_payload_signing_env_overrides_r2(
        self, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "b")
        monkeypatch.setenv("S3_ENDPOINT", "https://abc123.r2.cloudflarestorage.com")
        monkeypatch.setenv("S3_PAYLOAD_SIGNING", "0")
        monkeypatch.setenv("S3_ACCESS_KEY_ID", "x")
        monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "y")
        caplog.set_level(logging.INFO)
        log_s3_corpus_boot_diagnostics()
        text = " ".join(r.message for r in caplog.records)
        assert "payload_signing=False" in text
        assert "S3_PAYLOAD_SIGNING=0" in text

    def test_never_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORPUS_SINK", "s3")
        monkeypatch.setenv("S3_BUCKET", "b")
        monkeypatch.setenv("S3_ENDPOINT", "not-a-valid-url-???")
        log_s3_corpus_boot_diagnostics()
