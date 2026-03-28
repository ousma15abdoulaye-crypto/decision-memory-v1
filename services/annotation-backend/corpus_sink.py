"""
Persistance des lignes m12-v2 (webhook → dépôt durable).
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from s3_clock_skew import auto_botocore_clock_skew_from_http

logger = logging.getLogger(__name__)


def _s3_env_credentials() -> tuple[str | None, str | None]:
    """
    Clés explicites depuis l’env (sans espaces / retours ligne).

    Si les deux sont absents, retourne (None, None) pour **ne pas** passer de chaînes vides
    à boto3 — sinon la chaîne de résolution par défaut (IAM, ``~/.aws``, etc.) est court-circuitée.

    Si une seule des deux est définie : avertissement ; on ne passe aucune clé (comportement ambigu).
    """
    key = (
        os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID") or ""
    ).strip()
    secret = (
        os.environ.get("S3_SECRET_ACCESS_KEY")
        or os.environ.get("AWS_SECRET_ACCESS_KEY")
        or ""
    ).strip()
    if key and secret:
        return key, secret
    if key or secret:
        logger.warning(
            "[CORPUS] S3 : une seule des deux clés est définie "
            "(S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY ou AWS_*) — "
            "définir les deux ou aucune pour la chaîne de credentials par défaut"
        )
    return None, None


def _payload_signing_for_endpoint(endpoint_url: str | None) -> bool:
    """
    Active la signature SHA256 du corps (PutObject) pour certains endpoints S3-compatibles.

    Cloudflare R2 peut renvoyer ``SignatureDoesNotMatch`` si le client envoie
    ``UNSIGNED-PAYLOAD`` alors que le service attend un hash cohérent avec SigV4.
    Désactiver : ``S3_PAYLOAD_SIGNING=0`` ; forcer partout : ``S3_PAYLOAD_SIGNING=1``.
    """
    raw = (os.environ.get("S3_PAYLOAD_SIGNING") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    ep = (endpoint_url or "").strip().lower()
    return "r2.cloudflarestorage.com" in ep


def _botocore_config_for_s3(*, endpoint_url: str | None = None):
    """
    Signature V4.

    Pour **Cloudflare R2**, l’exemple officiel boto3 **ne force pas** path-style ; le forcer
    peut provoquer ``SignatureDoesNotMatch`` de façon intermittente. Par défaut : pas de
    ``addressing_style`` (comportement boto3 / virtual-hosted sur endpoint custom).

    Optionnel : ``S3_ADDRESSING_STYLE=path`` (MinIO, certains proxys) ou ``virtual``.

    Pour **R2** (détection par host du endpoint), ``payload_signing_enabled`` est activé
    afin d’aligner la signature sur le corps de ``PutObject`` (voir ``S3_PAYLOAD_SIGNING``).
    """
    from botocore.config import Config

    style = (os.environ.get("S3_ADDRESSING_STYLE") or "").strip().lower()
    s3_opts: dict[str, Any] = {}
    if style in ("path", "virtual"):
        s3_opts["addressing_style"] = style
    if _payload_signing_for_endpoint(endpoint_url):
        s3_opts["payload_signing_enabled"] = True

    if s3_opts:
        return Config(signature_version="s3v4", s3=s3_opts)
    return Config(signature_version="s3v4")


def _s3_endpoint_safe_for_log(raw: str | None) -> str:
    """
    Pour les logs uniquement : schéma + hôte (+ port), sans userinfo ni query/fragment
    (évite les fuites si S3_ENDPOINT contient des identifiants ou des jetons en query).
    """
    if not raw or not str(raw).strip():
        return "(AWS par défaut, pas d’endpoint custom)"
    s = str(raw).strip().rstrip("/")
    if "://" not in s:
        s = f"https://{s}"
    try:
        p = urlparse(s)
    except Exception:
        return "[endpoint_url_invalid]"
    host = p.hostname
    if not host:
        return "[endpoint_url_sans_hôte]"
    scheme = p.scheme or "https"
    port = p.port
    if port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def log_s3_corpus_boot_diagnostics() -> None:
    """
    À appeler au démarrage (ex. lifespan uvicorn).

    Log la configuration S3/R2 **sans secrets** ni création de client boto3, pour vérifier
    Railway (endpoint, région, détection R2, signature du corps PutObject).
    """
    if (os.environ.get("CORPUS_SINK") or "").strip().lower() != "s3":
        return
    bucket = (os.environ.get("S3_BUCKET") or "").strip()
    if not bucket:
        logger.warning(
            "[BOOT][CORPUS] CORPUS_SINK=s3 mais S3_BUCKET vide — sink noop jusqu’à correction"
        )
        return
    ep = (os.environ.get("S3_ENDPOINT") or "").strip().rstrip("/") or None
    prefix = (os.environ.get("S3_CORPUS_PREFIX") or "m12-v2").strip() or "m12-v2"
    region_raw = os.environ.get("S3_REGION", "").strip()
    if region_raw:
        region_name: str | None = region_raw
    elif ep:
        region_name = "auto"
    else:
        region_name = None
    access_key, secret_key = _s3_env_credentials()
    creds = (
        "explicit_env"
        if access_key is not None and secret_key is not None
        else "default_chain"
    )
    style = (os.environ.get("S3_ADDRESSING_STYLE") or "").strip().lower()
    addressing = style if style in ("path", "virtual") else "default"
    ep_lower = (ep or "").lower()
    r2_host = "r2.cloudflarestorage.com" in ep_lower
    ps = _payload_signing_for_endpoint(ep)
    ps_env = (os.environ.get("S3_PAYLOAD_SIGNING") or "").strip()
    ps_env_log = ps_env if ps_env else "unset"
    ep_safe = _s3_endpoint_safe_for_log(ep)
    logger.info(
        "[BOOT][CORPUS] S3/R2 — bucket=%r prefix=%r endpoint=%s region=%r "
        "credentials=%s r2_host=%s payload_signing=%s addressing=%s S3_PAYLOAD_SIGNING=%s",
        bucket,
        prefix.rstrip("/"),
        ep_safe,
        region_name,
        creds,
        r2_host,
        ps,
        addressing,
        ps_env_log,
    )
    if ep and not r2_host:
        logger.info(
            "[BOOT][CORPUS] Endpoint sans host r2.cloudflarestorage.com — "
            "domaine R2 custom : tester S3_PAYLOAD_SIGNING=1 si PutObject échoue (signature)."
        )


class CorpusSink(Protocol):
    def append_line(self, line: dict[str, Any]) -> None: ...


class NoopCorpusSink:
    """Défaut — aucune écriture (CORPUS_SINK absent ou noop)."""

    def append_line(self, line: dict[str, Any]) -> None:
        return


class FileAppendCorpusSink:
    """Append JSONL local — append atomique, crée les répertoires parents."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)

    def append_line(self, line: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


class DualCorpusSink:
    """
    Écrit vers deux sinks simultanément : primaire (S3/R2) + ombre locale.

    Garantie enterprise : si le primaire échoue (réseau, S3, etc.), l'ombre locale
    est toujours écrite en premier. Si l'ombre échoue, l'erreur est loguée mais
    n'empêche pas l'écriture primaire.

    Usage type : CORPUS_SINK=s3 + CORPUS_LOCAL_BACKUP_PATH=/chemin/backup.jsonl
    """

    def __init__(self, primary: "CorpusSink", shadow: FileAppendCorpusSink) -> None:
        self._primary = primary
        self._shadow = shadow

    def append_line(self, line: dict[str, Any]) -> None:
        # L'ombre locale est écrite EN PREMIER — survie si le primaire tombe
        try:
            self._shadow.append_line(line)
        except Exception as exc:
            logger.error(
                "[CORPUS][SHADOW] Écriture locale échouée (primaire tenté quand même) : %s",
                exc,
            )
        self._primary.append_line(line)


def _make_s3_client(endpoint_url: str | None) -> Any:
    """Client S3 boto3 — même configuration que le sink corpus (R2 / AWS / MinIO)."""
    import boto3  # lazy

    ep = (endpoint_url or "").strip().rstrip("/") or None
    region_raw = os.environ.get("S3_REGION", "").strip()
    if region_raw:
        region_name: str | None = region_raw
    elif ep:
        region_name = "auto"
    else:
        region_name = None

    access_key, secret_key = _s3_env_credentials()
    session = boto3.session.Session()
    client_kw: dict[str, Any] = {
        "endpoint_url": ep,
        "config": _botocore_config_for_s3(endpoint_url=ep),
    }
    if access_key is not None and secret_key is not None:
        client_kw["aws_access_key_id"] = access_key
        client_kw["aws_secret_access_key"] = secret_key
    if region_name is not None:
        client_kw["region_name"] = region_name
    verify_raw = (os.environ.get("S3_VERIFY_SSL") or "").strip().lower()
    if verify_raw in ("0", "false", "no", "off"):
        environment = (os.environ.get("ENVIRONMENT") or "").strip().lower()
        if environment == "production":
            logger.warning(
                "[CORPUS][S3] Variable d'environnement S3_VERIFY_SSL=%r ignorée en "
                "production : la vérification TLS reste activée pour des raisons de "
                "sécurité.",
                os.environ.get("S3_VERIFY_SSL"),
            )
        else:
            logger.warning(
                "[CORPUS][S3] La vérification TLS des certificats est DÉSACTIVÉE "
                "(S3_VERIFY_SSL=%r). À n'utiliser qu'en debug ou avec interception TLS. "
                "NE PAS activer en production.",
                os.environ.get("S3_VERIFY_SSL"),
            )
            client_kw["verify"] = False
    return session.client("s3", **client_kw)


def iter_corpus_m12_lines_from_s3(
    *,
    bucket: str | None = None,
    endpoint_url: str | None = None,
    prefix: str | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Liste et lit les objets dont la clé se termine par ``.json`` sous ``prefix/`` (R2/S3).

    Chaque objet est le **corps JSON** écrit par :class:`S3CorpusSink` (un document
    JSON par clé — pas de JSONL dans le bucket). Côté Python : ``json.loads`` sur le
    corps brut → une ``dict`` m12-v2 par objet.

    Variables d’environnement si les arguments sont omis : ``S3_BUCKET`` (obligatoire),
    ``S3_ENDPOINT``, ``S3_CORPUS_PREFIX`` (défaut ``m12-v2``), clés ``S3_*`` / ``AWS_*``.

    :raises ValueError: si ``S3_BUCKET`` absent et ``bucket`` non fourni.
    """
    b = bucket or os.environ.get("S3_BUCKET", "").strip()
    if not b:
        raise ValueError(
            "S3_BUCKET requis (variable d'environnement ou argument bucket=)"
        )
    ep = (
        endpoint_url
        if endpoint_url is not None
        else (os.environ.get("S3_ENDPOINT", "").strip() or None)
    )
    if prefix is not None:
        pfx = prefix.strip() or "m12-v2"
    else:
        pfx = (os.environ.get("S3_CORPUS_PREFIX") or "m12-v2").strip() or "m12-v2"
    pfx = pfx.rstrip("/")

    with auto_botocore_clock_skew_from_http():
        client = _make_s3_client(ep)
        paginator = client.get_paginator("list_objects_v2")
        list_prefix = f"{pfx}/"
        for page in paginator.paginate(Bucket=b, Prefix=list_prefix):
            contents = page.get("Contents") or []
            for obj in sorted(contents, key=lambda x: str(x.get("Key", ""))):
                key = obj.get("Key")
                if not key or not str(key).endswith(".json"):
                    continue
                resp = client.get_object(Bucket=b, Key=key)
                with closing(resp["Body"]) as body:
                    raw = body.read().decode("utf-8")
                try:
                    line = json.loads(raw)
                except json.JSONDecodeError as e:
                    logger.warning("[CORPUS] JSON invalide pour %s : %s", key, e)
                    continue
                if not isinstance(line, dict):
                    logger.warning("[CORPUS] Objet non-dict pour %s", key)
                    continue
                yield line


class S3CorpusSink:
    """Stockage objet S3-compatible (R2, AWS, MinIO)."""

    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str | None = None,
        prefix: str = "m12-v2",
    ) -> None:
        ep = (endpoint_url or "").strip().rstrip("/") or None
        self._client = _make_s3_client(ep)
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")

    def append_line(self, line: dict[str, Any]) -> None:
        ls_meta = line.get("ls_meta") or {}
        task_id = ls_meta.get("task_id", "unknown")
        ann_id = ls_meta.get("annotation_id", "unknown")
        project_id = ls_meta.get("project_id", "unknown")
        ch = line.get("content_hash", "unknown")
        key = f"{self._prefix}/{project_id}/{task_id}_{ann_id}_{ch}.json"
        body = json.dumps(line, ensure_ascii=False).encode("utf-8")
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType="application/json; charset=utf-8",
        )


def _local_backup_sink_from_env() -> FileAppendCorpusSink | None:
    """
    Construit un sink fichier local si ``CORPUS_LOCAL_BACKUP_PATH`` est défini.

    Permet d'ajouter un backup local automatique à n'importe quel sink principal
    (y compris S3/R2). Les données sont écrites localement EN PREMIER (voir DualCorpusSink).
    """
    path = (os.environ.get("CORPUS_LOCAL_BACKUP_PATH") or "").strip()
    if not path:
        return None
    return FileAppendCorpusSink(path)


def build_sink_from_env() -> CorpusSink:
    """
    Construit le sink selon CORPUS_SINK / variables associées.

    Si ``CORPUS_LOCAL_BACKUP_PATH`` est défini, un ``DualCorpusSink`` enveloppe le
    sink principal avec un backup local automatique — garantit la survie des données
    en cas de déconnexion réseau / perte de session Label Studio.
    """
    mode = (os.environ.get("CORPUS_SINK") or "noop").strip().lower()
    primary: CorpusSink
    if mode in ("", "noop", "none", "disabled"):
        primary = NoopCorpusSink()
    elif mode == "file":
        path = os.environ.get("CORPUS_FILE_PATH", "").strip()
        if not path:
            logger.warning("CORPUS_SINK=file mais CORPUS_FILE_PATH vide — noop")
            primary = NoopCorpusSink()
        else:
            primary = FileAppendCorpusSink(path)
    elif mode == "s3":
        bucket = os.environ.get("S3_BUCKET", "").strip()
        if not bucket:
            logger.warning("CORPUS_SINK=s3 mais S3_BUCKET vide — noop")
            primary = NoopCorpusSink()
        else:
            endpoint = os.environ.get("S3_ENDPOINT", "").strip() or None
            prefix = os.environ.get("S3_CORPUS_PREFIX", "m12-v2").strip() or "m12-v2"
            primary = S3CorpusSink(bucket, endpoint_url=endpoint, prefix=prefix)
    else:
        logger.warning("CORPUS_SINK inconnu %r — noop", mode)
        primary = NoopCorpusSink()

    shadow = _local_backup_sink_from_env()
    if shadow is not None:
        logger.info(
            "[CORPUS] DualSink activé — backup local : %s", shadow._path
        )
        return DualCorpusSink(primary=primary, shadow=shadow)
    return primary


def object_key_for_line(line: dict[str, Any], prefix: str = "m12-v2") -> str:
    """Clé stable idempotente (même logique que S3CorpusSink)."""
    ls_meta = line.get("ls_meta") or {}
    task_id = ls_meta.get("task_id", "unknown")
    ann_id = ls_meta.get("annotation_id", "unknown")
    project_id = ls_meta.get("project_id", "unknown")
    ch = line.get("content_hash", "unknown")
    p = prefix.rstrip("/")
    return f"{p}/{project_id}/{task_id}_{ann_id}_{ch}.json"
