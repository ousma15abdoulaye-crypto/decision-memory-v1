"""Tests configuration S3 / corpus sink."""

import io
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from corpus_sink import (
    DualCorpusSink,
    FileAppendCorpusSink,
    NoopCorpusSink,
    _botocore_config_for_s3,
    _s3_endpoint_safe_for_log,
    build_sink_from_env,
    iter_corpus_m12_lines_from_s3,
    log_s3_corpus_boot_diagnostics,
)


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
        paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "m12-v2/1/1_2_abcd1234.json"},
                ]
            }
        ]
        fake.get_object.return_value = {
            "Body": io.BytesIO(json.dumps(payload).encode("utf-8")),
        }

        import corpus_sink as cs

        monkeypatch.setattr(cs, "_make_s3_client", lambda ep: fake)

        lines = list(iter_corpus_m12_lines_from_s3(prefix="m12-v2"))
        assert len(lines) == 1
        assert lines[0]["source_text"] == "hello"
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


class TestDualCorpusSink:
    """DualCorpusSink — backup local toujours écrit en premier."""

    def test_writes_to_both_primary_and_shadow(self) -> None:
        written_primary: list[dict] = []

        class _FakePrimary:
            def append_line(self, line: dict) -> None:
                written_primary.append(line)

        with tempfile.TemporaryDirectory() as tmpdir:
            shadow_path = Path(tmpdir) / "shadow.jsonl"
            shadow = FileAppendCorpusSink(str(shadow_path))
            dual = DualCorpusSink(primary=_FakePrimary(), shadow=shadow)
            line = {"export_ok": True, "ls_meta": {"task_id": 1, "annotation_id": 99}}
            dual.append_line(line)
            assert len(written_primary) == 1
            raw = shadow_path.read_text("utf-8").strip()
            assert json.loads(raw) == line

    def test_primary_failure_does_not_prevent_shadow(self) -> None:
        """Si le primaire lève, l'ombre locale a déjà été écrite."""

        class _BrokenPrimary:
            def append_line(self, line: dict) -> None:
                raise RuntimeError("S3 down")

        with tempfile.TemporaryDirectory() as tmpdir:
            shadow_path = Path(tmpdir) / "shadow.jsonl"
            shadow = FileAppendCorpusSink(str(shadow_path))
            dual = DualCorpusSink(primary=_BrokenPrimary(), shadow=shadow)
            line = {"export_ok": False, "ls_meta": {"task_id": 2}}
            with pytest.raises(RuntimeError, match="S3 down"):
                dual.append_line(line)
            # L'ombre a été écrite avant le crash du primaire
            assert shadow_path.exists()
            saved = json.loads(shadow_path.read_text("utf-8").strip())
            assert saved["ls_meta"]["task_id"] == 2

    def test_shadow_failure_does_not_prevent_primary(self, caplog) -> None:
        """Si l'ombre locale échoue, le primaire est quand même appelé."""
        written: list[dict] = []

        class _GoodPrimary:
            def append_line(self, line: dict) -> None:
                written.append(line)

        class _BrokenShadow:
            _path = Path("/nonexistent/shadow.jsonl")

            def append_line(self, line: dict) -> None:
                raise OSError("disk full")

        dual = DualCorpusSink(primary=_GoodPrimary(), shadow=_BrokenShadow())  # type: ignore[arg-type]
        caplog.set_level(logging.ERROR)
        line = {"export_ok": True, "ls_meta": {"task_id": 3}}
        dual.append_line(line)
        assert written == [line]
        assert any("SHADOW" in r.message for r in caplog.records)

    def test_build_sink_from_env_creates_dual_when_backup_path_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backup = str(Path(tmpdir) / "bkp.jsonl")
            monkeypatch.setenv("CORPUS_SINK", "noop")
            monkeypatch.setenv("CORPUS_LOCAL_BACKUP_PATH", backup)
            sink = build_sink_from_env()
            assert isinstance(sink, DualCorpusSink)
            line = {"ls_meta": {"task_id": 5, "annotation_id": 10}}
            sink.append_line(line)
            saved = json.loads(Path(backup).read_text("utf-8").strip())
            assert saved["ls_meta"]["task_id"] == 5

    def test_build_sink_from_env_noop_without_backup_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CORPUS_SINK", "noop")
        monkeypatch.delenv("CORPUS_LOCAL_BACKUP_PATH", raising=False)
        sink = build_sink_from_env()
        assert isinstance(sink, NoopCorpusSink)
